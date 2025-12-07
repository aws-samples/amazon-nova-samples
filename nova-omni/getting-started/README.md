## Amazon Nova 2 Omni Model

Welcome to the Amazon Nova 2 Omni Model Getting Started!

### Model Overview

Amazon Nova 2 Omni is a multimodal foundation model that can understand and generate content across text, images, and audio. This model excels at:

- **Speech Understanding**: Transcribe, summarize, analyze, and answer questions about audio content
- **Image Generation**: Create high-quality images from text descriptions
- **Multimodal Reasoning**: Process and understand multiple input modalities simultaneously

| Model Characteristics | Amazon Nova 2 Omni |
| --------------------- | ------------------- |
| Model ID | us.amazon.nova-2-omni-v1:0 |
| Input Modalities | Text, Audio, Image |
| Output Modalities | Text, Image |
| Context Window | 300k tokens |
| Max Output Tokens | 10k |
| Supported Audio Formats | mp3, opus, wav, aac, flac, mp4, ogg, mkv |
| Regions | us-east-1 |
| Converse API | Yes |
| InvokeAPI | Yes |
| Streaming | Yes |
| Batch Inference | Yes |

This is a collection of Jupyter Notebooks that will help you explore the capabilities and syntax of the Amazon Nova 2 Omni model. There are just a few setup steps you need to follow before using the sample code provided in these notebooks.

## Prerequisites

Ensure you have met the following requirements before continuing:

- Python 3.12+ is installed
- [AWS CLI](https://aws.amazon.com/cli/) is installed
- AWS CLI is [configured with IAM credentials](https://docs.aws.amazon.com/cli/v1/userguide/cli-chap-configure.html)

## Enable the Nova 2 Omni Model in the Amazon Bedrock Console

Before you can make API requests to the Nova 2 Omni model, you need to enable the model in your account using the Amazon Bedrock console. Follow [the instructions here](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html) to enable the model called "Amazon > Nova 2 Omni".

## Configure IAM Permissions

Ensure the IAM role you are using has been given the following permissions:

* bedrock:InvokeModel

## Install Dependencies

We recommend using a Python virtual environment when running this code. Follow these steps to create a virtual environment.

1. Navigate to folder:

```bash
cd path/to/nova-omni/getting-started
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

4. Install dependencies. Note, this will install a special unreleased version of the Boto3 SDK which is required to support the new Nova 2 Omni model capabilities.

```bash
pip install -r requirements.txt
```

## Running the Notebooks

Jupyter Notebooks can be run in a number of ways. Choose the method you prefer from the following options.

### Microsoft VS Code

[Microsoft VS Code](https://code.visualstudio.com/) has great support for Jupyter Notebooks with a very user-friendly UI. Just install the ["Jupyter" extension](https://marketplace.visualstudio.com/items?itemName=ms-toolsai.jupyter) installed. After launching VS Code, choose **"Open Folder..."** and open this *"nova-omni/getting-started"* folder.

### From the Command Line

The setup steps above installed the command line version of Jupyter Notebook server. To use this option, do the following from the command line:

```bash
cd path/to/nova-omni/getting-started
```
```bash
source .venv/bin/activate
```
```bash
jupyter notebook
```

This will automatically open a browser-based UI that you can use to run the notebooks.

### Use Amazon SageMaker Notebooks

[Amazon SageMaker Notebooks](https://aws.amazon.com/sagemaker/ai/notebooks/) offers a way to run Jupyter Notebooks in the cloud. If you choose this option, you will need to edit the permissions of the SageMaker IAM role allow it access to Bedrock as described in the [Configure IAM Permissions](#configure-iam-permissions) section.

## Notebook Overview

### 00 - Setup
Verify your environment setup and test connection to Amazon Bedrock:
- Check Python version and dependencies
- Validate AWS credentials and configuration
- Test Bedrock connection and model access

### 01 - Speech Understanding Examples
Explore Nova 2 Omni's speech understanding capabilities including:
- Audio transcription with and without speaker diarization
- Audio summarization
- Call analytics with structured output
- Question answering about audio content

### 02 - Image Generation Examples
Learn how to use Nova 2 Omni for image generation tasks including:
- Text-to-image generation
- Image editing and manipulation
- Style transfer and artistic effects

### 03 - Multimodal Understanding Examples
Discover how to analyze images, videos, and audio:
- Image question answering and classification
- Video content analysis and classification
- Using system prompts vs user prompts
- Audio content understanding

### 04 - LangChain Multimodal Reasoning
Integrate Nova 2 Omni with LangChain for structured reasoning:
- Tool use with Pydantic schemas
- Reasoning effort configuration (low, medium, high)
- MMMU-style evaluation with submit_answer pattern
- Multimodal input processing with structured outputs

### 05 - LangGraph Multimodal Reasoning
Build stateful reasoning workflows with LangGraph:
- Stateful workflow management with checkpoints
- Multi-step reasoning chains
- Conditional routing based on tool calls
- MMMU evaluation graphs with reasoning traces

### 06 - Strands Multimodal Reasoning
Orchestrate multi-agent systems for collaborative reasoning:
- Specialized agents for different modalities
- Multi-agent orchestration and coordination
- Collaborative reasoning with result synthesis
- MMMU-style multi-agent evaluation patterns

### 07 - Document Understanding Examples
Process and analyze document content with Nova 2 Omni:
- OCR (Optical Character Recognition) from PDF documents
- Key Information Extraction (KIE) with structured JSON output
- Object detection and counting in images
- Document format support for PDF processing

### 08 - Financial Document Analysis
Showcase advanced multimodal capabilities with complex financial documents:
- Multi-page document understanding (13-page earnings reports)
- Financial table extraction and conversion to JSON
- Segment-level revenue analysis and calculations
- Chart and graph interpretation
- Cross-referencing information across multiple pages
- Financial ratio calculations and comparative analysis
- Executive summary generation from full reports

## Key Features Demonstrated

- **Speech Transcription**: Convert audio to text with optional speaker identification
- **Audio Analysis**: Extract insights, sentiment, and structured data from audio
- **Image Generation**: Create images from text descriptions
- **Multimodal Understanding**: Process multiple input types simultaneously
- **Reasoning Capabilities**: Enable advanced reasoning for complex tasks
- **Document Processing**: Extract text and data from PDF documents
- **Financial Analysis**: Analyze complex financial reports with tables and charts
