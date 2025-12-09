# Nova Data Preparation Tool

`nova-data-prep` is a comprehensive data preparation script for Nova fine-tuning. It handles the entire data preparation pipeline from loading raw data to generating validated Nova-compatible training files.

## Overview

The `nova-data-prep` script streamlines the process of preparing data for Nova model fine-tuning by:

1. Loading data from multiple sources (local files, S3, Hugging Face datasets)
2. Converting to the required Nova converse format
3. Splitting data into train/validation/test sets
4. Validating the output against Nova's format requirements
5. Uploading processed data to S3 (optional)

## Installation Requirements

```bash
pip install boto3 datasets pandas jinja2
```

## Command-Line Arguments Reference

### Input Source Arguments (One Required)

| Argument            | Description                          | Format                         | Example                                 | When to Use                                 |
| ------------------- | ------------------------------------ | ------------------------------ | --------------------------------------- | ------------------------------------------- |
| `--data_file PATH`  | Load data from a local or S3 file    | Supports CSV, JSON, JSONL, TXT | `my_data.csv`, `s3://bucket/data.jsonl` | When you have data in a file                |
| `--hf_dataset NAME` | Load data from Hugging Face datasets | Dataset name or path           | `"squad"`, `"microsoft/DialoGPT-large"` | When your data is available as a HF dataset |

### Hugging Face Dataset Configuration

| Argument           | Description                                | Default | Example               | When to Use                                   |
| ------------------ | ------------------------------------------ | ------- | --------------------- | --------------------------------------------- |
| `--hf_config NAME` | Specify Hugging Face dataset configuration | None    | `"default"`, `"v2.0"` | If the HF dataset has multiple configurations |
| `--hf_split NAME`  | Specify Hugging Face dataset split         | None    | `"train"`, `"test"`   | To load specific split from HF dataset        |

### Data Mapping Configuration

| Argument                | Description                                   | Default                          | Example                             | When to Use                             |
| ----------------------- | --------------------------------------------- | -------------------------------- | ----------------------------------- | --------------------------------------- |
| `--question_col NAME`   | Column/field name for user/question input     | `"question"`                     | `"user_input"`, `"prompt"`          | If your data uses different field names |
| `--answer_col NAME`     | Column/field name for assistant/answer output | `"answer"`                       | `"response"`, `"output"`            | If your data uses different field names |
| `--system_col NAME`     | Column/field name for system messages         | None                             | `"system_prompt"`, `"instructions"` | If you have per-sample system messages  |
| `--image_col NAME`      | Column/field name for image paths/URLs        | None                             | `"image_path"`, `"image_url"`       | For multimodal data with images         |
| `--video_col NAME`      | Column/field name for video paths/URLs        | None                             | `"video_path"`, `"video_url"`       | For multimodal data with videos         |
| `--system_message TEXT` | Default system message for all samples        | `"You are a helpful assistant."` | `"You are a medical expert."`       | To set a global system message          |

### Output Configuration

| Argument                 | Description                          | Default       | Example                                | When to Use                             |
| ------------------------ | ------------------------------------ | ------------- | -------------------------------------- | --------------------------------------- |
| `--output_dir PATH`      | Local directory for output files     | `"nova_data"` | `"processed_data"`, `"training_files"` | Always (controls where files are saved) |
| `--s3_output_prefix URI` | S3 prefix for uploading output files | None          | `s3://bucket/prefix`                   | To save results to S3                   |
| `--job_name NAME`        | Name for this preparation job        | None          | `"medical-assistant-v1"`               | To organize outputs in S3 by job        |

### Data Split Configuration

| Argument              | Description                            | Default   | Range       | Example | When to Use                 |
| --------------------- | -------------------------------------- | --------- | ----------- | ------- | --------------------------- |
| `--train_ratio FLOAT` | Proportion of data for training        | 0.8 (80%) | 0.0 to 1.0  | `0.7`   | To customize split ratios   |
| `--val_ratio FLOAT`   | Proportion of data for validation      | 0.1 (10%) | 0.0 to 1.0  | `0.2`   | To customize split ratios   |
| `--test_ratio FLOAT`  | Proportion of data for testing         | 0.1 (10%) | 0.0 to 1.0  | `0.1`   | To customize split ratios   |
| `--seed INT`          | Random seed for reproducible splitting | 42        | Any integer | `123`   | To ensure consistent splits |

### Template Configuration

| Argument                         | Description                       | Type                | Format          | Example                                | When to Use                    |
| -------------------------------- | --------------------------------- | ------------------- | --------------- | -------------------------------------- | ------------------------------ |
| `--use_templates`                | Enable Jinja2 template processing | Flag                | No value needed |                                        | For complex message formatting |
| `--user_template TEXT/PATH`      | Template for user messages        | String or file path | Jinja2 template | `"User query: {{ question }}"`         | With `--use_templates`         |
| `--assistant_template TEXT/PATH` | Template for assistant messages   | String or file path | Jinja2 template | `"{{ answer }}"`                       | With `--use_templates`         |
| `--system_template TEXT/PATH`    | Template for system messages      | String or file path | Jinja2 template | `"You are an expert in {{ domain }}."` | With `--use_templates`         |

### Model & Validation

| Argument            | Description               | Choices                      | Default  | When to Use                        |
| ------------------- | ------------------------- | ---------------------------- | -------- | ---------------------------------- |
| `--model_name NAME` | Nova model for validation | `"micro"`, `"lite"`, `"pro"` | `"lite"` | To validate against specific model |
| `--no_validate`     | Skip output validation    | Flag                         | False    | To bypass validation checks        |

## Input Data Formats

The `nova-data-prep` script supports various input formats:

### JSONL Format

Each line should be a valid JSON object with at least these 2 fields: "question" and "answer" (or your custom field names)

```jsonl
{"question": "What is the capital of France?", "answer": "The capital of France is Paris."}
{"question": "How do I reset my password?", "answer": "To reset your password, go to the login page and click 'Forgot Password'..."}
```

You can customize the field names using `--question_col` and `--answer_col` parameters:

```jsonl
{
  "user_input": "What's the weather like?",
  "assistant_response": "I don't have access to real-time weather data..."
}
```

Optional fields:

- `system_message`: Override default system message for this sample
- `image_path`: S3 URI for image (if using image support)
- `video_path`: S3 URI for video (if using video support)

Example with all fields:

```jsonl
{
  "question": "What's in this image?",
  "answer": "The image shows a red coffee maker on a white counter.",
  "system_message": "You are a product description assistant.",
  "image_path": "s3://my-bucket/images/coffee-maker.jpg"
}
```

### CSV Format

Should have columns matching the specified `--question_col` and `--answer_col` parameters:

```csv
question,answer
"What is the capital of France?","The capital of France is Paris."
"How do I reset my password?","To reset your password, go to the login page..."
```

### JSON Format

An array of objects following the same structure as JSONL:

```json
[
  {
    "question": "What is the capital of France?",
    "answer": "The capital of France is Paris."
  },
  {
    "question": "How do I reset my password?",
    "answer": "To reset your password, go to the login page..."
  }
]
```

### Text Format

Plain text files are parsed as Q&A pairs, separated by double newlines:

```text
What is the capital of France?
The capital of France is Paris.

How do I reset my password?
To reset your password, go to the login page and click 'Forgot Password'...
```

## Output Format

The script generates three files in Nova converse format:

- `train.jsonl` - Training data
- `val.jsonl` - Validation data
- `test.jsonl` - Test data

Each file follows the exact Nova format with proper schema validation:

```json
{
  "schemaVersion": "bedrock-conversation-2024",
  "system": [{ "text": "You are a helpful assistant." }],
  "messages": [
    {
      "role": "user",
      "content": [{ "text": "What is the capital of France?" }]
    },
    {
      "role": "assistant",
      "content": [{ "text": "The capital of France is Paris." }]
    }
  ]
}
```

## Validation Process

The `nova-data-prep` script performs comprehensive validation to ensure your data meets Nova's requirements:

1. **Schema Validation**: Verifies that all samples follow the correct Nova converse format
2. **Content Validation**: Checks for forbidden keywords, empty content, and other content rules
3. **Role Order Validation**: Ensures messages alternate between user and assistant roles
4. **Media Validation**: Validates image/video formats and limits (max 10 images, 1 video)
5. **Model-Specific Validation**: Applies model-specific rules (e.g., no media for micro models)
6. **Sample Count Validation**: Ensures the number of samples is within allowed bounds for the model

### Validation Rules

- **Sample Count**: Each model has minimum and maximum sample limits:

  - Micro: 8-100,000 samples
  - Lite: 8-100,000 samples
  - Pro: 8-100,000 samples

- **Media Support**:

  - Micro: No image or video support
  - Lite: Supports images and videos
  - Pro: Supports images and videos

- **Image Formats**: jpeg, png, gif, webp
- **Video Formats**: mov, mkv, mp4, webm
- **Media Limits**: Maximum 10 images per sample, 1 video per sample
- **Content Rules**: Cannot mix images and videos in the same sample
- **Role Rules**: Assistant messages cannot contain images or videos

- **Forbidden Keywords**: The following keywords are not allowed in text content:
  - "Bot:"
  - "<image>"
  - "<video>"
  - "[EOS]"
  - "Assistant:"
  - "User:"

## Template System

The script supports Jinja2 templates for flexible formatting of messages. Templates can access any field in your input data.

### Template Examples

1. Basic Template Usage:

```bash
python nova-data-prep.py \
    --data_file customer_service.csv \
    --use_templates \
    --user_template "Customer Query: {{ query }}\nProduct: {{ product }}\nCategory: {{ category }}" \
    --assistant_template "{{ response }}\n\nReference ID: {{ ticket_id }}" \
    --output_dir ./templated_data
```

2. Using Template Files:

Create template files:

user_template.txt:

```
Customer: {{ customer_name }}
Issue: {{ issue_description }}
Priority: {{ priority }}
Account ID: {{ account_id }}
```

assistant_template.txt:

```
Dear {{ customer_name }},

{{ solution }}

Best regards,
Customer Support
Ticket #{{ ticket_id }}
```

Then use them:

```bash
python nova-data-prep.py \
    --data_file support_tickets.csv \
    --use_templates \
    --user_template user_template.txt \
    --assistant_template assistant_template.txt \
    --system_template "You are a customer service agent for {{ department }}." \
    --output_dir ./support_data
```

### Template Filters

Template variables can be processed using Jinja2 filters:

- `{{ text | upper }}` - Convert to uppercase
- `{{ text | lower }}` - Convert to lowercase
- `{{ text | truncate(100) }}` - Truncate to 100 characters

## S3 Integration

When uploading to S3, you can use the `--job_name` parameter to organize your data into meaningful partitions:

```bash
# Without job name (uses only timestamp):
python nova-data-prep.py --data_file input.jsonl \
    --s3_output_prefix s3://my-bucket/training
# Output: s3://my-bucket/training/1687401467/train.jsonl

# With job name (combines name and timestamp):
python nova-data-prep.py --data_file input.jsonl \
    --s3_output_prefix s3://my-bucket/training \
    --job_name my-training-job
# Output: s3://my-bucket/training/my-training-job-1687401467/train.jsonl
```

Benefits of job-based partitioning:

- Track different training runs easily
- Organize data splits by job name
- Prevent overwriting of data from different runs
- Enable easy identification and retrieval of specific training datasets
- Maintain historical versions of training data

## Usage Examples

### Basic Local File Processing

```bash
python nova-data-prep.py \
    --data_file my_data.csv \
    --question_col "user_input" \
    --answer_col "assistant_output" \
    --output_dir ./prepared_data
```

### Processing S3 File with Custom System Message

```bash
python nova-data-prep.py \
    --data_file s3://my-bucket/raw_data.jsonl \
    --system_message "You are an expert medical assistant." \
    --model_name "pro" \
    --output_dir ./medical_data
```

### HuggingFace Dataset with Custom Split Ratios

```bash
python nova-data-prep.py \
    --hf_dataset "squad" \
    --hf_config "v2.0" \
    --hf_split "train" \
    --question_col "question" \
    --answer_col "answer" \
    --train_ratio 0.7 \
    --val_ratio 0.2 \
    --test_ratio 0.1 \
    --output_dir ./squad_data
```

### Multimodal Data with Image and Video Support

```bash
python nova-data-prep.py \
    --data_file conversations_with_media.csv \
    --question_col "text" \
    --answer_col "response" \
    --image_col "image_path" \
    --video_col "video_path" \
    --output_dir ./multimodal_data \
    --model_name "pro"
```

### Complete Example with All Features

```bash
python nova-data-prep.py \
    --data_file customer_data.jsonl \
    --output_dir ./processed_data \
    --s3_output_prefix s3://my-bucket/training-data \
    --job_name customer-service-v1 \
    --question_col "user_message" \
    --answer_col "agent_response" \
    --system_col "custom_system" \
    --image_col "image_url" \
    --video_col "video_url" \
    --system_message "You are a customer service AI assistant." \
    --train_ratio 0.7 \
    --val_ratio 0.2 \
    --test_ratio 0.1 \
    --use_templates \
    --user_template user_template.txt \
    --assistant_template assistant_template.txt \
    --model_name "pro" \
    --seed 42
```

## Best Practices

1. **Data Quality**:

   - Ensure your data is clean and well-formatted
   - Remove any samples with empty or low-quality responses
   - Check for and remove any forbidden keywords

2. **System Messages**:

   - Use clear, concise system messages that define the assistant's role
   - Consider using per-sample system messages for varied tasks

3. **Data Splitting**:

   - Use appropriate split ratios based on your dataset size
   - For small datasets (<100 samples), consider using 70/20/10 split
   - For large datasets (>1000 samples), 80/10/10 is typically sufficient

4. **Validation**:

   - Always validate your data against the target model
   - Fix validation errors before proceeding with fine-tuning

5. **S3 Organization**:

   - Use meaningful job names to organize your data
   - Consider using a consistent naming convention for jobs

6. **Templates**:

   - Use templates for complex formatting needs
   - Validate templates with sample data before processing large datasets

7. **Media Content**:
   - Ensure all media files are accessible from S3
   - Use appropriate formats for images and videos
   - Don't mix images and videos in the same sample

## Troubleshooting

### Common Validation Errors

1. **Invalid role order**: Messages must alternate between user and assistant roles, starting with user.

   ```
   Solution: Ensure your data follows the correct turn-taking pattern.
   ```

2. **Forbidden keywords**: Text contains keywords like "Bot:", "User:", etc.

   ```
   Solution: Remove or replace these keywords in your data.
   ```

3. **Media format errors**: Unsupported image or video formats.

   ```
   Solution: Convert media to supported formats (jpeg, png, gif, webp for images; mov, mkv, mp4, webm for videos).
   ```

4. **Sample count errors**: Too few or too many samples for the target model.

   ```
   Solution: Ensure you have at least 8 samples and no more than 100,000 samples.
   ```

5. **Template errors**: Missing variables in templates.
   ```
   Solution: Check that all variables used in templates exist in your data.
   ```

### S3 Issues

1. **Permission errors**: Insufficient permissions to access S3.

   ```
   Solution: Check your AWS credentials and ensure you have the necessary permissions.
   ```

2. **Invalid S3 URI**: S3 URI doesn't start with "s3://".
   ```
   Solution: Ensure all S3 paths follow the format "s3://bucket-name/path".
   ```

## Error Handling

The script provides comprehensive error messages for common issues:

- Validation failures with specific sample locations
- Missing dependencies with installation instructions
- S3 credential and permission error handling
- Template rendering errors with variable information

## Advanced Usage

### Processing Large Datasets

For very large datasets, consider:

1. Processing in batches
2. Using a larger machine with more memory
3. Pre-filtering data to remove low-quality samples

### Custom Validation

If you need custom validation beyond what's provided:

1. Create a custom validator script
2. Process the output files with your custom validator
3. Filter out samples that don't meet your criteria

### Combining Multiple Data Sources

To combine data from multiple sources:

1. Process each source separately
2. Merge the resulting JSONL files
3. Re-split the combined data if needed

## Conclusion

The `nova-data-prep` script is a powerful tool for preparing data for Nova fine-tuning. By following the guidelines and best practices in this documentation, you can ensure your data is properly formatted and validated for successful fine-tuning.
