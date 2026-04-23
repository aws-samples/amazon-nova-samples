import base64
import io
import json
import matplotlib.pyplot as plt
import numpy as np
import textwrap
from PIL import Image
from c2pa import Reader
from typing import Dict, Any, Optional, Tuple
from matplotlib.patches import Rectangle


# Define function to save the output
def save_image(base64_image, output_file):
    image_bytes = base64.b64decode(base64_image)
    image = Image.open(io.BytesIO(image_bytes))
    image.save(output_file)


# Define different types of plot function
def plot_images(
    generated_images, ref_image_path=None, original_title=None, processed_title=None
):
    if ref_image_path:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    else:
        fig, axes = plt.subplots(1, 1, figsize=(6, 5))
        axes = [axes]

    if ref_image_path:
        reference_image = Image.open(ref_image_path)
        max_size = (512, 512)
        reference_image.thumbnail(max_size)
        axes[0].imshow(np.array(reference_image))
        axes[0].set_title(original_title or "Reference Image")
        axes[0].axis("off")

    generated_image_index = 1 if ref_image_path else 0
    axes[generated_image_index].imshow(np.array(generated_images[0]))
    axes[generated_image_index].set_title(processed_title or "Processed Image")
    axes[generated_image_index].axis("off")

    plt.tight_layout()
    plt.show()


def plot_image_conditioning(
    ref_image_path,
    base_images=None,
    prompt=None,
    generated_images=None,
    control_strength_values=None,
    comparison_mode=False,
):
    if comparison_mode:
        num_images = len(control_strength_values) + 1
        fig, axes = plt.subplots(1, num_images, figsize=((num_images) * 4, 5))
    else:
        fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    reference_image = Image.open(ref_image_path)
    max_size = (300, 300)
    reference_image.thumbnail(max_size)

    axes[0].imshow(np.array(reference_image))
    axes[0].set_title("Condition Image")
    axes[0].axis("off")

    if comparison_mode:
        if generated_images is None or len(generated_images) != len(
            control_strength_values
        ):
            raise ValueError(
                "The length of generated_images must match the length of control_strength_values."
            )
        for i, (image, strength) in enumerate(
            zip(generated_images, control_strength_values), start=1
        ):
            axes[i].imshow(np.array(image))
            axes[i].set_title(f"Control Strength: {strength}")
            axes[i].axis("off")
    else:
        axes[1].imshow(np.array(base_images[0]))
        axes[1].set_title("Result of Conditioning")
        axes[1].axis("off")

    if prompt:
        print("Prompt:{}\n".format(prompt))

    plt.tight_layout()
    plt.show()


def plot_color_conditioning(base_images, color_codes, prompt, ref_image_path=None):
    if ref_image_path:
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    else:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Plot Hex Color
    num_colors = len(color_codes)
    color_width = 0.8 / num_colors
    for i, color_code in enumerate(color_codes):
        x = i * color_width
        rect = plt.Rectangle(
            (x, 0), color_width, 1, facecolor=f"{color_code}", edgecolor="white"
        )
        axes[0].add_patch(rect)
    axes[0].set_xlim(0, 0.8)
    axes[0].set_ylim(0, 1)
    axes[0].set_title("Color Codes")
    axes[0].axis("off")

    if ref_image_path:
        reference_image = Image.open(ref_image_path)
        max_size = (300, 300)
        reference_image.thumbnail(max_size)
        axes[1].imshow(np.array(reference_image))
        axes[1].set_title("Reference Image")
        axes[1].axis("off")
        image_index = 2
    else:
        image_index = 1

    axes[image_index].imshow(np.array(base_images[0]))
    if ref_image_path:
        axes[image_index].set_title(f"Image Generated Based on Reference")
    else:
        axes[image_index].set_title(f"Image Generated")
    axes[image_index].axis("off")

    print(f"Prompt: {prompt}\n")
    plt.tight_layout()
    plt.show()


def create_color_palette_image(
    colors, width=400, height=50, border_color="#cccccc", border_width=2
):
    """
    Create a color palette image from a list of hex color codes.

    Args:
        colors (list): List of hex color codes (e.g., ["#FFFFFF", "#B066AC"])
        width (int): Total width of the image in pixels
        height (int): Total height of the image in pixels
        border_color (str): Hex color code for the border
        border_width (int): Width of the border in pixels

    Returns:
        PIL.Image: Color palette image with border
    """
    # Convert border color from hex to RGB
    border_rgb = tuple(int(border_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))

    # Create image with border (add border_width*2 to dimensions to account for borders)
    total_width = width + (border_width * 2)
    total_height = height + (border_width * 2)
    img = Image.new("RGB", (total_width, total_height), border_rgb)

    # Calculate the width of each color segment
    num_colors = len(colors)
    segment_width = width // num_colors

    # Convert hex colors to RGB
    rgb_colors = [
        tuple(int(color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
        for color in colors
    ]

    # Create the inner image (without border)
    inner_img = Image.new("RGB", (width, height))

    # Draw each color segment
    for i, color in enumerate(rgb_colors):
        start_x = i * segment_width
        end_x = start_x + segment_width if i < num_colors - 1 else width

        # Create and paste each color segment
        segment = Image.new("RGB", (end_x - start_x, height), color)
        inner_img.paste(segment, (start_x, 0))

    # Paste the inner image onto the bordered image
    img.paste(inner_img, (border_width, border_width))

    return img


def plot_images_for_comparison(
    ref_image_path=None,
    base_images=None,
    custom_images=None,
    generated_images=None,
    labels=None,
    prompt=None,
    comparison_mode=False,
    title_prefix="Image",
):
    if comparison_mode:
        num_images = len(generated_images) + (1 if ref_image_path else 0)
        _, axes = plt.subplots(1, num_images, figsize=(num_images * 4, 5))
    else:
        _, axes = plt.subplots(1, 3, figsize=(15, 5))

    if not isinstance(axes, np.ndarray):
        axes = [axes]

    if ref_image_path:
        reference_image = Image.open(ref_image_path)
        max_size = (300, 300)
        reference_image.thumbnail(max_size)

        axes[0].imshow(np.array(reference_image))
        axes[0].set_title("Reference Image")
        axes[0].axis("off")

    if comparison_mode:
        start_index = 1 if ref_image_path else 0
        for i, img in enumerate(generated_images):
            axes[i + start_index].imshow(np.array(img))
            title = f"{title_prefix} {labels[i]}" if labels else f"{title_prefix} {i+1}"
            axes[i + start_index].set_title(title)
            axes[i + start_index].axis("off")
    else:
        if base_images:
            axes[1].imshow(np.array(base_images[0]))
            axes[1].set_title("Without Reference")
            axes[1].axis("off")

        if custom_images:
            axes[2].imshow(np.array(custom_images[0]))
            axes[2].set_title("With Reference")
            axes[2].axis("off")

    if prompt:
        print(f"Prompt: {prompt}\n")
    plt.tight_layout()
    plt.show()

def save_binary_image(base64_image: str, output_path: str) -> None:
    """
    Save a base64 encoded image as binary file, preserving C2PA metadata.

    Args:
        base64_image (str): Base64 encoded image data
        output_path (str): Path where to save the image
    """
    image_bytes = base64.b64decode(base64_image)
    with open(output_path, 'wb') as f:
        f.write(image_bytes)

def extract_c2pa_metadata(image_path: str) -> Dict[str, Any]:
    """
    Extract C2PA metadata from an image file.

    Args:
        image_path (str): Path to the image file

    Returns:
        dict: Dictionary containing manifest store and active manifest information
    """
    try:
        reader = Reader.from_file(image_path)
        manifest_store = reader.json()
        active_manifest = reader.get_active_manifest()

        return {
            "manifest_store": json.loads(manifest_store),
            "active_manifest": active_manifest
        }
    except Exception as e:
        print(f"Error extracting C2PA metadata: {str(e)}")

    return {}

def display_image_with_metadata(image_path: str, ref_image_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Display an image and its C2PA metadata using the utils.plot_images function.

    Args:
        image_path (str): Path to the image file
        ref_image_path (str, optional): Path to a reference image for comparison

    Returns:
        dict: C2PA metadata information
    """
    # Extract C2PA metadata
    c2pa_info = extract_c2pa_metadata(image_path)

    print("\nC2PA Manifest Store:")
    print(json.dumps(c2pa_info.get("manifest_store", {}), indent=2))

    # Open the image using PIL
    image = Image.open(image_path)

    # Use plot_images from utils to display
    plot_images([image], ref_image_path=ref_image_path,
                original_title="Reference Image" if ref_image_path else None,
                processed_title="Generated Image with C2PA Metadata")

    return c2pa_info

def get_manifest_info(manifest_store: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key information from a manifest store.

    Args:
        manifest_store (dict): The C2PA manifest store

    Returns:
        dict: Dictionary containing key manifest information
    """
    info = {}

    try:
        active_manifest_id = manifest_store.get("active_manifest")
        if not active_manifest_id:
            return info

        active_manifest = manifest_store["manifests"][active_manifest_id]

        info["manifest_id"] = active_manifest_id
        info["generator"] = active_manifest.get("claim_generator")
        info["generator_info"] = active_manifest.get("claim_generator_info")
        info["signature"] = active_manifest.get("signature_info")

        # Extract creation info from assertions
        for assertion in active_manifest.get("assertions", []):
            if assertion["label"] == "c2pa.actions":
                actions = assertion["data"].get("actions", [])
                for action in actions:
                    if action["action"] in ["c2pa.created", "c2pa.edited"]:
                        info["action"] = action["action"]
                        info["timestamp"] = action["when"]
                        info["software_agent"] = action.get("softwareAgent")
                        info["is_ai_generated"] = (
                            action.get("digitalSourceType") == 
                            "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
                        )
                        break
    except Exception as e:
        print(f"Error extracting manifest info: {str(e)}")

    return info

def verify_c2pa_metadata(image_path: str) -> Dict[str, Any]:
    """
    Verify C2PA metadata in an image and return verification results.

    Args:
        image_path (str): Path to the image file

    Returns:
        dict: Verification results including source, creation, and signature info
    """
    try:
        # Extract C2PA metadata
        c2pa_info = extract_c2pa_metadata(image_path)
        manifest_store = c2pa_info.get("manifest_store", {})

        # Get the active manifest
        active_manifest_id = manifest_store.get("active_manifest")
        if not active_manifest_id:
            return {
                'verified': False,
                'reason': 'No active manifest found'
            }

        # Get manifest info
        manifest_info = get_manifest_info(manifest_store)

        verification_result = {
            'verified': True,
            'source': {
                'generator': manifest_info.get('generator'),
                'generator_info': manifest_info.get('generator_info')
            },
            'creation': {
                'time': manifest_info.get('timestamp'),
                'ai_generated': manifest_info.get('is_ai_generated'),
                'action': manifest_info.get('action')
            },
            'signature': manifest_info.get('signature'),
            'manifest_id': manifest_info.get('manifest_id')
        }

        return verification_result

    except Exception as e:
        return {
            'verified': False,
            'reason': f'Error verifying image: {str(e)}'
        }

def track_edit_provenance(original_path: str, edited_path: str, figsize: Tuple[int, int] = (22, 14)) -> Dict[str, Any]:
    """
    Compare Content Credentials before and after editing and visualize the changes.

    Args:
        original_path (str): Path to the original image
        edited_path (str): Path to the edited image
        figsize (tuple): Figure size for the visualization

    Returns:
        dict: Comparison information between original and edited manifests
    """

    try:
        # Read manifests from both images
        original_store = extract_c2pa_metadata(original_path)["manifest_store"]
        edited_store = extract_c2pa_metadata(edited_path)["manifest_store"]

        # Create figure and axes with increased size for better readability
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        fig.patch.set_facecolor('white')

        # Helper function to format and identify lines to highlight
        def process_json(json_obj: Dict[str, Any], is_edited: bool = False) -> Tuple[list, list]:
            json_str = json.dumps(json_obj, indent=2)
            # Wrap long lines for better readability
            wrapped_lines = []
            for line in json_str.split('\n'):
                if len(line) > 80:
                    # Preserve indentation for wrapped lines
                    indent = len(line) - len(line.lstrip())
                    indent_str = ' ' * indent
                    wrapped = textwrap.wrap(line.lstrip(), width=80-indent, 
                                          subsequent_indent=indent_str + '  ')
                    wrapped_lines.extend(indent_str + l for l in wrapped)
                else:
                    wrapped_lines.append(line)

            highlight_terms = [
                'urn:uuid:',
                '"action":',
                '"when":',
                '"time":',
                '"instance_id":',
                '"signature_info":'
            ]

            highlight_indices = []
            for i, line in enumerate(wrapped_lines):
                if is_edited:
                    if any(term in line for term in highlight_terms) or '"c2pa.edited"' in line:
                        highlight_indices.append(i)
                else:
                    if any(term in line for term in highlight_terms) or '"c2pa.created"' in line:
                        highlight_indices.append(i)

            return wrapped_lines, highlight_indices

        # Process both manifests
        original_lines, original_highlights = process_json(original_store)
        edited_lines, edited_highlights = process_json(edited_store, is_edited=True)

        # Clear and set up axes
        for ax, title in [(ax1, 'Original Manifest'), (ax2, 'Edited Manifest')]:
            ax.clear()
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(title, pad=20, fontsize=14, fontweight='bold')

        # Calculate text properties
        font_size = 12
        line_height = 1.3
        text_left_margin = 0.05

        # Display and highlight text for original manifest
        for i, line in enumerate(original_lines):
            y_pos = len(original_lines) - i - 1
            if i in original_highlights:
                rect = Rectangle((-0.02, y_pos-0.2), 1.04, 1.0,
                               facecolor='lightblue', alpha=0.3,
                               transform=ax1.transData)
                ax1.add_patch(rect)
            ax1.text(text_left_margin, y_pos, line, 
                    fontfamily='monospace', 
                    fontsize=font_size,
                    ha='left', 
                    va='center')

        # Display and highlight text for edited manifest
        for i, line in enumerate(edited_lines):
            y_pos = len(edited_lines) - i - 1
            if i in edited_highlights:
                rect = Rectangle((-0.02, y_pos-0.2), 1.04, 1.0,
                               facecolor='yellow', alpha=0.3,
                               transform=ax2.transData)
                ax2.add_patch(rect)
            ax2.text(text_left_margin, y_pos, line, 
                    fontfamily='monospace', 
                    fontsize=font_size,
                    ha='left', 
                    va='center')

        # Set axis limits with additional padding
        max_lines = max(len(original_lines), len(edited_lines))
        for ax in [ax1, ax2]:
            ax.set_ylim(-1, max_lines + 1)
            ax.set_xlim(-0.1, 1.1)
            for spine in ax.spines.values():
                spine.set_visible(False)

        # Adjust layout to prevent overlap
        plt.tight_layout(pad=3.0)
        plt.show()

        # Compare images visually
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 8))
        fig.suptitle('Original vs Edited Image', fontsize=14)

        # Display original image
        img1 = plt.imread(original_path)
        ax1.imshow(img1)
        ax1.set_title('Original Image')
        ax1.axis('off')

        # Display edited image
        img2 = plt.imread(edited_path)
        ax2.imshow(img2)
        ax2.set_title('Edited Image')
        ax2.axis('off')

        plt.tight_layout()
        plt.show()

        # Get manifest information for both images
        original_info = get_manifest_info(original_store)
        edited_info = get_manifest_info(edited_store)

        return {
            'original': {
                'manifest_id': original_info['manifest_id'],
                'creation_time': original_info['timestamp'],
                'manifest': original_store
            },
            'edited': {
                'manifest_id': edited_info['manifest_id'],
                'creation_time': edited_info['timestamp'],
                'manifest': edited_store
            }
        }

    except Exception as e:
        return {
            'error': f'Error comparing provenance: {str(e)}'
        }