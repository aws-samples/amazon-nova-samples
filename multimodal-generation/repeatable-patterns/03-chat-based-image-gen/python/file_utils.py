import base64
import io
import os

from PIL import Image


def save_base64_image(base64_image, output_directory, base_name="image", suffix="_1"):
    """
    Saves a base64 encoded image to a specified output directory with a timestamp and a suffix.

    Args:
        base64_image (str): The base64 encoded image string.
        output_directory (str): The directory where the image will be saved.
        suffix (str, optional): A suffix to be added to the filename. Defaults to "_1".
    Returns:
        PIL.Image.Image: The Pillow Image object representing the saved image.
    """
    image_bytes = base64.b64decode(base64_image)
    image = Image.open(io.BytesIO(image_bytes))
    save_image(image, output_directory, base_name, suffix)
    return image


def save_image(image, output_directory, base_name="image", suffix="_1"):
    """
    Saves a Pillow Image object to a specified output directory with a timestamp and a suffix.

    Args:
        image (PIL.Image.Image): The Pillow Image object to be saved.
        output_directory (str): The directory where the image will be saved.
        suffix (str, optional): A suffix to be added to the filename. Defaults to "_1".
    Returns:
        None
    """
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    file_name = f"{base_name}{suffix}.png"
    file_path = os.path.join(output_directory, file_name)
    image.save(file_path)


def save_base64_images(base64_images, output_directory, base_name="image"):
    """
    Saves a list of base64 encoded images to a specified output directory.

    Args:
        base64_images (list): A list of base64 encoded image strings.
        output_directory (str): The directory where the images will be saved.
    Returns:
        An array of Pillow Image objects representing the saved images.
    """
    images = []
    for i, base64_image in enumerate(base64_images):
        image = save_base64_image(
            base64_image, output_directory, base_name=base_name, suffix=f"_{i+1}"
        )
        images.append(image)

    return images
