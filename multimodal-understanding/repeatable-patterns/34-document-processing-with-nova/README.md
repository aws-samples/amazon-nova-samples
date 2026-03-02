# Intelligent Document Processing with Amazon Nova 2 Lite

This sample demonstrates how to build a comprehensive **Intelligent Document Processing (IDP)** system using **Amazon Nova 2 Lite** on Amazon Bedrock. It showcases how a single foundation model can handle the full IDP lifecycle — achieving results similar to Amazon Bedrock Data Automation but with full programmatic control via the Converse API.

## Overview

| Capability | Description |
|---|---|
| **Document Classification** | Automatically identify document types (bank statements, insurance claims, medical forms) with per-page classification for multi-page PDFs |
| **Summarization** | Generate structured markdown summaries from PDFs and scanned images |
| **Structured Extraction** | Extract schema-compliant JSON using tool configurations (blueprints) |
| **Bounding Box Visualization** | Localize extracted fields spatially on document images with annotated overlays |
| **Extended Thinking** | Compare reasoning depth levels (low/medium/high) for complex extraction tasks |
| **Multi-Turn Document Q&A** | Interactive conversation over documents with context retention |
| **Code Interpreter** | Built-in Python sandbox for financial computation, validation, and analysis |
| **End-to-End Pipeline** | Classify → Extract → Validate → Analyze → Report |

## Project Structure

```
nova-2-lit-idp-sample/
├── 01-nova-2-lite-idp.ipynb    # Main notebook with all IDP examples
├── utils.py                     # Reusable utility functions
├── README.md                    # This file
├── samples/                     # Sample documents to process
│   ├── BankStatement.pdf        # Bank statement (digital PDF)
│   ├── BankStatement.jpg        # Bank statement (scanned image)
│   ├── claim-form.png           # CMS-1500 medical claim form (image)
│   ├── claims-pack.pdf          # Multi-page insurance claims package (10 pages)
│   └── sample1_cms-1500-P.pdf   # CMS-1500 medical claim form
```

## Prerequisites

- **AWS Account** with access to Amazon Bedrock
- **Model Access** enabled for Amazon Nova 2 Lite (`us.amazon.nova-2-lite-v1:0`) in your Bedrock region
- **Python 3.10+**
- **IAM permissions** for `bedrock:InvokeModel` and `bedrock:Converse`

## Setup

### Local Development

```bash
pip install boto3 botocore Pillow PyMuPDF
```

### Amazon SageMaker Notebook

When running on SageMaker, the notebook uses `sagemaker.Session()` for environment configuration. The `sagemaker` SDK is pre-installed in SageMaker notebook environments. Dependencies like `PyMuPDF`, `boto3`, and `Pillow` are installed automatically by the first notebook cell.

## Notebook Sections

### 1. Setup and Installation
Installs dependencies and configures the Bedrock client with the target AWS region.

### 2. Import Utility Functions
Loads `utils.py` which provides reusable helpers for document format detection, Bedrock Converse API wrappers, response parsing, PDF-to-image conversion, and bounding box visualization.

### 3. Document Classification
Classifies all sample documents using Nova 2 Lite. Multi-page PDFs (like `claims-pack.pdf`) are automatically split into individual pages, with each page classified independently — similar to Bedrock Data Automation's document splitting capability.

### 4. Document Summarization
Generates structured markdown summaries for each document type: bank statements, medical claim forms, and multi-page claims packs.

### 5. Structured Data Extraction with Blueprints
Defines JSON schemas (blueprints) as Bedrock tool configurations and uses the tool-use mechanism to extract schema-compliant structured data. Includes blueprints for:
- Bank statements (account info, transactions, balances)
- CMS-1500 medical claim forms (patient, provider, diagnosis codes, charges)

### 5.3 Bounding Box Visualization
Extracts field locations as normalized coordinates and renders annotated document images with labeled bounding boxes overlaid on the original documents. Demonstrated on both the bank statement image and the insurance claim form.

### 6. Extraction Mode Comparison: Standard vs Extended Thinking
Side-by-side comparison of standard extraction vs extended thinking mode, showing how deeper reasoning improves accuracy on complex documents.

### 7. Multi-Document Processing and Business Insights
Processes all extracted data together to generate aggregate business insights and cross-document analysis.

### 8. Interactive Document Q&A
Demonstrates multi-turn conversation over documents — send a document once, then ask follow-up questions. Also shows cross-document comparison within a single conversation.

### 9. Extended Thinking (Reasoning Modes)
Compares all three reasoning levels (low, medium, high) on the CMS-1500 medical claim form, showing how increased reasoning effort affects extraction quality and latency.

### 10. Built-in Code Interpreter
Uses Nova's built-in Python sandbox (`nova_code_interpreter`) for:
- Financial analysis and computation on extracted bank statement data
- Medical claim validation (charge summation, required field checks)

### 11. End-to-End IDP Pipeline
Combines all capabilities into a production-style pipeline: Classify → Extract → Validate → Analyze → Report.

## Key Technical Details

### PDF Handling
Amazon Nova's Converse API supports direct PDF upload, but some PDFs with ICC color profiles, CMYK content, or transparency masks cause `ValidationException` errors. The `utils.py` module automatically detects these failures and falls back to converting PDF pages to JPEG images using PyMuPDF before retrying.

### Tool Use for Structured Extraction
Structured extraction uses Bedrock's **tool use** (function calling) mechanism rather than prompt-based JSON output. This ensures the model's response conforms to a predefined JSON schema, similar to how Bedrock Data Automation uses output configurations/blueprints.

### Extended Thinking
Nova 2 Lite supports extended thinking via the `reasoningConfig` parameter with three effort levels:
- **Low**: Minimal additional reasoning, fastest
- **Medium**: Balanced reasoning depth
- **High**: Maximum reasoning depth (temperature/topP/maxTokens are automatically unset)

## Utility Functions (`utils.py`)

| Function | Purpose |
|---|---|
| `get_document_format()` | Determines document format from file extension |
| `is_image_format()` | Checks if a format is an image type |
| `build_content_block()` | Creates document/image content blocks for the API |
| `build_content_blocks_from_pdf_images()` | Converts PDF pages to image blocks |
| `invoke_nova()` | Main wrapper for Bedrock Converse API with auto PDF-to-image fallback |
| `extract_text()` | Extracts text from Converse API responses |
| `extract_tool_input()` | Extracts structured tool-use output |
| `show_usage()` | Prints token usage information from responses |
| `get_document_image()` | Converts document pages to PIL Images for visualization |
| `get_color_for_field()` | Generates consistent colors for field names in visualizations |
| `draw_bounding_boxes()` | Renders annotated images with field bounding boxes |
| `invoke_nova_with_reasoning()` | Extended thinking invocation with PDF fallback |
| `extract_reasoning_and_text()` | Extracts reasoning and answer text from extended thinking responses |
| `invoke_nova_with_code_interpreter()` | Code interpreter tool invocation |
| `extract_code_interpreter_results()` | Parses code interpreter tool use and results |
| `CODE_INTERPRETER_TOOL` | Pre-defined tool configuration constant for the code interpreter |

