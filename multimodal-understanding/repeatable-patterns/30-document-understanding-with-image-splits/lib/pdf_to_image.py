from pdf2image import convert_from_path
from PIL import Image
import base64
import io

def convert_pdf_to_png_images(pdf_path):
    """
    Convert a PDF to an array of base64 encoded images (PNG format), with images resized
    to maintain aspect ratio with longest edge being 2000 pixels.
    
    Args:
        pdf_path (str): Path to the PDF file
    
    Returns:
        list: Array of base64 encoded PNG images
    """
    # Convert PDF pages to images
    set_resolution = 2000
    images = convert_from_path(pdf_path)
    base64_images = []
    
    # Process each page
    for i, image in enumerate(images):
        # Calculate new dimensions while maintaining aspect ratio
        width, height = image.size
        if width > height:
            new_width = set_resolution
            new_height = int(height * (set_resolution / width))
        else:
            new_height = set_resolution
            new_width = int(width * (set_resolution / height))
        
        # Resize image
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to base64
        buffer = io.BytesIO()
        resized_image.save(buffer, format='PNG')
        base64_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
        base64_images.append(base64_string)
        
        print(f'Processed page {i+1}')
    
    return base64_images