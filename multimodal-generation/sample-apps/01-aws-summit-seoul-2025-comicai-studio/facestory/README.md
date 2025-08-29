# Face Story: Creative Applications with Amazon Bedrock

This sample application demonstrates creative applications using Amazon Bedrock's multimodal capabilities, including comic-style transformations and face reading/fortune telling.

## Overview

**Based on AWS Summit Seoul 2025 Expo: ComicAI Studio - Face Story**

This collection showcases how to use Amazon Bedrock models for creative image transformation and analysis:

1. **Comic Style Transformation** - Transform realistic face images into comic-style artwork
2. **Face Analysis and Fortune Reading** - Analyze facial features and generate fortune readings

## Files

- `01_face_to_comic_style.ipynb` - Notebook for transforming realistic face images into comic-style artwork
- `02_face_to_fortune.ipynb` - English version of face analysis and fortune reading notebook
- `02_face_to_fortune_kr.ipynb` - Korean version of face analysis and fortune reading notebook

## Features

### Comic Style Transformation
- **Nova Canvas Best Practices**: Implements image caption style prompts and specific element inclusion
- **Step-by-step Process**: Clear progression from realistic to comic-style imagery
- **Korean Face Generation**: Specialized prompts for generating Korean facial features
- **Comic Style Transformation**: Professional comic book styling techniques

### Face Analysis and Fortune Reading
- **Facial Feature Analysis**: Detailed analysis of facial features using Amazon Bedrock's Nova models
- **Fortune Generation**: Creates personalized fortune readings based on facial analysis
- **Bilingual Support**: Available in both English and Korean versions
- **Interactive Results**: Clean visualization of analysis and fortune results
- **Modular Design**: Separate functions for analysis and fortune generation

## Getting Started

1. Choose the notebook for your desired application:
   - `01_face_to_comic_style.ipynb` for comic transformations
   - `02_face_to_fortune.ipynb` for face analysis and fortune reading (English)
   - `02_face_to_fortune_kr.ipynb` for face analysis and fortune reading (Korean)
2. Follow the step-by-step process outlined in each notebook
3. Experiment with different images and prompts

## Requirements

- Access to Amazon Bedrock (Nova Canvas and Nova Lite models)
- Jupyter Notebook environment
- Required Python packages:
  - boto3
  - pillow
  - matplotlib
  - IPython

## Usage Examples

### Comic Style Transformation
Transform realistic face images into comic-style artwork through a 3-step process:
1. Generate realistic face image
2. Convert to black & white comic style
3. Add color expression

### Face Analysis and Fortune Reading
Analyze facial features and generate fortune readings:
1. Upload a face image
2. Run facial feature analysis
3. Generate personalized fortune reading based on analysis
