import json
import os
from pathlib import Path


def converse(bedrock_runtime, request, output_dir=None):
    try:
        response = bedrock_runtime.converse(**request)

        if output_dir:
            save_request_and_response(request, response, output_folder=output_dir)

        return response

    except Exception as err:
        if output_dir:
            save_request_and_response(
                request=request, exception=err, output_folder=output_dir
            )
        raise err


def extract_response_text(response):
    content_list = response["output"]["message"]["content"]
    text_block = next((item for item in content_list if "text" in item), None)

    if text_block is None:
        return None

    text = text_block["text"]
    return text


def extract_response_request_id(response):
    request_id = response["ResponseMetadata"]["RequestId"]
    return request_id


def extract_response_reasoning(response):
    content_list = response["output"]["message"]["content"]
    reasoning_block = next(
        (item for item in content_list if "reasoningContent" in item), None
    )

    if reasoning_block is None:
        return None

    text = reasoning_block["reasoningContent"]["reasoningText"]["text"]
    return text


def extract_response_image(response):
    content_list = response["output"]["message"]["content"]
    image_block = next((item for item in content_list if "image" in item), None)

    if image_block is None:
        return None

    image_bytes = image_block["image"]["source"]["bytes"]
    return image_bytes


def load_audio_as_bytes(audio_path):
    """
    Load audio from disk as a byte array
    """
    with open(audio_path, "rb") as f:
        result = f.read()

    return result


def load_image_as_bytes(image_path):
    """
    Load image from disk as a byte array
    """
    with open(image_path, "rb") as f:
        result = f.read(), get_image_format(image_path)

    return result


def get_image_format(image_path):
    """
    Load image bytes from disk
    """
    # Determine the image format based on the file extension
    image_format = os.path.splitext(image_path)[1].lower().replace(".", "").lower()
    if image_format == "jpg":
        image_format = "jpeg"

    return image_format


def create_output_folder(parent_folder_path="output", folder_suffix=None):
    """
    Creates an output folder whose name is in the format "YYYY-MM-DD_HH-MM-SS
    """
    import datetime
    import os

    # Get the current date and time
    current_datetime = datetime.datetime.now()

    # Format the date and time as a string
    formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")

    folder_name = (
        f"{formatted_datetime}"
        if folder_suffix is None
        else f"{formatted_datetime}-{folder_suffix}"
    )

    # Create the full path for the new folder
    new_folder_path = os.path.join(parent_folder_path, folder_name)

    # Create the new folder
    os.makedirs(new_folder_path, exist_ok=True)

    # Absolute path to output folder
    abs_path = Path(new_folder_path).resolve()

    return abs_path


def save_dict_as_json(dict, folder_path, base_filename):
    """
    Saves the dict to disk formatted as JSON
    """
    import os

    # Create the full path for the request file
    request_file_path = os.path.join(folder_path, f"{base_filename}.json")

    serializable_dict = make_serializable(dict)

    # Write the request to the file as JSON
    with open(request_file_path, "w") as f:
        json.dump(serializable_dict, f, indent=4)


def save_text(text, folder_path, base_filename, file_extension="txt"):
    """
    Saves the text to disk
    """
    import os

    # Create the full path for the request file
    request_file_path = os.path.join(folder_path, f"{base_filename}.{file_extension}")

    # Write the request to the file as JSON
    with open(request_file_path, "w") as f:
        f.write(text)


def save_request_and_response(
    request, response=None, exception=None, output_folder="output"
):
    output_folder = create_output_folder(parent_folder_path=output_folder)
    save_dict_as_json(request, output_folder, "request")

    if exception is not None:
        if hasattr(exception, "response"):
            save_dict_as_json(exception.response, output_folder, "exception")
        else:
            save_text(str(exception), output_folder, "exception", "txt")
        return

    if response is None:
        return

    save_dict_as_json(response, output_folder, "response")

    if reasoning_text := extract_response_reasoning(response):
        save_text(reasoning_text, output_folder, "output-reasoning")

    if text := extract_response_text(response):
        save_text(text, output_folder, "output-text", "md")

    # Save any images that were generated.
    content_list = response["output"]["message"]["content"]
    image_num = 0
    for node in content_list:
        if "image" in node:
            image_num += 1
            image_bytes = node["image"]["source"]["bytes"]
            image_path = Path(output_folder) / f"output-image-{image_num}.png"
            with open(image_path, "wb") as f:
                f.write(image_bytes)

    print(f"""Outputs saved to {output_folder}""")

    return output_folder


def make_serializable(obj, omit_byte_data=False):
    """
    Convert objects to JSON-serializable format.

    Args:
        obj: Object to make serializable

    Returns:
        JSON-serializable representation of the object

    Handles binary data, complex objects, and other non-serializable types
    with appropriate fallback representations.
    """
    if isinstance(obj, dict):
        return {
            key: make_serializable(value, omit_byte_data) for key, value in obj.items()
        }
    elif isinstance(obj, list):
        return [make_serializable(item, omit_byte_data) for item in obj]
    elif isinstance(obj, bytes):
        # Convert bytes to base64 string with metadata
        import base64

        if not omit_byte_data:
            return {
                "bytes": "<bytes have been converted to Base64 for serialization>",
                "_type": "bytes",
                "_length": len(obj),
                "_data_as_base64": base64.b64encode(obj).decode("utf-8"),
            }
        else:
            return {
                "bytes": "<bytes omitted>",
            }
    elif hasattr(obj, "__dict__"):
        # Handle custom objects by converting to dict
        return {
            "_type": type(obj).__name__,
            "_data": make_serializable(obj.__dict__, omit_byte_data),
        }
    elif not isinstance(obj, (str, int, float, bool, type(None))):
        # Fallback for other non-serializable types
        return {"_type": type(obj).__name__, "_repr": str(obj)}
    else:
        return obj
