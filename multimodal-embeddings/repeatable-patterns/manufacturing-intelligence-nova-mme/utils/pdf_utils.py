"""PDF to PNG conversion utility."""

import os
from pathlib import Path
from pdf2image import convert_from_path


def pdf_to_png(pdf_path, output_dir=None, dpi=200):
    """Convert a PDF file to individual PNG page images.

    Returns list of output file paths.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' not found.")
        return []

    if output_dir is None:
        output_dir = os.path.splitext(pdf_path)[0] + "_pages"

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    pages = convert_from_path(pdf_path, dpi=dpi)
    output_paths = []
    for i, page in enumerate(pages, 1):
        output_path = os.path.join(output_dir, f"page_{i:03d}.png")
        page.save(output_path, "PNG")
        output_paths.append(output_path)
        print(f"Saved: {output_path}")

    print(f"\nConverted {len(pages)} pages from '{pdf_path}'")
    return output_paths
