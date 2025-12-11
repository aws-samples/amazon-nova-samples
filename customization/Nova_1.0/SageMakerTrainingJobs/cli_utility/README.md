# 🛠️ Nova CLI Utility Guide

> ⚠️ **EXPERIMENTAL PREVIEW** ⚠️
>
> This CLI utility is currently in experimental preview phase. We encourage you to try it out and provide feedback to help make it even better! Your contributions and suggestions are valuable in shaping its development.

## Overview

This guide provides a comprehensive overview of the Nova CLI utility modules, their purposes, and when to use each one. Each module is designed to handle specific aspects of the ML model lifecycle.

## Available Modules

### 📊 001 Data Preparation Module

**Purpose**: Prepare and validate data for model training

- 🔍 Data validation
- 📝 Data formatting
- 🔄 Data transformation
- 📋 JSONL handling

**When to use**:

- When you need to prepare training/validation/test datasets
- To validate data format compliance
- To transform data into Nova-compatible format

### 🎯 002 Tuner Module

**Purpose**: Fine-tune and optimize models

- 🔧 Model parameter tuning
- ⚙️ Hyperparameter optimization
- 🎛️ Training configuration

**When to use**:

- For model fine-tuning tasks
- When optimizing model performance
- To customize model parameters

### 📈 003 Model Analysis Module

**Purpose**: Analyze model artifacts and performance

- 📊 Performance metrics analysis
- 🔍 Model artifact inspection
- 📉 Training results evaluation

**When to use**:

- To analyze model training results
- When inspecting model artifacts
- For performance evaluation

### ⚖️ 004 Evaluation Module

**Purpose**: Comprehensive model evaluation

- 📊 Metrics calculation
- 📈 Visual analysis
- 🔄 Format conversion
- 📋 Results analysis

**When to use**:

- For model evaluation tasks
- To generate performance metrics
- When analyzing evaluation results
- To visualize model performance

### 📦 005 Model Export Module

**Purpose**: Export models to different platforms

- 💾 Model export functionality
- 🔄 Format conversion
- 📤 Platform-specific packaging

**When to use**:

- When deploying models
- To export models to different platforms
- For model sharing and distribution

### 🔌 006 Custom Model BR Inferencer Module

**Purpose**: Custom model inference handling

- 🔮 Inference execution
- 🎯 Custom model integration
- 📊 Inference logging

**When to use**:

- For custom model inference
- When implementing custom inference logic
- To handle model predictions

## Quick Start

Each module contains its own detailed README with specific usage instructions. Navigate to the respective module directory for detailed documentation.

## Module Dependencies

- All modules require Python 3.7+
- Specific dependencies are listed in each module's README
- Core dependencies are in the root requirements.txt

## Best Practices

1. 📋 Always validate data before training
2. 🔍 Use the analysis module to inspect results
3. ⚖️ Evaluate models thoroughly before deployment
4. 📊 Monitor and log all inference operations
5. 🔄 Keep data formats consistent across modules

## Common Workflows

### Training Pipeline

1. Data Prep (001) → Tuner (002) → Analysis (003) → Evaluation (004)

### Deployment Pipeline

1. Evaluation (004) → Export (005) → Inferencer (006)

## Support

Refer to individual module documentation for specific usage details and troubleshooting.

## 🤝 Contributing

We welcome contributions to help improve this experimental utility! Here's how you can help:

- Try out the modules and provide feedback
- Report bugs or suggest improvements
- Share your use cases and feature requests
- Submit pull requests with enhancements
- Help improve documentation

Your input is crucial in making this utility more robust and user-friendly. Feel free to:

1. Open issues for bugs or feature requests
2. Submit pull requests with improvements
3. Share your experience and suggestions
4. Help others in the community

Together, we can make this utility even more awesome! 🚀
