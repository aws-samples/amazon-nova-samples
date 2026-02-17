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

### Nova 2.0 Features

**Nova 2.0 Lite (lite-2.0) supports:**

- ✅ Reasoning content - Optional reasoning blocks in assistant messages
- ✅ Tool use - Complete tool calling with input/output validation
- ✅ Documents - PDF document processing
- ✅ Restricted media formats:
  - Images: PNG, JPEG, GIF (webp not supported)
  - Videos: MOV, MKV, MP4 (webm not supported)

### Features

1. Validates the `JSONL` format
2. Collects all the client errors so
   - This ensures that all the errors are reported once rather than in an iterative manner
3. **Task type validation:**
   - Ensures RFT is only used with lite-2.0 model
   - Ensures DPO is only used with Nova 1.0 models (not lite-2.0)
   - SFT works with all models
4. For each line
   - required keys exists
   - `messages` field is not null
   - given `role` for each message is supported
   - messages with the `assistant` role do not contain an image/video
   - `role` alternates between `user` and `assistant`
   - there are no more than 10 images per line
   - number of samples supported by model type (only for Bedrock platform)
   - image/video/document is from the supported formats
   - invalid tokens are detected (case-insensitive: System:, USER:, Assistant:, etc.)
   - **Nova 2.0 specific validations:**
     - reasoning content only in assistant messages and only for lite-2.0
     - tool use placement (toolUse in assistant, toolResult in user messages)
     - tool use/result ID matching and uniqueness
     - tool names match toolConfig definitions
     - format restrictions for lite-2.0 (PNG, JPEG, GIF for images; MOV, MKV, MP4 for videos; PDF for documents)
   - **RFT specific validations:**
     - id field validation (optional but if present must not be empty)
     - messages must contain at least one user message
     - tools field is required and cannot be empty
     - reference_answer validation (optional but if present must not be empty)
     - duplicate tool names detection
5. Platform-specific validations
   - For Bedrock: Validates that the number of samples is within the allowed bounds for the model and task type
   - For SageMaker: Skips the data record bounds validation

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
