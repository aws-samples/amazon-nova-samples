# Nova  FT Dataset Validator — Usage Guide

Standalone CLI tool that validates JSONL training/validation datasets for Amazon Nova fine-tuning.
Combines Pydantic-based schema validation with skip-bad-samples mode, validation-file support,
structured reporting, and support for all recipe types.

## Supported Models

| Short Name   | Description              |
|--------------|--------------------------|
| `micro`      | Nova Micro 1.0           |
| `micro-1.0`  | Nova Micro 1.0 (explicit)|
| `lite`       | Nova Lite 1.0            |
| `lite-1.0`   | Nova Lite 1.0 (explicit) |
| `lite-2.0`   | Nova 2.0 Lite            |
| `pro`        | Nova Pro 1.0             |
| `pro-1.0`    | Nova Pro 1.0 (explicit)  |

## Supported Recipe Types

| Recipe | Description                          | Supported Models                          |
|--------|--------------------------------------|-------------------------------------------|
| `sft`  | Supervised Fine-Tuning (Converse)    | All models                                |
| `cpt`  | Continued Pre-Training (plain text)  | All models                                |
| `dpo`  | Direct Preference Optimization       | All Nova 1.0 models (not `lite-2.0`)      |
| `rft`  | Reinforcement Fine-Tuning            | `lite-2.0` only                           |

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

---

## Examples by Use Case

### 1. SFT — Nova Lite 1.0 (basic)

Validate a text-only SFT dataset on Nova Lite:

```bash
python3 nova_dataset_validator.py \
    -i train.jsonl \
    -m lite \
    -t sft
```

**Expected JSONL format (one object per line):**
```json
{"schemaVersion":"bedrock-conversation-2024","messages":[{"role":"user","content":[{"text":"What is machine learning?"}]},{"role":"assistant","content":[{"text":"Machine learning is a subset of AI..."}]}]}
```

### 2. SFT — Nova Lite 1.0 with validation file

```bash
python3 nova_dataset_validator.py \
    -i train.jsonl \
    --validation val.jsonl \
    -m lite \
    -t sft
```

### 3. SFT — Nova Micro (text-only, no multimodal)

Micro models reject image/video/document content:

```bash
python3 nova_dataset_validator.py \
    -i train.jsonl \
    -m micro \
    -t sft
```

### 4. SFT — Nova Pro 1.0 with multimodal content

Pro supports images, video, and documents in user messages:

```bash
python3 nova_dataset_validator.py \
    -i multimodal_train.jsonl \
    -m pro \
    -t sft
```

**Example multimodal sample:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {"text": "Describe this image"},
        {"image": {"format": "jpeg", "source": {"s3Location": {"uri": "s3://bucket/image.jpg"}}}}
      ]
    },
    {"role": "assistant", "content": [{"text": "The image shows..."}]}
  ]
}
```

### 5. SFT — Nova 2.0 Lite (with reasoning content)

Nova 2.0 Lite supports `reasoningContent` in assistant messages:

```bash
python3 nova_dataset_validator.py \
    -i reasoning_train.jsonl \
    -m lite-2.0 \
    -t sft
```

**Example reasoning sample:**
```json
{
  "messages": [
    {"role": "user", "content": [{"text": "Solve: 2x + 3 = 7"}]},
    {
      "role": "assistant",
      "content": [
        {"reasoningContent": {"reasoningText": {"text": "Subtract 3 from both sides: 2x = 4. Divide by 2: x = 2."}}},
        {"text": "x = 2"}
      ]
    }
  ]
}
```

### 6. SFT — Nova 2.0 Lite with tool use

```bash
python3 nova_dataset_validator.py \
    -i tool_use_train.jsonl \
    -m lite-2.0 \
    -t sft
```

**Example tool use sample:**
```json
{
  "toolConfig": {
    "tools": [{
      "toolSpec": {
        "name": "calculator",
        "description": "Performs arithmetic",
        "inputSchema": {"json": {"type": "object", "properties": {"expression": {"type": "string"}}}}
      }
    }]
  },
  "messages": [
    {"role": "user", "content": [{"text": "What is 42 * 17?"}]},
    {"role": "assistant", "content": [{"toolUse": {"toolUseId": "t1", "name": "calculator", "input": {"expression": "42 * 17"}}}]},
    {"role": "user", "content": [{"toolResult": {"toolUseId": "t1", "content": [{"text": "714"}]}}]},
    {"role": "assistant", "content": [{"text": "42 × 17 = 714"}]}
  ]
}
```

### 7. CPT — Continued Pre-Training

Plain text format, no conversation structure:

```bash
python3 nova_dataset_validator.py \
    -i cpt_train.jsonl \
    -m lite \
    -t cpt
```

**Expected JSONL format:**
```json
{"text": "Amazon Nova is a family of foundation models designed for enterprise use cases..."}
```

### 8. DPO — Direct Preference Optimization (Nova 1.0 only)

DPO requires candidates with preference labels in the last message. Not supported on `lite-2.0`.

```bash
python3 nova_dataset_validator.py \
    -i dpo_train.jsonl \
    -m lite \
    -t dpo
```

**Expected JSONL format:**
```json
{
  "messages": [
    {"role": "user", "content": [{"text": "Explain quantum computing"}]},
    {
      "role": "assistant",
      "candidates": [
        {"content": [{"text": "Quantum computing uses qubits that can exist in superposition..."}], "preferenceLabel": "preferred"},
        {"content": [{"text": "Quantum computing is fast computers."}], "preferenceLabel": "non-preferred"}
      ]
    }
  ]
}
```

### 9. RFT — Reinforcement Fine-Tuning (lite-2.0 only)

OpenAI-style chat format with tool definitions. Only supported on `lite-2.0`.

```bash
python3 nova_dataset_validator.py \
    -i rft_train.jsonl \
    -m lite-2.0 \
    -t rft
```

**Expected JSONL format:**
```json
{
  "id": "sample-001",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant with access to tools."},
    {"role": "user", "content": "What is the weather in Seattle?"}
  ],
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_weather",
      "description": "Get current weather for a location",
      "parameters": {
        "type": "object",
        "properties": {"location": {"type": "string"}},
        "required": ["location"]
      }
    }
  }],
  "reference_answer": "{\"location\": \"Seattle\", \"temperature\": \"55°F\"}"
}
```

### 10. Skip bad samples mode

Process the entire file and report all errors instead of stopping at the first failure:

```bash
python3 nova_dataset_validator.py \
    -i train.jsonl \
    -m lite \
    -t sft \
    --skip-bad-samples
```

This produces a full report with pass rate, error breakdown by category, and the first 20 errors.

### 11. SageMaker platform (skip dataset-level bounds)

When running on SageMaker, dataset-level sample count bounds are not enforced:

```bash
python3 nova_dataset_validator.py \
    -i train.jsonl \
    -m lite \
    -t sft \
    -p sagemaker
```

### 12. Full validation pipeline (training + validation + skip mode)

```bash
python3 nova_dataset_validator.py \
    -i train.jsonl \
    --validation val.jsonl \
    -m pro \
    -t sft \
    --skip-bad-samples
```

---

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

---

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
- Tool type must be `"function"` with valid name, description, and parameters
- Optional `id` and `reference_answer` fields
- System message (if present) must be first

### Dataset-level (Bedrock only)
- Nova 2.0 Lite does not support a validation dataset
- Sample count bounds per model (default 8–20,000; lite-2.0 SFT: 200–20,000; lite-2.0 RFT: 100–20,000)

---

## Programmatic Usage

The validator can also be imported and used as a library:

```python
from olympus_fine_tuning_common.scripts.nova_dataset_validator import (
    TaskType,
    validate_jsonl_file,
    validate_dataset_level,
)

# Validate a file
report = validate_jsonl_file(
    "train.jsonl",
    model_name="lite-2.0",
    task_type=TaskType.SFT,
    skip_bad_samples=True,
)

print(report.summary())
print(f"Pass rate: {report.pass_rate:.1f}%")

# Dataset-level checks
errors = validate_dataset_level(report, None, "lite-2.0", "SFT")
for err in errors:
    print(f"  - {err}")
```

### Legacy entry point (backwards-compatible with nova_ft_dataset_validator.py)

```python
import argparse
from olympus_fine_tuning_common.scripts.nova_dataset_validator import validate_converse_dataset

args = argparse.Namespace(
    input_file="train.jsonl",
    model_name="lite",
    task_type="sft",
    platform="bedrock",
)
validate_converse_dataset(args)  # raises NovaClientError on failure
```
