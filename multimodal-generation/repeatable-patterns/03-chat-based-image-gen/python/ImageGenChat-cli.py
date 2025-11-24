import base64
import io
import json
import logging
import os
from datetime import datetime
import random
from PIL import Image

import inquirer
from file_utils import save_base64_image

from amazon_image_gen import BedrockImageGenerator
from ImageGenChat import ImageGenChat

image_resolutions = {
    "16:9": {"width": 1280, "height": 720},
    "1:1": {"width": 1024, "height": 1024},
    "9:16": {"width": 720, "height": 1280},
}


class FileFilter(logging.Filter):
    def filter(self, record):
        # Only allow logs from test_enhance_prompt.py and ImageGenChat.py
        return record.filename in ["test_enhance_prompt.py", "ImageGenChat.py"]


def configure_logging():
    # Configure the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create a handler with your desired format
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
        )
    )

    # Add the filter to the handler
    handler.addFilter(FileFilter())

    # Add the handler to the logger
    logger.addHandler(handler)

    # Clear any existing handlers from the root logger to avoid duplicate logs
    for hdlr in logger.handlers[:]:
        if isinstance(hdlr, logging.StreamHandler) and hdlr != handler:
            logger.removeHandler(hdlr)

    return logger


def validate_int(answers, current):
    try:
        value = int(current)
        if value < 0:
            return "Please enter a positive number"
        return True
    except ValueError:
        return "Please enter a valid number"


def get_starting_input():
    questions = [
        inquirer.List(
            "model",
            message="Select a LLM to use for enhancement",
            choices=[
                "us.amazon.nova-pro-v1:0",
                "us.amazon.nova-lite-v1:0",
                "us.amazon.nova-micro-v1:0",
            ],
        ),
        inquirer.Text(
            "max_turns_to_track",
            message="Enter the number of turns to remember",
            validate=validate_int,
            default="4",
        ),
        inquirer.List(
            "enable_image_gen", message="Generate images?", choices=["No", "Yes"]
        ),
    ]
    answers = inquirer.prompt(questions)

    # If the user chose to generation images, present them with a list of resolutions to choose from.
    if answers["enable_image_gen"] == "Yes":
        resolution_questions = [
            inquirer.List(
                "resolution",
                message="Select an image resolution",
                choices=image_resolutions.keys(),
            ),
            inquirer.List(
                "quality",
                message="Select a quality setting",
                choices=["standard", "premium"],
            ),
        ]
        resolution_answers = inquirer.prompt(resolution_questions)
        selected_resolution = image_resolutions[resolution_answers["resolution"]]
        quality = resolution_answers["quality"]

    return (
        answers["model"],
        int(answers["max_turns_to_track"]),
        bool(answers["enable_image_gen"] == "Yes"),
        (
            selected_resolution
            if answers["enable_image_gen"] == "Yes"
            else image_resolutions["16:9"]
        ),
        quality if answers["enable_image_gen"] == "Yes" else "No",
    )


def save_debugging_artifacts(image_chat, output_dir):
    # Create the folder if it doesn't exist.
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Save the system prompt that was used.
    system_prompt_path = os.path.join(output_dir, "system_prompt.txt")
    with open(system_prompt_path, "w") as f:
        f.write(image_chat.system_prompt)

    # Save the conversation message structure as a JSON file.
    history_path = os.path.join(output_dir, "chat_history.json")
    with open(history_path, "w") as f:
        history_flattened = json.dumps(image_chat.chat_history, indent=2)
        f.write(history_flattened)

    # Save the conversation as a more human-readable text file.
    history_path = os.path.join(output_dir, "chat_history.md")
    with open(history_path, "w") as f:
        f.write(image_chat.get_chat_history_as_markdown())


def display_chat_response(chat_response):
    # At a minimum, there will always be a userIntent and a narrativeResponse.
    user_intent = chat_response["userIntent"]
    final_prompt = chat_response["finalPrompt"]
    negative_prompt = chat_response["negativePrompt"]
    narrative_response = chat_response["narrativeResponse"]

    next_action_options = chat_response.get("newIdeas", None)

    # Display the user intent.
    print(f"\nUser Intent:\n{user_intent}")

    # Display enhanced prompt and negative prompt.
    print(f"\nEnhanced Prompt:\n{final_prompt}")
    print(f"\nNegative Prompt:\n{negative_prompt}")

    # Display the list of suggested prompts if they exist.
    if next_action_options is not None:
        print("\nSuggestions:")
        for label in next_action_options:
            print(f"- {label}")

    # Display the model's narrative response (which may be a follow up question)
    print(f"\nNarrative Response:\n{narrative_response}")


def act_on_chat_response(
    chat_response, enable_image_gen, width, height, quality, output_dir
):
    # Generate and display an image if requested.
    if enable_image_gen:
        enhanced_prompt = chat_response["finalPrompt"]
        negative_prompt = chat_response["negativePrompt"]

        # Create the generator.
        generator = BedrockImageGenerator(output_directory=output_dir)

        # Configure the inference parameters.
        seed = random.randint(0, 2147483646)

        inference_params = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {"text": enhanced_prompt},
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "width": width,
                "height": height,
                "quality": quality,
                "cfgScale": 4.0,
                "seed": seed,
            },
        }

        # Add negative prompt if provided.
        if negative_prompt:
            inference_params["textToImageParams"]["negativeText"] = negative_prompt

        print("\nGenerating image...")
        try:
            # Generate the image(s).
            response = generator.generate_images(inference_params)

            # Check for valid images.
            images = response.get("images", [])
            if len(images) == 0:
                print("No images were generated.")

            # Check for an error message.
            if response.get("error", None) is not None:
                print(f"Error: {response['error']}")
                return

            # Save the image as a PNG and display it.
            image_base64 = images[0]
            image_bytes = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_bytes))
            image.show()

        except Exception as e:
            print(f"Sorry. Image generation failed: {e}")


def main():
    # Configure logging.
    logger = configure_logging()

    # Gather user preferences interactively.
    print("")
    selected_model, max_turns_to_track, enable_image_gen, resolution, quality = (
        get_starting_input()
    )

    print("\nEnter the prompt you would like to enhance. Enter 'q' to quit.\n")

    # Create an instance of ImageGenChat which manages conversation history and
    # user input.
    image_chat = ImageGenChat(
        turn_memory_count=max_turns_to_track,
        model_id=selected_model,
        region_name="us-east-1",
    )

    # Keep asking the user for input until they end the session.
    while True:
        # Have the user enter a prompt.
        user_input = input("\nPrompt: ")
        if user_input == "q":
            break

        # Create a folder name based on the current time.
        folder_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = os.path.join(os.path.dirname(__file__), "output", folder_name)

        chat_response = image_chat.process_user_input(user_input, output_dir=output_dir)

        save_debugging_artifacts(image_chat, output_dir)
        display_chat_response(chat_response)
        act_on_chat_response(
            chat_response,
            enable_image_gen,
            resolution["width"],
            resolution["height"],
            quality,
            output_dir,
        )


main()
