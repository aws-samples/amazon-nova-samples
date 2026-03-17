"""
Utility functions for Intelligent Document Processing with Amazon Nova Models.

This module provides reusable helpers for:
- Document format detection and content block building
- Invoking Amazon Nova via the Bedrock Converse API
- Extracting text and structured tool outputs from responses
- Document image rendering and bounding box visualization

PDF-to-image conversion uses PyMuPDF 
"""

import io
import json
import logging
import re
from pathlib import Path

from botocore.exceptions import ClientError

try:
    from PIL import Image as PILImage, ImageDraw, ImageFont
except ImportError:
    PILImage = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


# ============================================================================
# Document Format Helpers
# ============================================================================

def get_document_format(file_path):
    """Determine the document format based on file extension."""
    ext = Path(file_path).suffix.lower()
    fmt_map = {
        ".pdf": "pdf", ".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg",
        ".gif": "gif", ".webp": "webp", ".csv": "csv", ".html": "html",
        ".txt": "txt", ".md": "md", ".doc": "doc", ".docx": "docx",
        ".xls": "xls", ".xlsx": "xlsx"
    }
    return fmt_map.get(ext, "pdf")


def is_image_format(fmt):
    """Check if the format is an image type."""
    return fmt in ["png", "jpeg", "gif", "webp"]


def _sanitize_doc_name(file_path):
    """Sanitize a filename for use as a Converse API document name.
    
    The API only allows: alphanumeric, whitespace (no consecutive), hyphens,
    parentheses, and square brackets. No underscores or special characters.
    """
    raw_name = Path(file_path).stem
    doc_name = re.sub(r'[^a-zA-Z0-9\s\-\(\)\[\]]', '-', raw_name)
    doc_name = re.sub(r'-+', '-', doc_name).strip('-')
    if not doc_name or not doc_name[0].isalpha():
        doc_name = "doc-" + doc_name
    return doc_name


def _pdf_to_pil_images(file_path, max_pages=20, dpi=150):
    """Convert PDF pages to PIL Images using PyMuPDF.
    
    Args:
        file_path: Path to the PDF file
        max_pages: Maximum number of pages to convert
        dpi: Resolution for rendering
    
    Returns:
        List of PIL Images, one per page
    """
    if fitz is None:
        raise ImportError(
            "PyMuPDF is required for PDF rendering. Install with: pip install PyMuPDF"
        )
    doc = fitz.open(file_path)
    images = []
    zoom = dpi / 72.0  # PyMuPDF default is 72 DPI
    mat = fitz.Matrix(zoom, zoom)
    for page_num in range(min(len(doc), max_pages)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    doc.close()
    return images


def _pdf_to_image_bytes(file_path, max_pages=20, dpi=150):
    """Convert PDF pages to JPEG byte arrays for use as image content blocks.
    
    This is used as a fallback when a PDF cannot be processed directly by Nova
    (e.g., PDFs with ICC color profiles, transparency masks, or CMYK content).
    
    Args:
        file_path: Path to the PDF file
        max_pages: Maximum number of pages to convert
        dpi: Resolution for rendering (150 balances quality vs token cost)
    
    Returns:
        List of JPEG byte arrays, one per page
    """
    images = _pdf_to_pil_images(file_path, max_pages=max_pages, dpi=dpi)
    page_bytes = []
    for img in images:
        # Convert to RGB to ensure no CMYK/ICC issues
        img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        page_bytes.append(buf.getvalue())
    return page_bytes


def build_content_block(file_path):
    """Build the appropriate Converse API content block for a document or image file."""
    fmt = get_document_format(file_path)
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    if is_image_format(fmt):
        return {"image": {"format": fmt, "source": {"bytes": file_bytes}}}
    else:
        doc_name = _sanitize_doc_name(file_path)
        return {"document": {"name": doc_name, "format": fmt, "source": {"bytes": file_bytes}}}


def build_content_blocks_from_pdf_images(file_path, max_pages=20, dpi=150):
    """Convert a PDF to page images and return as a list of image content blocks.
    
    Use this as a fallback when build_content_block fails for problematic PDFs
    (e.g., those with ICC color profiles, CMYK, transparency, or SVG content).
    
    Each page becomes a separate image content block. The Converse API supports
    up to 20 images per request via direct upload.
    
    Args:
        file_path: Path to the PDF file
        max_pages: Maximum pages to convert (default 20)
        dpi: Rendering resolution
    
    Returns:
        List of image content block dicts ready for the Converse API
    """
    page_bytes_list = _pdf_to_image_bytes(file_path, max_pages=max_pages, dpi=dpi)
    blocks = []
    for page_bytes in page_bytes_list:
        blocks.append({"image": {"format": "jpeg", "source": {"bytes": page_bytes}}})
    return blocks


# ============================================================================
# Bedrock Converse API Helpers
# ============================================================================

def invoke_nova(bedrock_client, prompt, file_paths=None, model_id=None,
                system_prompt=None, tool_config=None, max_tokens=4096,
                temperature=0, top_p=0.9):
    """
    Send a prompt (with optional document/image files) to Amazon Nova via the Converse API.

    If a PDF fails with a ValidationException (e.g., due to ICC color profiles, CMYK,
    or transparency masks), the function automatically retries by converting PDF pages
    to JPEG images.

    Args:
        bedrock_client: boto3 bedrock-runtime client
        prompt: Text prompt for the model
        file_paths: Single file path or list of file paths to include
        model_id: Nova model ID to use
        system_prompt: Optional system prompt text
        tool_config: Optional tool configuration for structured extraction (blueprint)
        max_tokens: Maximum output tokens
        temperature: Sampling temperature (0 for deterministic)
        top_p: Nucleus sampling parameter

    Returns:
        Full Converse API response dict, or None on error
    """
    if file_paths:
        if isinstance(file_paths, (str, Path)):
            file_paths = [file_paths]
    else:
        file_paths = []

    content_blocks = [{"text": prompt}]
    for fp in file_paths:
        content_blocks.append(build_content_block(fp))

    messages = [{"role": "user", "content": content_blocks}]
    params = {
        "modelId": model_id,
        "messages": messages,
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature, "topP": top_p}
    }
    if system_prompt:
        params["system"] = [{"text": system_prompt}]
    if tool_config:
        params["toolConfig"] = tool_config
    try:
        return bedrock_client.converse(**params)
    except ClientError as e:
        error_msg = str(e)
        # Check if this is a PDF format issue — retry with image conversion
        if "ValidationException" in error_msg and "partId" in error_msg:
            pdf_files = [fp for fp in file_paths if get_document_format(fp) == "pdf"]
            if pdf_files:
                logging.warning("PDF direct upload failed, retrying with page-image conversion...")
                print(f"  ⚠ PDF format issue detected — converting pages to images...")
                # Rebuild content blocks with PDF pages as images
                content_blocks = [{"text": prompt}]
                for fp in file_paths:
                    if get_document_format(fp) == "pdf":
                        try:
                            image_blocks = build_content_blocks_from_pdf_images(fp)
                            content_blocks.extend(image_blocks)
                            print(f"  ✓ Converted {Path(fp).name} to {len(image_blocks)} page images")
                        except Exception as conv_err:
                            logging.error(f"PDF image conversion failed: {conv_err}")
                            return None
                    else:
                        content_blocks.append(build_content_block(fp))

                messages = [{"role": "user", "content": content_blocks}]
                params["messages"] = messages
                try:
                    return bedrock_client.converse(**params)
                except ClientError as e2:
                    logging.error(f"Bedrock API error (after image fallback): {e2}")
                    return None
        logging.error(f"Bedrock API error: {e}")
        return None


def extract_text(response):
    """Extract text content from a Converse API response."""
    if not response:
        return "[No response]"
    texts = [c["text"] for c in response.get("output", {}).get("message", {}).get("content", []) if "text" in c]
    return "\n".join(texts) if texts else "[No text in response]"


def extract_tool_input(response):
    """Extract structured tool use output from a Converse API response."""
    if not response:
        return None
    for c in response.get("output", {}).get("message", {}).get("content", []):
        if "toolUse" in c:
            return c["toolUse"]["input"]
    return None


def show_usage(response):
    """Print token usage information."""
    if response and "usage" in response:
        u = response["usage"]
        print(f"  Tokens - Input: {u.get('inputTokens','N/A')}, "
              f"Output: {u.get('outputTokens','N/A')}, "
              f"Total: {u.get('totalTokens','N/A')}")


# ============================================================================
# Bounding Box Visualization Helpers
# ============================================================================

def get_document_image(file_path, page=0, dpi=200):
    """Convert a document page to a PIL Image for visualization.
    
    Uses PyMuPDF for PDF files, Pillow for image files.
    """
    fmt = get_document_format(file_path)
    if fmt == "pdf":
        try:
            images = _pdf_to_pil_images(file_path, max_pages=page+1, dpi=dpi)
            return images[page] if len(images) > page else None
        except ImportError as e:
            print(f"PDF rendering not available: {e}")
            return None
    elif is_image_format(fmt):
        if PILImage is None:
            print("Pillow not installed. Install with: pip install Pillow")
            return None
        return PILImage.open(file_path).convert("RGB")
    return None


def get_color_for_field(field_name, palette=None):
    """Generate a consistent color for a field name."""
    if palette is None:
        palette = [
            (255, 0, 0), (0, 128, 0), (0, 0, 255), (255, 165, 0),
            (128, 0, 128), (0, 128, 128), (255, 0, 255), (0, 0, 128),
            (128, 128, 0), (255, 69, 0), (34, 139, 34), (70, 130, 180),
            (220, 20, 60), (184, 134, 11), (0, 191, 255), (148, 103, 189)
        ]
    return palette[hash(field_name) % len(palette)]


def _normalize_coord(val):
    """Normalize a single coordinate value to the 0.0–1.0 range.

    The model sometimes drops the leading '0.' from a decimal, producing
    values like 208 instead of 0.208 or 35 instead of 0.35. This function
    detects values > 1.0 and divides by the appropriate power of 10.
    """
    if val <= 1.0:
        return val
    # Divide by increasing powers of 10 until the value is in (0, 1]
    while val > 1.0:
        val /= 10.0
    return val


def _normalize_bboxes(fields_with_boxes):
    """
    Normalize bounding boxes from model output to consistent [x1, y1, x2, y2]
    format with values in the 0.0–1.0 range.

    Handles multiple coordinate issues the model may produce:
      - Individual coordinates > 1.0 (dropped decimal point, e.g. 208 → 0.208)
      - Entire bbox in 0–100 or 0–1000 scale
      - [x, y, width, height] instead of [x1, y1, x2, y2]

    Modifies fields in-place and prints a diagnostic summary.
    """
    # --- Step 1: Detect if ALL coords share a common non-1.0 scale -------
    # Check whether the majority of coordinates are in 0-1 or a larger scale.
    # If the majority are > 1.0 it's a uniform scale issue (0-100 or 0-1000).
    # If only a few are > 1.0 they are individual anomalies (dropped decimal).
    all_coords = []
    for field in fields_with_boxes:
        bbox = field.get("bbox")
        if bbox and len(bbox) == 4:
            all_coords.extend(bbox)

    if not all_coords:
        return

    count_gt1 = sum(1 for v in all_coords if v > 1.0)
    total = len(all_coords)

    # If the vast majority (> 75%) of coords are > 1.0, it's a uniform scale
    if count_gt1 > total * 0.75:
        max_coord = max(all_coords)
        if max_coord > 100:
            coord_scale = 1000.0
        else:
            coord_scale = 100.0
        print(f"  ℹ Detected uniform coordinate scale: 0-{int(coord_scale)} "
              f"(max value: {max_coord:.2f})")
    else:
        coord_scale = 1.0
        if count_gt1 > 0:
            print(f"  ℹ Found {count_gt1} out-of-range coordinate(s) — "
                  f"normalizing individually")

    # --- Step 2: Normalize each bbox ------------------------------------
    xywh_count = 0
    fixed_count = 0
    for field in fields_with_boxes:
        bbox = field.get("bbox")
        if not bbox or len(bbox) != 4:
            continue

        # Apply uniform scale first, then fix any remaining outliers
        coords = [v / coord_scale for v in bbox]
        # Fix individual outliers (coords still > 1.0 after uniform scaling)
        for i in range(4):
            if coords[i] > 1.0:
                coords[i] = _normalize_coord(coords[i])
                fixed_count += 1

        bx1, by1, bx2, by2 = coords

        # Detect [x, y, width, height] — the 3rd/4th values represent a
        # size rather than a position if they are smaller than the 1st/2nd
        is_xywh = False
        if bx2 < bx1 or by2 < by1:
            is_xywh = True

        if is_xywh:
            bx2 = bx1 + bx2
            by2 = by1 + by2
            xywh_count += 1

        # Clamp
        bx1 = max(0.0, min(1.0, bx1))
        by1 = max(0.0, min(1.0, by1))
        bx2 = max(0.0, min(1.0, bx2))
        by2 = max(0.0, min(1.0, by2))

        # Ensure ordering
        if bx1 > bx2:
            bx1, bx2 = bx2, bx1
        if by1 > by2:
            by1, by2 = by2, by1

        field["bbox"] = [bx1, by1, bx2, by2]

    if xywh_count:
        print(f"  ℹ Converted {xywh_count} bounding box(es) from "
              f"[x, y, w, h] → [x1, y1, x2, y2]")
    if fixed_count:
        print(f"  ℹ Fixed {fixed_count} coordinate(s) with dropped decimal point")


def draw_bounding_boxes(image, fields_with_boxes, title="", debug=False):
    """
    Draw bounding boxes on a document image.

    Args:
        image: PIL Image
        fields_with_boxes: list of dicts with keys: field_name, value, bbox
            bbox may be [x1,y1,x2,y2] or [x,y,w,h] in 0-1, 0-100, or 0-1000 scale.
            All formats are auto-detected and normalized.
        title: optional title for the visualization
        debug: if True, print raw vs normalized coordinates for every field

    Returns:
        Tuple of (annotated PIL Image, legend_items list)
    """
    if PILImage is None:
        raise ImportError("Pillow is required for bounding box visualization")

    # Work on a copy so we don't mutate the caller's data
    import copy
    fields_with_boxes = copy.deepcopy(fields_with_boxes)

    # Auto-detect scale and convert [x,y,w,h] → [x1,y1,x2,y2] in 0-1 range
    _normalize_bboxes(fields_with_boxes)

    img = image.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except (OSError, IOError):
            font = ImageFont.load_default()

    legend_items = []

    for field in fields_with_boxes:
        name = field.get("field_name", "unknown")
        value = str(field.get("value", ""))[:40]
        bbox = field.get("bbox", None)

        if not bbox or len(bbox) != 4:
            continue

        color = get_color_for_field(name)

        bx1, by1, bx2, by2 = bbox

        # Convert fractional coords to pixel coords
        x1 = int(bx1 * w)
        y1 = int(by1 * h)
        x2 = int(bx2 * w)
        y2 = int(by2 * h)

        # Ensure proper ordering
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1

        if debug:
            print(f"  {name}: raw_bbox={field.get('_raw_bbox', bbox)} "
                  f"→ norm=[{bx1:.4f},{by1:.4f},{bx2:.4f},{by2:.4f}] "
                  f"→ px=[{x1},{y1},{x2},{y2}]")

        # Skip degenerate boxes
        if x1 == x2 or y1 == y2:
            continue

        # Draw rectangle
        for offset in range(2):  # thicker border
            draw.rectangle([x1-offset, y1-offset, x2+offset, y2+offset], outline=color)

        # Draw label — place above box when space allows, otherwise inside top edge
        label = f"{name}: {value}"
        # Use anchor="lt" (left-top) so xy is the top-left corner of the text,
        # keeping textbbox and draw.text perfectly aligned.
        label_y = y1 - 16 if y1 >= 16 else y1 + 2
        text_bbox = draw.textbbox((x1, label_y), label, font=font, anchor="lt")
        draw.rectangle(
            [text_bbox[0] - 2, text_bbox[1] - 1, text_bbox[2] + 2, text_bbox[3] + 1],
            fill=color,
        )
        draw.text((x1, label_y), label, fill="white", font=font, anchor="lt")

        legend_items.append((name, value, color))

    if title:
        draw.text((10, 10), title, fill="red", font=font)

    return img, legend_items


# ============================================================================
# Extended Thinking Helpers
# ============================================================================

def invoke_nova_with_reasoning(bedrock_client, prompt, file_paths=None,
                                model_id=None, system_prompt=None,
                                reasoning_effort="medium", max_tokens=10000,
                                tool_config=None):
    """
    Invoke Amazon Nova with extended thinking (reasoning) enabled.

    Extended thinking is supported by Nova 2 Lite. It enables deeper reasoning
    for complex problems via the reasoningConfig parameter.

    Args:
        bedrock_client: boto3 bedrock-runtime client
        prompt: Text prompt for the model
        file_paths: Single file path or list of file paths to include
        model_id: Nova model ID (defaults to Nova 2 Lite which supports reasoning)
        system_prompt: Optional system prompt text
        reasoning_effort: "low", "medium", or "high"
        max_tokens: Maximum output tokens (ignored when effort="high")
        tool_config: Optional tool configuration

    Returns:
        Full Converse API response dict, or None on error
    """
    if model_id is None:
        model_id = "us.amazon.nova-2-lite-v1:0"

    content_blocks = [{"text": prompt}]
    if file_paths:
        if isinstance(file_paths, (str, Path)):
            file_paths = [file_paths]
        for fp in file_paths:
            content_blocks.append(build_content_block(fp))

    messages = [{"role": "user", "content": content_blocks}]

    params = {
        "modelId": model_id,
        "messages": messages,
        "additionalModelRequestFields": {
            "reasoningConfig": {
                "type": "enabled",
                "maxReasoningEffort": reasoning_effort
            }
        }
    }

    # When effort is "high", temperature/topP/maxTokens must be unset
    if reasoning_effort != "high":
        params["inferenceConfig"] = {
            "maxTokens": max_tokens,
            "temperature": 0.7,
            "topP": 0.9
        }

    if system_prompt:
        params["system"] = [{"text": system_prompt}]
    if tool_config:
        params["toolConfig"] = tool_config

    try:
        return bedrock_client.converse(**params)
    except ClientError as e:
        error_msg = str(e)
        # Check if this is a PDF format issue — retry with image conversion
        if "ValidationException" in error_msg and "partId" in error_msg and file_paths:
            pdf_files = [fp for fp in file_paths if get_document_format(fp) == "pdf"]
            if pdf_files:
                logging.warning("PDF direct upload failed in reasoning mode, retrying with images...")
                print(f"  ⚠ PDF format issue detected — converting pages to images...")
                content_blocks = [{"text": prompt}]
                for fp in file_paths:
                    if get_document_format(fp) == "pdf":
                        try:
                            image_blocks = build_content_blocks_from_pdf_images(fp)
                            content_blocks.extend(image_blocks)
                            print(f"  ✓ Converted {Path(fp).name} to {len(image_blocks)} page images")
                        except Exception as conv_err:
                            logging.error(f"PDF image conversion failed: {conv_err}")
                            return None
                    else:
                        content_blocks.append(build_content_block(fp))
                params["messages"] = [{"role": "user", "content": content_blocks}]
                try:
                    return bedrock_client.converse(**params)
                except ClientError as e2:
                    logging.error(f"Bedrock API error (after image fallback): {e2}")
                    return None
        logging.error(f"Bedrock API error: {e}")
        return None


def extract_reasoning_and_text(response):
    """
    Extract both reasoning content and text from an extended thinking response.

    Returns:
        Tuple of (reasoning_text, answer_text)
    """
    if not response:
        return "[No response]", "[No response]"

    reasoning = []
    texts = []
    for c in response.get("output", {}).get("message", {}).get("content", []):
        if "reasoningContent" in c:
            rt = c["reasoningContent"].get("reasoningText", {}).get("text", "[REDACTED]")
            reasoning.append(rt)
        elif "text" in c:
            texts.append(c["text"])

    return "\n".join(reasoning) if reasoning else "[No reasoning]", \
           "\n".join(texts) if texts else "[No text]"


# ============================================================================
# Built-in Tool Helpers
# ============================================================================

CODE_INTERPRETER_TOOL = {
    "tools": [{
        "systemTool": {
            "name": "nova_code_interpreter"
        }
    }]
}


def invoke_nova_with_code_interpreter(bedrock_client, messages, model_id=None,
                                       system_prompt=None, max_tokens=8000):
    """
    Invoke Amazon Nova with the built-in code interpreter tool.

    The code interpreter allows Nova to generate and execute Python code
    in an isolated sandbox, returning stdout/stderr results.

    Args:
        bedrock_client: boto3 bedrock-runtime client
        messages: Full messages list (supports multi-turn for tool results)
        model_id: Nova model ID
        system_prompt: Optional system prompt text
        max_tokens: Maximum output tokens

    Returns:
        Full Converse API response dict, or None on error
    """
    if model_id is None:
        model_id = "us.amazon.nova-2-lite-v1:0"

    params = {
        "modelId": model_id,
        "messages": messages,
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0, "topP": 0.9},
        "toolConfig": CODE_INTERPRETER_TOOL
    }

    if system_prompt:
        params["system"] = [{"text": system_prompt}]

    try:
        return bedrock_client.converse(**params)
    except ClientError as e:
        logging.error(f"Bedrock API error: {e}")
        return None


def extract_code_interpreter_results(response):
    """
    Extract code interpreter tool use and results from a response.

    Returns:
        List of dicts with keys: code, tool_use_id, and optionally result
    """
    if not response:
        return []

    results = []
    for c in response.get("output", {}).get("message", {}).get("content", []):
        if "toolUse" in c:
            tu = c["toolUse"]
            if tu.get("name") == "nova_code_interpreter" or tu.get("type") == "server_tool_use":
                results.append({
                    "code": tu.get("input", {}).get("code", ""),
                    "tool_use_id": tu.get("toolUseId", ""),
                    "type": "tool_use"
                })
        elif "toolResult" in c:
            tr = c["toolResult"]
            result_text = ""
            for content in tr.get("content", []):
                if "text" in content:
                    result_text = content["text"]
            results.append({
                "result": result_text,
                "tool_use_id": tr.get("toolUseId", ""),
                "status": tr.get("status", ""),
                "type": "tool_result"
            })
        elif "text" in c:
            results.append({"text": c["text"], "type": "text"})

    return results