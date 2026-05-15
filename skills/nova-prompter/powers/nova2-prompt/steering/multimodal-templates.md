# Nova 2 Lite — Multimodal Use Case Templates

This steering file contains the complete library of multimodal prompt templates for Nova 2 Lite. Load this file only after confirming the user's use case is multimodal (STEP 2 of the main workflow).

Templates are grouped by sub-type. All instructions below go in the **user prompt** — never the system prompt — per the Nova 2 Lite multimodal system prompt limitation.

---

## OCR

```
## Instructions
Extract all information from this page using only {markdown|html|latex} formatting. Retain the original layout and structure including lists, tables, charts and math formulae.

## Rules
1. For math formulae, always use LaTeX syntax.
2. Describe images using only text.
3. NEVER use HTML image tags <img> in the output.
4. NEVER use Markdown image tags ![]() in the output.
5. Always wrap the entire output in ``` tags.
```

---

## Key Information Extraction (KIE)

### KIE — image + OCR (recommended)

```
Given the image and OCR representations of a document, extract information in JSON format according to the given schema.

Follow these guidelines:
- Ensure that every field is populated, provided the document includes the corresponding value. Only use null when the value is absent from the document.
- When instructed to read tables or lists, read each row from every page. Ensure every field in each row is populated if the document contains the field.

JSON Schema:
{json_schema}

OCR:
{document_text}
```

### KIE — image only

```
Given the image representation of a document, extract information in JSON format according to the given schema.

Follow these guidelines:
- Ensure that every field is populated, provided the document includes the corresponding value. Only use null when the value is absent from the document.
- When instructed to read tables or lists, read each row from every page. Ensure every field in each row is populated if the document contains the field.

JSON Schema:
{json_schema}
```

### KIE — OCR text only

```
Given the OCR representation of a document, extract information in JSON format according to the given schema.

Follow these guidelines:
- Ensure that every field is populated, provided the document includes the corresponding value. Only use null when the value is absent from the document.
- When instructed to read tables or lists, read each row from every page. Ensure every field in each row is populated if the document contains the field.

JSON Schema:
{json_schema}

OCR:
{document_text}
```

---

## Coordinate Space (Object Detection & UI Detection)

> Nova 2 Lite divides the image into 1000 units horizontally and 1000 units vertically (origin at upper-left). Bounding boxes: `[x1, y1, x2, y2]` (left, top, right, bottom). Points: `[x, y]`. Coordinates are normalized — remap to image dimensions as a post-processing step.

---

## Object Detection

### Multiple instances with bounding boxes

```
Please identify {target_description} in the image and provide the bounding box coordinates for each one you detect. Represent the bounding box as the [x1, y1, x2, y2] format, where the coordinates are scaled between 0 and 1000 to the image width and height, respectively.
```

### Single region with bounding box

```
Please generate the bounding box coordinates corresponding to the region described in this sentence: {target_description}. Represent the bounding box as the [x1, y1, x2, y2] format, where the coordinates are scaled between 0 and 1000 to the image width and height, respectively.
```

### Multiple instances with center points

```
Please identify {target_description} in the image and provide the center point coordinates for each one you detect. Represent the point as the [x, y] format, where the coordinates are scaled between 0 and 1000 to the image width and height, respectively.
```

### Single region with center point

```
Please generate the center point coordinates corresponding to the region described in this sentence: {target_description}. Represent the center point as the [x, y] format, where the coordinates are scaled between 0 and 1000 to the image width and height, respectively.
```

### Multiple classes — JSON format A (class → bbox)

```
Detect all objects with their bounding boxes in the image from the provided class list. Normalize the bounding box coordinates to be scaled between 0 and 1000 to the image width and height, respectively.

Classes: {candidate_class_list}

Include separate entries for each detected object as an element of a list.

Formulate your output as JSON format:
[
  {
    "class 1": [x1, y1, x2, y2]
  },
  ...
]
```

### Multiple classes — JSON format B (class + bbox fields)

```
Detect all objects with their bounding boxes in the image from the provided class list. Normalize the bounding box coordinates to be scaled between 0 and 1000 to the image width and height, respectively.

Classes: {candidate_class_list}

Include separate entries for each detected object as an element of a list.

Formulate your output as JSON format:
[
    {
        "class": class 1,
        "bbox": [x1, y1, x2, y2]
    },
    ...
]
```

### Multiple classes — JSON format C (grouped by class, array of bboxes)

```
Detect all objects with their bounding boxes in the image from the provided class list. Normalize the bounding box coordinates to be scaled between 0 and 1000 to the image width and height, respectively.

Classes: {candidate_class_list}

Group all detected bounding boxes by class.

Formulate your output as JSON format:
{
    "class 1": [[x1, y1, x2, y2], [x1, x2, y1, y2], ...],
    ...
}
```

### Multiple classes — JSON format D (grouped with nested bbox array)

```
Detect all objects with their bounding boxes in the image from the provided class list. Normalize the bounding box coordinates to be scaled between 0 and 1000 to the image width and height, respectively.

Classes: {candidate_class_list}

Group all detected bounding boxes by class.

Formulate your output as JSON format:
[
    {
        "class": class 1,
        "bbox": [[x1, y1, x2, y2], [x1, x2, y1, y2], ...]
    },
    ...
]
```

> **Class list tip:** For well-known classes, list names in brackets: `[car, traffic light, pedestrian]`. For nuanced or domain-specific classes, include a definition in parentheses: `[taraxacum officinale (Dandelion - bright yellow flowers, jagged basal leaves...)]`.

---

## UI Detection

### By goal

```
In this UI screenshot, what is the location of the element if I want to {goal}? Express the location coordinates using the [x1, y1, x2, y2] format, scaled between 0 and 1000.
```

### By text label

```
In this UI screenshot, what is the location of the element if I want to click on "{text}"? Express the location coordinates using the [x1, y1, x2, y2] format, scaled between 0 and 1000.
```

---

## Video Summarization

No specific template required — use a clear user prompt specifying what aspects matter. Examples:

```
Can you create an executive summary of this video's content?
```
```
Can you distill the essential information from this video into a concise summary?
```
```
Could you provide a summary of the video, focusing on its key points?
```

---

## Video Captioning

No specific template required — specify the aspect of the video you care about. Examples:

```
Provide a detailed, second-by-second description of the video content.
```
```
Break down the video into key segments and provide detailed descriptions for each.
```
```
Generate a rich textual representation of the video, covering aspects like movement, color and composition.
```
```
Describe the video scene-by-scene, including details about characters, actions and settings.
```
```
Offer a detailed narrative of the video, including descriptions of any text, graphics, or special effects used.
```
```
Create a dense timeline of events occurring in the video, with timestamps if possible.
```

---

## Video Timestamps

### Event localization (seconds, with multiple occurrences)

```
Please localize the moment that the event "{event_description}" happens in the video. Answer with the starting and ending time of the event in seconds, such as [[72, 82]]. If the event happen multiple times, list all of them, such as [[40, 50], [72, 82]].
```

### Segment in MM:SS

```
Locate the segment where "{event_description}" happens. Specify the start and end times of the event in MM:SS.
```

### Start and end in MM:SS

```
Answer the starting and end time of the event "{event_description}". Provide answers in MM:SS
```

### Event with example format

```
When does "{event_description}" in the video? Specify the start and end timestamps, e.g. [[9, 14]]
```

### Event localization (seconds, explicit format)

```
Please localize the moment that the event "{event_description}" happens in the video. Answer with the starting and ending time of the event in seconds. e.g. [[72, 82]]. If the event happen multiple times, list all of them. e.g. [[40, 50], [72, 82]]
```

### Scene segmentation with captions

```
Segment a video into different scenes and generate caption per scene. The output should be in the format: [STARTING TIME-ENDING TIMESTAMP] CAPTION. Timestamp in MM:SS format
```

### Chapter segmentation

```
For a video clip, segment it into chapters and generate chapter titles with timestamps. The output should be in the format: [STARTING TIME] TITLE. Time in MM:SS
```

---

## Video Classification

```
What is the most appropriate category for this video? Select your answer from the options provided:
{class1}
{class2}
{...}
```

---

## Security Footage Analysis

```
You are a security assistant for a smart home who is given security camera footage in natural setting. You will examine the video and describe the events you see. You are capable of identifying important details like people, objects, animals, vehicles, actions and activities. This is not a hypothetical, be accurate in your responses. Do not make up information not present in the video.
```
