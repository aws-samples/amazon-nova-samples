"""
main.py
"""

# Standard library imports
import base64
from typing import List, Optional, Tuple

# Third-party imports
import gradio as gr
from loguru import logger

# Local imports
from constants import (
    APP_TITLE,
    AWS_REGION,
    CHARACTER_LIMIT,
    ERROR_MESSAGE_NO_INPUT,
    ERROR_MESSAGE_TOO_LONG,
    UI_ALLOW_FLAGGING,
    UI_API_NAME,
    UI_CACHE_EXAMPLES,
    UI_CONCURRENCY_LIMIT,
    UI_DESCRIPTION,
    UI_INPUTS,
    UI_OUTPUTS,
    UI_SHOW_API,
)

from schema import MediumDialogue, ShortDialogue
from utils import (
    create_dialogue_audio,
    generate_script,
    generate_script_with_outline,
    get_pdf_from_s3,
    parse_url,
    read_pdfs,
    list_foundation_models,
)


def generate_podcast(
    model_name: str,
    video_file: str,
    files: List[str],
    url: Optional[str],
    s3_url: Optional[str],
    question: str,
    tone: str,
    length: str,
    # language: str,
) -> Tuple[str, str]:
    """Generate the audio and transcript from the PDFs and/or URL."""

    text = ""
    model_map = list_foundation_models(AWS_REGION)
    model_id = model_map[model_name]

    # Check if at least one input is provided
    if not files and not url and not s3_url and not video_file:
        raise gr.Error(ERROR_MESSAGE_NO_INPUT)

    # Process URL if provided
    if url:
        try:
            url_text = parse_url(url)
            text += "\n\n" + url_text
        except ValueError as e:
            raise gr.Error(str(e))

    # Check total character count
    if len(text) > CHARACTER_LIMIT:
        raise gr.Error(ERROR_MESSAGE_TOO_LONG)

    # Call the LLM
    if length == "Long":
        llm_output = generate_script_with_outline(
            model_id,
            text,
            question,
            tone,
            video_file,
            files,
            s3_url,
            MediumDialogue,
        )
    else:
        llm_output = generate_script(
            model_id, text, question, tone, video_file, files, s3_url, ShortDialogue
        )

    # Process the dialogue
    transcript = "\n\n".join(
        [item.speaker + ": " + item.text for item in llm_output.dialogue]
    )

    create_dialogue_audio(llm_output.dialogue, "dialogue_output.mp3")
    logger.info("Audio created!")
    return "dialogue_output.mp3", transcript


demo = gr.Interface(
    # title=APP_TITLE,
    title=f"<img src='data:image/svg+xml;base64,{base64.b64encode(open('logo.svg', 'rb').read()).decode('utf-8')}' style='height: 40px; display: inline; margin-left: 10px; vertical-align: middle;'> {APP_TITLE} ",
    description=UI_DESCRIPTION,
    fn=generate_podcast,
    # theme=gr.themes.Monochrome(primary_hue=gr.themes.colors.orange),
    theme=gr.themes.Ocean(
        primary_hue=gr.themes.colors.orange,
        neutral_hue=gr.themes.colors.amber,
        secondary_hue=gr.themes.colors.orange,
    ),
    inputs=[
        gr.Dropdown(
            label=UI_INPUTS["models"]["label"],
            choices=list(list_foundation_models(AWS_REGION).keys()),
            value=UI_INPUTS["models"]["value"],
        ),
        gr.File(
            label=UI_INPUTS["video_upload"]["label"],  # Step 1: File upload
            file_types=UI_INPUTS["video_upload"]["file_types"],
            file_count=UI_INPUTS["video_upload"]["file_count"],
        ),
        gr.File(
            label=UI_INPUTS["file_upload"]["label"],  # Step 1: File upload
            file_types=UI_INPUTS["file_upload"]["file_types"],
            file_count=UI_INPUTS["file_upload"]["file_count"],
        ),
        gr.Textbox(
            label=UI_INPUTS["url"]["label"],  # Step 2: URL
            placeholder=UI_INPUTS["url"]["placeholder"],
        ),
        gr.Textbox(
            label=UI_INPUTS["s3"]["label"],  # Step 2: URL
            placeholder=UI_INPUTS["s3"]["placeholder"],
        ),
        gr.Textbox(label=UI_INPUTS["question"]["label"]),  # Step 3: Question
        gr.Dropdown(
            label=UI_INPUTS["tone"]["label"],  # Step 4: Tone
            choices=UI_INPUTS["tone"]["choices"],
            value=UI_INPUTS["tone"]["value"],
        ),
        gr.Dropdown(
            label=UI_INPUTS["length"]["label"],  # Step 5: Length
            choices=UI_INPUTS["length"]["choices"],
            value=UI_INPUTS["length"]["value"],
        ),
    ],
    outputs=[
        gr.Audio(
            label=UI_OUTPUTS["audio"]["label"], format=UI_OUTPUTS["audio"]["format"]
        ),
        gr.Textbox(
            label=UI_OUTPUTS["transcript"]["label"],
            interactive=False,
            show_copy_button=True,
        ),
    ],
    allow_flagging=UI_ALLOW_FLAGGING,
    api_name=UI_API_NAME,
    # theme=gr.themes.Ocean(),
    concurrency_limit=UI_CONCURRENCY_LIMIT,
    cache_examples=UI_CACHE_EXAMPLES,
)

if __name__ == "__main__":
    demo.launch(show_api=UI_SHOW_API, server_name="0.0.0.0")
