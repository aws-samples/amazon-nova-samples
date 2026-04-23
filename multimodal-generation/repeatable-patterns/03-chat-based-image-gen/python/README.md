# Chat-based Image Generation Pattern

This pattern demonstrates one approach to building a conversation-driven, multi-turn UX for image generation with Amazon Nova Canvas. It leverages one of the Nova understanding models (Micro, Lite, or Pro) to determine user intent, formulate enhanced prompts, and produce other outputs that fuel a pleasant user experience.

## Setup

The following are recommended setup steps.

1. Navigate to folder:
```bash
cd path/to/03-chat-based-image-gen/python
```

2. Create virtual environment:
```bash
python -m venv .venv
```

3. Activate virtual environment:
- On Windows:
```bash
.venv\Scripts\activate
```
- On macOS/Linux:
```bash
source .venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```



## Quick Start

To try things out, run the *ImageGenChat-cli.py* script . It provides an interactive command line interface that will allow you to see prompt enhancement in action and optionally have it generate images.

Run this command from the root of the project folder to test:

```bash
python ImageGenChat-cli.py
```

> 💾 Images and prompts will automatically be saved to "output/".



## Code Tour

### Primary

#### `ImageGenChat.py`

Defines the **ImageGenChat** class which manages image geneneration conversation flow and provides automatic prompt enhancement. It maintains conversation history, processes user inputs, and formats model responses.

#### `system_prompt.md`

Defines the LLM system prompt used by the **ImageGenChat** class.

#### `amazon_image_gen.py`

Provides a **BedrockImageGenerator** class for use in generating images with Nova Canvas.

### `file_utils.py`

Defines a few convenience functions for working with image files.

### Secondary

#### `ImageGenChat-cli.py`

A simple CLI tool provided as a simple interactive way to excercise the capabilities of teh **ImageGenChat** class.

#### `ImageGenChat-test.py`

Defines tests for the **ImageGenChat** class. You can run this class directly to execute the test suite.
