## Dataset Validation for Fine-tuning Nova Understanding models

Before you create a fine-tuning job in the Amazon Bedrock console or using API, utilize the provided script to validate your dataset first. This would allow you to identify formatting errors (if any) faster and save costs.

### Usage

Install the last version of python [here](https://www.python.org/downloads/) if you haven't already.

Download the `dataset_validation` folder, `cd` into the root directory, and run the dataset validation script:

```
python3 nova_ft_dataset_validator.py -i <file path> -m <model name> -t <task type> [-p <platform>]
```

- Task type options:

  - sft: Supervised Fine-Tuning (supported on all models)
  - dpo: Direct Preference Optimization (Nova 1.0 only - not supported on lite-2.0)
  - rft: Reinforcement Fine-Tuning with reference answers (Nova 2.0 Lite only - lite-2.0)

- Model name options

  - **Nova 1.0 (backward compatible):**

    - micro / micro-1.0: Nova Micro Model
    - lite / lite-1.0: Nova Lite Model
    - pro / pro-1.0: Nova Pro Model

  - **Nova 2.0:**
    - lite-2.0: Nova Lite 2.0 Model (supports reasoning, tool use, and documents)

- Platform options (optional, defaults to bedrock)
  - bedrock: Amazon Bedrock platform
  - sagemaker: Amazon SageMaker platform

### Task Type Support Matrix

| Task Type | Nova 1.0 Models | Nova 2.0 Lite (lite-2.0) |
|-----------|----------------|--------------------------|
| SFT       | ✅ Supported    | ✅ Supported             |
| DPO       | ✅ Supported    | ❌ Not Supported         |
| RFT       | ❌ Not Supported| ✅ Supported             |
| CPT       | ✅ Supported    | ✅ Supported             |

## CLI Arguments

```
python3 nova_dataset_validator.py \
    -i / --input_file       PATH    (required) Training JSONL file
    --validation            PATH    (optional) Validation JSONL file
    -m / --model_name       NAME    (required) Model short name (see table above)
    -t / --task_type        TYPE    (optional) sft | cpt | dpo | rft (default: sft)
    -p / --platform         PLAT    (optional) bedrock | sagemaker (default: bedrock)
    --skip-bad-samples              (optional) Continue past errors to report all issues
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0`  | PASS — dataset is valid for Nova fine-tuning |
| `1`  | FAIL — one or more validation errors found   |

## Sample Output

```
Validating training file: train.jsonl

============================================================
  Dataset Validation Report: train.jsonl
============================================================
  Total samples:   1000
  Valid samples:   985
  Failed samples:  15
  Pass rate:       98.5%

  Error breakdown:
    role_ordering_error: 7
    empty_content_error: 5
    invalid_token_error: 3

  First errors (up to 20):
    Line 12: [role_ordering_error] Location ('messages', 0, ...): Invalid messages, expected user role but found assistant (type=value_error)
    Line 45: [empty_content_error] Location ('messages', 1, 'content'): Invalid content, empty text content (type=value_error)
    ...
============================================================

Result: FAIL — please fix the issues above and re-validate.
```

### Nova 2.0 Features

**Nova 2.0 Lite (lite-2.0) supports:**

- ✅ Reasoning content - Optional reasoning blocks in assistant messages
- ✅ Tool use - Complete tool calling with input/output validation
- ✅ Documents - PDF document processing
- ✅ Restricted media formats:
  - Images: PNG, JPEG, GIF (webp not supported)
  - Videos: MOV, MKV, MP4 (webm not supported)

## Validation Rules Summary

### All recipes
- File must have `.jsonl` extension
- Each line must be valid JSON
- Sample count must be within model bounds (Bedrock platform only)

### SFT / DPO
- Messages must alternate: user → assistant → user → assistant → ...
- Last message must be from assistant (SFT) or have candidates (DPO)
- At least 2 messages (one user, one assistant)
- Text content must not contain invalid tokens (`System:`, `User:`, `Bot:`, `[EOS]`, `<image>`, etc.)
- Images/video/documents only in user messages
- Max 10 images per message, max 1 video per sample, max 1 document per user turn
- Video and image/document cannot coexist in the same content list
- S3 URIs must start with `s3://`
- Micro models: no image/video/document content
- Nova 2.0 Lite: restricted image formats (png, jpeg, gif), video formats (mov, mkv, mp4)
- `reasoningContent` only in assistant messages, only on `lite-2.0`
- Tool use: `toolUse` only in assistant messages, `toolResult` only in user messages, IDs must match

### DPO-specific
- Last message must have `candidates` with at least 2 items
- Candidates must have different `preferenceLabel` values (`preferred` / `non-preferred`)
- Candidate content cannot include image/video/document
- No video in non-candidate messages
- Not supported on `lite-2.0`

### CPT
- Each sample must have a non-empty `text` string field

### RFT
- Only supported on `lite-2.0`
- Must have `messages` (non-empty, at least one user message) and `tools` (non-empty)
- `tools` is optional; if provided, must be a non-empty list with no duplicate tool names
- Tool type must be `"function"` with valid name, description, and parameters
- Optional `id` and `reference_answer` fields
- System message (if present) must be first

### Dataset-level (Bedrock only)
- Nova 2.0 Lite does not support a validation dataset
- Sample count bounds per model (default 8–20,000; lite-2.0 SFT: 200–20,000; lite-2.0 RFT: 100–20,000)

### RFT (Reinforcement Fine-Tuning)

**RFT is a new training paradigm that uses reference answers for better model alignment.**

**Note: RFT is ONLY supported on Nova 2.0 Lite (lite-2.0) model.**

RFT format requires:

- `id`: Unique identifier for each sample
- `messages`: List of conversation messages (system, user, assistant)
- `reference_answer`: Dictionary containing the expected/desired output (can be any structure)
- `tools`: (Optional) List of function definitions for tool-based tasks

**RFT Examples:**

Basic RFT:

```json
{
  "id": "chem-01",
  "messages": [
    { "role": "system", "content": "You are a helpful chemistry assistant" },
    {
      "role": "user",
      "content": "Calculate the molecular weight of caffeine (C8H10N4O2)"
    }
  ],
  "reference_answer": {
    "molecular_weight": 194.19,
    "unit": "g/mol",
    "calculation": "8(12.01) + 10(1.008) + 4(14.01) + 2(16.00) = 194.19"
  }
}
```

RFT with Tools:

```json
{
  "id": "tool-001",
  "messages": [
    { "role": "system", "content": "You are a helpful game master assistant" },
    {
      "role": "user",
      "content": "Generate a strength stat for a warrior character. Apply a +2 racial bonus modifier."
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "StatRollAPI",
        "description": "Generates character stats",
        "parameters": {
          "type": "object",
          "properties": {
            "modifier": {
              "description": "Modifier to apply",
              "type": "integer"
            }
          },
          "required": ["modifier"]
        }
      }
    }
  ],
  "reference_answer": {
    "tool_called": "StatRollAPI",
    "tool_parameters": { "modifier": 2 },
    "expected_behavior": "Call StatRollAPI with modifier=2"
  }
}
```

### Test Examples

The following test files are provided to demonstrate various features:

**SFT/DPO (Nova 1.0 & 2.0):**

- `test_simple.jsonl` - Basic text conversations (8 examples, works on all models)
- `test_reasoning.jsonl` - Text conversations with reasoning content (8 examples, Nova 2.0 only)
- `test_image_video_reasoning.jsonl` - Multimodal examples with images/videos and reasoning (8 examples, Nova 2.0 only)
- `test_tool_use.jsonl` - Tool calling examples with reasoning (8 examples, Nova 2.0 only)
- `test_documents.jsonl` - PDF document processing with reasoning (6 examples, Nova 2.0 only)

**RFT (Nova 2.0 Lite only):**

- `test_rft_valid.jsonl` - Valid RFT examples with reference answers (6 examples)
- `test_rft_tools.jsonl` - RFT examples with tool definitions (6 examples)
- `test_rft_invalid.jsonl` - Invalid RFT examples to test error detection (8 examples)

**Test commands:**

```bash
# Test basic SFT (works on all models)
python3 nova_ft_dataset_validator.py -i test_simple.jsonl -m lite-2.0 -t sft

# Test reasoning content (SFT, Nova 2.0 only)
python3 nova_ft_dataset_validator.py -i test_reasoning.jsonl -m lite-2.0 -t sft

# Test images/videos with reasoning (SFT, Nova 2.0 only)
python3 nova_ft_dataset_validator.py -i test_image_video_reasoning.jsonl -m lite-2.0 -t sft

# Test tool use (SFT, Nova 2.0 only)
python3 nova_ft_dataset_validator.py -i test_tool_use.jsonl -m lite-2.0 -t sft

# Test documents (SFT, Nova 2.0 only)
python3 nova_ft_dataset_validator.py -i test_documents.jsonl -m lite-2.0 -t sft

# Test RFT valid samples (RFT only supported on lite-2.0)
python3 nova_ft_dataset_validator.py -i test_rft_valid.jsonl -m lite-2.0 -t rft

# Test RFT with tools (RFT only supported on lite-2.0)
python3 nova_ft_dataset_validator.py -i test_rft_tools.jsonl -m lite-2.0 -t rft

# Test RFT invalid samples (should show validation errors)
python3 nova_ft_dataset_validator.py -i test_rft_invalid.jsonl -m lite-2.0 -t rft

# Test DPO (Nova 1.0 only - will fail on lite-2.0)
python3 nova_ft_dataset_validator.py -i test_dpo.jsonl -m lite -t dpo

# Backward compatible test (Nova 1.0)
python3 nova_ft_dataset_validator.py -i test_simple.jsonl -m lite -t sft
```

### Limitations

This script cannot perform the following validations, as the logic is proprietary to Nova model customization:

- Image size validation
- Video length validation
- Checking whether the service has access to S3 paths

However, these details can be found in the Nova model customization documentation: https://docs.aws.amazon.com/nova/latest/userguide/customize-fine-tune-prepare.html
