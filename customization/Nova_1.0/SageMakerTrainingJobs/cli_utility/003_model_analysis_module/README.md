# Nova Model Artifact Analysis Module

A comprehensive tool for analyzing Nova model training artifacts, performance metrics, and providing detailed insights with automated loss curve visualization.

## Overview

The Model Artifact Analysis module provides detailed analysis of SageMaker training jobs, including:

- **Training Job Analysis**: Comprehensive job details, status, and performance metrics
- **Artifact Download & Extraction**: Automatic download and extraction of model artifacts from S3
- **Escrow Model URI Discovery**: Extraction of checkpoint S3 bucket from manifest.json
- **Training Loss Curve Analysis**: Comprehensive analysis and visualization of training metrics
- **Performance Metrics**: Training/validation loss extraction from multiple file formats
- **Job Comparison**: Side-by-side analysis of multiple training jobs

## Features

### 🔍 Training Job Analysis

- Job status and completion details
- Training duration and resource utilization
- Instance type and configuration analysis
- Model artifact location and validation

### 📥 Artifact Download & Extraction

- Automatic download of output.tar.gz from S3
- Extraction of training artifacts to temporary directory
- Support for various archive formats
- Automatic cleanup of temporary files

### 🔗 Escrow Model URI Discovery

- Automatic search for manifest.json in extracted artifacts
- Extraction of checkpoint_s3_bucket from manifest
- Support for multiple manifest.json locations
- Error handling for missing or malformed manifests

### 📈 Training Loss Curve Analysis

- Comprehensive parsing of training metrics from multiple file formats
- Support for JSONL, JSON, CSV, TXT, and LOG files
- Extraction of training/validation losses, epochs, and steps
- Advanced statistical analysis of loss trends
- Convergence assessment using coefficient of variation
- Overfitting detection through trend analysis

### 📊 Loss Curve Visualization

- High-quality matplotlib plots with professional styling
- Support for multiple x-axis types (epochs, steps, iterations)
- Training and validation loss curves with trend lines
- Automatic plot saving with customizable resolution
- Grid lines, legends, and proper labeling

### 📈 Performance Metrics

- CloudWatch logs access for fallback metrics
- Multi-format training log parsing
- Statistical analysis of training performance
- Loss reduction calculations and percentages

### 🔄 Job Comparison

- Multi-job performance comparison
- Success rate analysis
- Duration and efficiency metrics
- Best performing model identification

## Installation

### Prerequisites

```bash
pip install boto3 pandas matplotlib seaborn
```

### AWS Configuration

Ensure your AWS credentials are configured with permissions for:

- SageMaker (DescribeTrainingJob, ListTrainingJobs)
- S3 (ListObjects, GetObject)
- CloudWatch Logs (DescribeLogStreams, GetLogEvents)

## Usage

### Basic Analysis

```bash
# Analyze a single training job
python model_artifact_analysis.py --job-name my-training-job

# Analyze with specific region
python model_artifact_analysis.py --job-name my-training-job --region us-west-2

# Save analysis results to file
python model_artifact_analysis.py --job-name my-training-job --output-file analysis_report.json
```

### Advanced Analysis

```bash
# Perform specific analysis types
python model_artifact_analysis.py --job-name my-training-job --analysis-type metrics
python model_artifact_analysis.py --job-name my-training-job --analysis-type artifacts
python model_artifact_analysis.py --job-name my-training-job --analysis-type all

# Compare multiple training jobs
python model_artifact_analysis.py --compare-jobs job1 job2 job3 --output-file comparison.json
```

### Python API Usage

```python
from model_artifact_analysis import NovaModelAnalyzer

# Initialize analyzer
analyzer = NovaModelAnalyzer(region='us-east-1')

# Analyze single job
analysis = analyzer.analyze_training_job('my-training-job')
print(f"Job Status: {analysis['job_details']['status']}")
print(f"Training Duration: {analysis['job_details']['training_duration_minutes']} minutes")

# Compare multiple jobs
comparison = analyzer.compare_training_jobs(['job1', 'job2', 'job3'])
print(f"Success Rate: {comparison['summary']['success_rate']}%")

# Export results
analyzer.export_analysis_report(analysis, 'detailed_analysis.json')
```

## Command Line Options

### Required Arguments

- `--job-name`: SageMaker training job name to analyze

### Optional Arguments

- `--analysis-type`: Type of analysis to perform

  - `basic`: Job details and status only
  - `metrics`: Include performance metrics analysis
  - `artifacts`: Include artifact validation
  - `all`: Complete analysis (default)

- `--compare-jobs`: List of job names for comparison analysis
- `--output-file`: Save results to JSON file
- `--region`: AWS region (default: us-east-1)

## Analysis Output

### Complete Analysis Structure

```json
{
  "job_name": "my-training-job",
  "analysis_timestamp": "2024-01-15T10:30:00",
  "job_details": {
    "status": "Completed",
    "creation_time": "2024-01-15T10:30:00",
    "training_duration_minutes": 120.5,
    "instance_type": "ml.p5.48xlarge",
    "instance_count": 2,
    "model_artifacts": "s3://bucket/path/to/model.tar.gz"
  },
  "escrow_model_uri": "s3://bucket/path/to/checkpoint",
  "loss_analysis": {
    "training_losses": [2.5, 2.1, 1.8, 1.5, 1.2],
    "validation_losses": [2.4, 2.0, 1.9, 1.7, 1.6],
    "epochs": [1, 2, 3, 4, 5],
    "steps": [100, 200, 300, 400, 500],
    "loss_curve_plot": "/path/to/loss_curve.png",
    "analysis": {
      "training_loss": {
        "initial_loss": 2.5,
        "final_loss": 1.2,
        "min_loss": 1.2,
        "loss_reduction": 1.3,
        "loss_reduction_percent": 52.0,
        "convergence_assessment": "converged"
      },
      "validation_loss": {
        "initial_loss": 2.4,
        "final_loss": 1.6,
        "min_loss": 1.6,
        "loss_reduction": 0.8,
        "loss_reduction_percent": 33.3
      },
      "overfitting_check": {
        "status": "normal",
        "train_trend": -0.325,
        "val_trend": -0.2
      }
    },
    "metrics_files_found": 3
  },
  "metrics": {
    "training_loss": [],
    "validation_loss": [],
    "learning_rate": [],
    "timestamps": []
  },
  "recommendations": []
}
```

### Loss Analysis Details

The `loss_analysis` section provides comprehensive insights:

- **training_losses/validation_losses**: Arrays of loss values extracted from training logs
- **epochs/steps**: Corresponding training progress indicators
- **loss_curve_plot**: Path to generated matplotlib visualization
- **analysis**: Statistical analysis including:
  - Loss reduction calculations and percentages
  - Convergence assessment (converged, likely_converged, possibly_converged, not_converged)
  - Overfitting detection (normal, overfitting_detected, stable)
- **metrics_files_found**: Number of training log files successfully parsed

### Escrow Model URI

The `escrow_model_uri` field contains the checkpoint S3 bucket extracted from the manifest.json file, providing direct access to the model checkpoint location.

### Loss Curve Visualization

The analysis automatically generates high-quality matplotlib plots showing:

- Training loss progression over time
- Validation loss curves (when available)
- Trend lines with slope analysis
- Professional styling with grids and legends
- Support for epochs, steps, or iteration-based x-axis

## Analysis Types

### Basic Analysis

- Training job status and metadata
- Resource configuration details
- Basic timing information
- Quick health check

### Metrics Analysis

- Training/validation loss progression
- Learning rate scheduling analysis
- Performance trend identification
- Convergence assessment

### Artifacts Analysis

- Model file validation
- S3 storage verification
- File integrity checks
- Size and structure analysis

### Complete Analysis (All)

- Combines all analysis types
- Full performance assessment
- Complete artifact validation

## Job Comparison Features

When comparing multiple jobs, the analysis provides:

### Summary Statistics

- Total jobs analyzed
- Success/failure rates
- Average training duration
- Resource utilization patterns

### Performance Comparison

- Best performing model identification
- Training efficiency metrics
- Cost-effectiveness analysis
- Optimization opportunities

## Error Handling

### Common Issues and Solutions

#### Training Job Not Found

```
Error: Training job 'job-name' not found
```

**Solution**: Verify the job name and ensure it exists in the specified region.

#### AWS Permissions

```
Error: Access denied for SageMaker operation
```

**Solution**: Ensure your IAM role has the required permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sagemaker:DescribeTrainingJob",
        "sagemaker:ListTrainingJobs",
        "s3:ListBucket",
        "s3:GetObject",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

#### CloudWatch Logs Access

```
Warning: Could not analyze training metrics
```

**Solution**: Ensure CloudWatch logs permissions and verify the log group exists.

## Integration Examples

### With CI/CD Pipelines

```bash
#!/bin/bash
# Automated analysis in CI/CD
python model_artifact_analysis.py \
  --job-name $TRAINING_JOB_NAME \
  --output-file analysis_results.json

# Check if analysis passed
if grep -q '"validation_status": "PASS"' analysis_results.json; then
  echo "Model validation passed"
  exit 0
else
  echo "Model validation failed"
  exit 1
fi
```

### With Monitoring Systems

```python
import json
from model_artifact_analysis import NovaModelAnalyzer

def monitor_training_jobs(job_names):
    analyzer = NovaModelAnalyzer()
    results = []

    for job_name in job_names:
        try:
            analysis = analyzer.analyze_training_job(job_name)
            if analysis['job_details']['status'] == 'Failed':
                # Send alert
                send_alert(f"Training job {job_name} failed")
            results.append(analysis)
        except Exception as e:
            print(f"Error analyzing {job_name}: {e}")

    return results
```

### Batch Analysis Script

```bash
#!/bin/bash
# Analyze all jobs from the last week
JOBS=$(aws sagemaker list-training-jobs \
  --creation-time-after $(date -d '7 days ago' -u +%Y-%m-%dT%H:%M:%S) \
  --query 'TrainingJobSummaries[].TrainingJobName' \
  --output text)

for job in $JOBS; do
  echo "Analyzing job: $job"
  python model_artifact_analysis.py \
    --job-name $job \
    --output-file "analysis_${job}.json"
done
```

## Best Practices

### Performance Optimization

1. **Regular Analysis**: Run analysis after each training job
2. **Trend Monitoring**: Track metrics across multiple jobs
3. **Resource Optimization**: Optimize costs based on analysis results
4. **Early Detection**: Identify issues before they impact production

### Automation

1. **Scheduled Analysis**: Set up automated analysis workflows
2. **Alert Integration**: Connect with monitoring systems
3. **Report Generation**: Automate report creation and distribution
4. **Threshold Monitoring**: Set up alerts for performance degradation

### Data Management

1. **Result Storage**: Systematically store analysis results
2. **Historical Tracking**: Maintain analysis history for trends
3. **Comparison Baselines**: Establish performance baselines
4. **Documentation**: Document findings and actions taken

## Troubleshooting

### Debug Mode

Enable verbose logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

analyzer = NovaModelAnalyzer()
analysis = analyzer.analyze_training_job('my-job')
```

### Common Solutions

1. **Timeout Issues**: Increase timeout for large log analysis
2. **Memory Issues**: Process metrics in batches for large jobs
3. **Permission Issues**: Verify IAM roles and policies
4. **Region Issues**: Ensure consistent region configuration

## Contributing

To contribute to this module:

1. Follow the existing code structure
2. Add comprehensive error handling
3. Include unit tests for new features
4. Update documentation for new functionality
5. Ensure backward compatibility

## Support

For issues and questions:

- Check the troubleshooting section
- Review AWS CloudWatch logs
- Verify IAM permissions
- Test with a simple training job first

## Version History

- **v1.0**: Initial release with basic analysis
- **v1.1**: Added metrics analysis and CloudWatch integration
- **v1.2**: Enhanced artifact validation
- **v1.3**: Added job comparison and batch analysis features
- **v2.0**: Major enhancement with comprehensive artifact analysis
  - Automatic S3 artifact download and extraction
  - Escrow model URI discovery from manifest.json
  - Multi-format training log parsing (JSONL, JSON, CSV, TXT, LOG)
  - Advanced loss curve analysis and visualization
  - Statistical convergence assessment
  - Overfitting detection algorithms
  - High-quality matplotlib plot generation
  - Comprehensive error handling and cleanup
