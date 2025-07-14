#!/usr/bin/env python3
from random import randint
from amazon_image_gen import BedrockImageGenerator
import file_utils
import logging
import base64
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def main():
        
    # Edit these values to experiment with your own images.
    source_image_path = "../images/vto-images/vto_image_mask_source.jpg"
    mask_image_path = "../images/vto-images/vto_image_mask_maskimage.png"
    reference_image_path = "../images/vto-images/vto_image_mask_reference.jpg"

    # Load the source image from disk.
    with open(source_image_path, "rb") as image_file:
        source_image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
    # Load the mask image from disk.
    with open(mask_image_path, "rb") as image_file:
       mask_image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
    # Load the reference image from disk.
    with open(reference_image_path, "rb") as image_file:
        reference_image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
    
    inference_params = {
        "taskType": "VIRTUAL_TRY_ON",
        "virtualTryOnParams": {
            "sourceImage": source_image_base64,
            "referenceImage": reference_image_base64,
            # Use the "IMAGE" mask type
            "maskType": "IMAGE",
            # Configure the image mask
            "imageBasedMask": {"maskImage":mask_image_base64},
            # When the try-on item is small, using the "DETAILED" merge style is
            # almost always the best choice.
            "mergeStyle": "DETAILED",
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "quality": "standard",
            "cfgScale": 6.5,
            "seed": randint(0, 2147483646),
        },
    }

    # Define an output directory with a unique name.
    generation_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_directory = f"output/{generation_id}"

    # Create the generator.
    generator = BedrockImageGenerator(
            output_directory=output_directory
        )
    # Generate the image(s).
    response = generator.generate_images(inference_params)

    if "images" in response:
        # Save and display each image
        file_utils.save_base64_images(response["images"], output_directory, "image")

if __name__ == "__main__":
    main()

