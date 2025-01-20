"""
utils.py

Functions:
- generate_script: Get the dialogue from the LLM.
- call_llm: Call the LLM with the given prompt and dialogue format.
- parse_url: Parse the given URL and return the text content.
- generate_podcast_audio: Generate audio for podcast using TTS or advanced audio models.
"""

from concurrent.futures import ThreadPoolExecutor
import io

# Standard library imports
import json
import time
from io import BytesIO
from typing import Any, Union
from urllib.parse import urlparse

import boto3
from botocore.config import Config
import requests
from botocore.exceptions import ClientError
from pydub import AudioSegment
from pypdf import PdfReader
from loguru import logger
from prompts import (
    QUESTION_MODIFIER,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_OUTLINE,
    TONE_MODIFIER,
)

# Local imports
from constants import (
    AWS_REGION,
    ERROR_MESSAGE_NOT_PDF,
    ERROR_MESSAGE_READING_PDF,
    JINA_READER_URL,
    JINA_RETRY_ATTEMPTS,
    JINA_RETRY_DELAY,
)
from schema import MediumDialogue, ShortDialogue
from prompts import OUTPUT_FORMAT_MODIFIER


def generate_topics():
    """Rough topics to be discussed in the podcast"""


def generate_topic_dialogues():
    """Generate dialogues for each topic"""


def generate_script_with_outline(
    model_id: str,
    input_text: str,
    question: str,
    tone: str,
    video_file: str | None,
    files: list[str] | None,
    s3_url: str | None,
    output_model: Union[ShortDialogue, MediumDialogue],
) -> Union[ShortDialogue, MediumDialogue]:
    """Get the dialogue from the LLM."""

    # Call the LLM for the first time
    # We only use video for draft generation
    user_prompt = f"""Create an outline for a podcast on the following topic
    
    <topic>
    {question}
    </topic>
    
    Provided reference text:
    <reference>
    {input_text}
    </reference>
    """

    outline = invoke_bedrock_model(
        model_id, SYSTEM_PROMPT_OUTLINE, user_prompt, None, files, s3_url
    )

    outline_output = (
        outline["output"]["message"]["content"][0]["text"]
        .split("<output>")[-1]
        .split("</output>")[0]
    )

    logger.info(outline_output)

    outline_output = json.loads(outline_output)
    old_dialogue = None

    # Modify the system prompt based on the user input
    modified_system_prompt = SYSTEM_PROMPT

    # if question:
    #     modified_system_prompt += f"\n\n{QUESTION_MODIFIER} {question}"
    if tone:
        modified_system_prompt += f"\n\n{TONE_MODIFIER} {tone}."

    text = (
        f"Use this context and provided documents to generate the podcast <text>\n{input_text}</text>\n"
        + "The dialogue should have 20-25 turns per speaker"
        + OUTPUT_FORMAT_MODIFIER
    )

    for topic in outline_output["topics"]:
        logger.info(f"Topic: {topic['topic']}")
        logger.info(f"Description: {topic['summary']}")
        if not old_dialogue:

            system_prompt_with_dialogue = f"""{modified_system_prompt}. Continue podcast for the following topic based on provided inputs (text and/or video). The continuation should sound natural. The topic is:
            {topic["topic"]}: {topic["summary"]}
            Do not end the podcast, just generate dialogues for the above topic. The podcast will be continued later on different topics. Do not generate ending dialogues. Do not generate concluding dialogues. Do not end the podcast
            """

            old_dialogue = call_llm(
                model_id,
                modified_system_prompt,
                text
                + """Do not end the podcast, just generate dialogues for the above topic. The podcast will be continued later on different topics. Do not generate ending dialogues. Do not generate concluding dialogues. Do not end the podcast""",
                video_file,
                files,
                s3_url,
                output_model,
            )
        else:

            system_prompt_with_dialogue = f"""{SYSTEM_PROMPT}\n\nHere is the podcast generated so far:\n\n{old_dialogue.model_dump_json()}.\n\n Continue podcast for the following topic based on provided inputs (text and/or video). The continuation should sound natural. The topic is:
            {topic["topic"]}: {topic["summary"]}
            Do not end the podcast, just generate dialogues for the above topic. The podcast will be continued later on different topics. Do not generate ending dialogues. Do not generate concluding dialogues. Do not end the podcast
            """

            dialogue_current = call_llm(
                model_id,
                system_prompt_with_dialogue,
                text
                + """Do not end the podcast, just generate dialogues for the above topic. The podcast will be continued later on different topics. Do not generate ending dialogues. Do not generate concluding dialogues. Do not end the podcast""",
                video_file,
                files,
                s3_url,
                output_model,
            )

            old_dialogue.dialogue.extend(dialogue_current.dialogue)
            logger.info(old_dialogue)

    system_prompt_with_dialogue = f"""{SYSTEM_PROMPT}\n\nHere is the podcast generated so far:\n\n{old_dialogue.model_dump_json()}.\n\n Generate dialogues to finish the podcast. The finish should be natural."""

    dialogue_current = call_llm(
        model_id,
        system_prompt_with_dialogue,
        text,
        video_file,
        files,
        s3_url,
        output_model,
    )

    old_dialogue.dialogue.extend(dialogue_current.dialogue)

    return old_dialogue


def generate_script(
    model_id: str,
    input_text: str,
    question: str,
    tone: str,
    video_file: str | None,
    files: list[str] | None,
    s3_url: str | None,
    output_model: Union[ShortDialogue, MediumDialogue],
) -> Union[ShortDialogue, MediumDialogue]:
    """Get the dialogue from the LLM."""

    # Call the LLM for the first time
    # We only use video for draft generation

    # Modify the system prompt based on the user input
    modified_system_prompt = SYSTEM_PROMPT

    if question:
        modified_system_prompt += f"\n\n{QUESTION_MODIFIER} {question}"
    if tone:
        modified_system_prompt += f"\n\n{TONE_MODIFIER} {tone}."

    user_prompt = f"<text>\n{input_text}</text>\n" + OUTPUT_FORMAT_MODIFIER

    first_draft_dialogue = call_llm(
        model_id,
        modified_system_prompt,
        user_prompt,
        video_file,
        files,
        s3_url,
        output_model,
    )

    logger.info(f"First draft dialogue:\n {first_draft_dialogue}")
    # Call the LLM a second time to improve the dialogue
    user_prompt_update = f"""Here is the first draft of the dialogue you provided:\n\n{first_draft_dialogue.model_dump_json()}.
    "Please improve the dialogue. Make it more natural and engaging.\n"
    {OUTPUT_FORMAT_MODIFIER}
    """
    final_dialogue = call_llm(
        model_id,
        modified_system_prompt,
        user_prompt_update,
        None,
        None,
        None,
        output_model,
    )
    logger.info(f"Final dialogue:\n {final_dialogue}")

    return final_dialogue


def get_pdf_from_s3(object_url: str) -> bytes:
    """
    Retrieves a PDF file from S3 and returns it as a BytesIO object

    Args:
        bucket_name (str): Name of the S3 bucket
        key_name (str): Key/path of the PDF file in the bucket

    Returns:
        BytesIO: PDF file contents as a BytesIO object

    Raises:
        ClientError: If there's an error retrieving the file from S3
    """
    try:

        # Create an S3 client
        s3_client = boto3.client("s3")

        parsed_url = urlparse(object_url)
        bucket_name = parsed_url.netloc.split(".")[0]
        key_name = parsed_url.path.lstrip("/")

        # Get the PDF file from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=key_name)

        # Read the file content
        pdf_content = response["Body"].read()
        # Create a BytesIO object
        # pdf_file = BytesIO(pdf_content)

        # text = read_pdf(pdf_file)

        return pdf_content

    except ClientError as e:
        raise Exception(
            f"Error reading PDF file '{key_name}' from bucket '{bucket_name}': {str(e)}"
        )


def read_pdf(file_name: str | bytes):
    text = ""
    try:
        reader = PdfReader(file_name)
        text += "\n\n".join([page.extract_text() for page in reader.pages])
    except Exception as e:
        raise Exception(f"{ERROR_MESSAGE_READING_PDF}: {str(e)}")

    return text


def read_pdfs(files: list[str] | bytes) -> str:
    text = ""

    for file in files:
        if not file.lower().endswith(".pdf"):
            raise Exception(ERROR_MESSAGE_NOT_PDF)

        text += read_pdf(file)

    return text


def call_llm(
    model_id: str,
    system_prompt: str,
    text: str,
    video_file: str | None,
    files: list[str] | None,
    s3_url: str | None,
    dialogue_format: Any,
) -> Any:
    logger.info(f"Video files are passed: {video_file}")
    # if not video_files:
    result = invoke_bedrock_model(
        model_id, system_prompt, text, video_file, files, s3_url
    )

    logger.info(f"Result:\n {result}")
    result_output = (
        result["output"]["message"]["content"][0]["text"]
        .split("<output>")[-1]
        .split("</output>")[0]
    )

    scratchpad = (
        result["output"]["message"]["content"][0]["text"]
        .split("<scratchpad>")[-1]
        .split("</scratchpad>")[0]
    )

    idx_start = result_output.find("{")
    idx_end = result_output.rfind("}") + 1

    result_output = result_output[idx_start:idx_end]
    json_result = json.loads(result_output)

    json_result["scratchpad"] = scratchpad

    return dialogue_format.parse_obj(json_result)


def parse_url(url: str) -> str:
    """Parse the given URL and return the text content."""
    for attempt in range(JINA_RETRY_ATTEMPTS):
        try:
            full_url = f"{JINA_READER_URL}{url}"
            response = requests.get(full_url, timeout=60)
            response.raise_for_status()  # Raise an exception for bad status codes
            break
        except requests.RequestException as e:
            if attempt == JINA_RETRY_ATTEMPTS - 1:  # Last attempt
                raise ValueError(
                    f"Failed to fetch URL after {JINA_RETRY_ATTEMPTS} attempts: {e}"
                ) from e
            time.sleep(JINA_RETRY_DELAY)  # Wait for X second before retrying
    return response.text


def text_to_speech(text, voice_id, polly_client):
    """Convert text to speech using Amazon Polly"""
    try:
        response = polly_client.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId=voice_id,
            Engine="generative",
        )
        # Convert the audio stream to AudioSegment
        audio = AudioSegment.from_mp3(io.BytesIO(response["AudioStream"].read()))
        return audio

    except Exception as e:
        print(f"Error synthesizing speech: {str(e)}")
        return None


def create_dialogue_audio(dialogue, output_file):
    """Convert dialogue to speech and save to file"""

    # Initialize Polly client
    polly_client = boto3.Session(
        region_name="us-east-1"  # Change to your preferred region
    ).client("polly")

    # Initialize an empty audio segment
    combined_audio = AudioSegment.empty()

    # Define voices for each speaker
    host = dialogue[0].speaker
    distinct_speakers = set(line.speaker for line in dialogue)
    guest = list(distinct_speakers.difference({host}))[0]

    logger.warning(f"VOICES: {host}, {guest}")

    speaker_voices = {
        # "Guest": "Danielle",  # Male voice
        # "Host": "Stephen",  # Female voice
        guest: "Danielle",
        host: "Stephen",
    }
    # Process each line of dialogue
    # Create a thread pool for parallel processing
    with ThreadPoolExecutor() as executor:
        # Create a list to store futures
        futures = []

        for line in dialogue:
            speaker = line.speaker
            text = line.text
            # Submit text-to-speech task to thread pool
            future = executor.submit(
                text_to_speech, text, speaker_voices[speaker], polly_client
            )
            futures.append((future, speaker))

        # Process results in order
        for i, (future, speaker) in enumerate(futures):
            # Add a small pause between lines except for first line
            if i > 0:
                combined_audio += AudioSegment.silent(duration=500)  # 500ms pause

            # Get the audio segment from the future
            audio_segment = future.result()
            if audio_segment:
                combined_audio += audio_segment
    # Export the combined audio to a file
    combined_audio.export(output_file, format="mp3")


def list_foundation_models(region: str = "us-east-1") -> dict:
    """
    List all available foundation models in Amazon Bedrock

    Returns:
        list: List of model summaries if successful, None if there's an error
    """
    try:
        # Create a Bedrock client
        bedrock_client = boto3.client("bedrock", config=Config(region_name=region))

        # Get the list of foundation models
        response = bedrock_client.list_foundation_models()

        # Extract model summaries from response
        models = response["modelSummaries"]

        return {item["modelName"]: item["modelId"] for item in models}

    except ClientError as e:
        raise


def invoke_bedrock_model(
    model_id: str,
    system_prompt: str,
    text: str,
    video_file: str | None,
    files: list[str],
    s3_url: str,
) -> Any:

    logger.info(f"Calling LLM {model_id}")

    messages = [{"role": "user", "content": [{"text": text}]}]
    if video_file:
        # Only single video is supported
        video_data = file_to_bytes(video_file)
        messages[0]["content"].insert(
            0, {"video": {"format": "mp4", "source": {"bytes": video_data}}}
        )

    if files:
        for i, file in enumerate(files):
            file_data = file_to_bytes(file)
            fmt = file.split(".")[-1].lower()
            messages[0]["content"].append(
                {
                    "document": {
                        "format": fmt,
                        "name": f"document{i}",
                        "source": {"bytes": file_data},
                    }
                }
            )

    if s3_url:
        s3_bytes = get_pdf_from_s3(s3_url)
        messages[0]["content"].append(
            {
                "document": {
                    "format": "pdf",
                    "name": "Document",
                    "source": {"bytes": s3_bytes},
                }
            }
        )
        # messages[0]["content"].append({"text": text})

    session = boto3.Session(
        region_name=AWS_REGION,
    )

    bedrock_runtime_client = session.client("bedrock-runtime")

    n_tries = 0
    result = ""

    while True:
        if n_tries > 2:
            raise Exception("Too many retries")
        try:
            result = bedrock_runtime_client.converse(
                modelId=model_id,
                messages=messages,
                system=[{"text": system_prompt}],
                inferenceConfig={"temperature": 0.2},
            )

            break
        except ClientError as e:
            logger.info(f"Exception {e}")
            if e.response["Error"]["Code"] == "ThrottlingException":
                logger.info("Throttling!. Will Sleep for 90 seconds")
                n_tries += 1
                if n_tries > 2:
                    raise e
                time.sleep(90)
            else:
                raise e
        except Exception as ex:
            logger.info(f"Exception {ex}")
            raise ex

        n_tries += 1

    return result


def file_to_bytes(file_loc: str):
    with open(file_loc, "rb") as file:
        bytes = file.read()
    return bytes
