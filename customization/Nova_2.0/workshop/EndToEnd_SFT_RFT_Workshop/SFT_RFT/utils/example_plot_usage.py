#!/usr/bin/env python3
"""
Simple example showing how to import and use the plotting functions.
"""

# Example 1: Import from utils.plot_training_metrics
from utils.plot_training_metrics import plot_step_wise_training_metrics, plot_training_metrics_combined

# Example 2: Import from utils package
from utils import plot_step_wise_training_metrics

# Example 3: Import all
import utils


def basic_usage_example():
    """Basic usage - plot all metrics and save to file"""
    
    # Plot all metrics
    plot_step_wise_training_metrics(
        csv_path='extracted/step_wise_training_metrics.csv',
        output_path='training_metrics.png'
    )
    print("✓ Plot saved to training_metrics.png")


def plot_specific_metrics_example():
    """Plot only specific metrics"""
    
    plot_step_wise_training_metrics(
        csv_path='extracted/step_wise_training_metrics.csv',
        output_path='selected_metrics.png',
        metrics=['train_reward_mean', 'policy_entropy']
    )
    print("✓ Selected metrics plot saved")


def combined_plot_example():
    """Plot all metrics normalized on one plot"""
    
    plot_training_metrics_combined(
        csv_path='extracted/step_wise_training_metrics.csv',
        output_path='combined_metrics.png'
    )
    print("✓ Combined plot saved")


def complete_workflow_example():
    """Complete workflow: download from S3, extract, and plot"""
    
    from utils import download_and_unpack_s3_tar, plot_step_wise_training_metrics
    
    # Step 1: Download and extract from S3
    files = download_and_unpack_s3_tar(
        bucket_name='my-bucket',
        s3_key='training/output.tar.gz',
        extract_to='./extracted'
    )
    
    # Step 2: Plot the metrics
    plot_step_wise_training_metrics(
        csv_path='extracted/step_wise_training_metrics.csv',
        output_path='training_metrics.png'
    )
    
    print("✓ Complete workflow finished!")


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                     QUICK USAGE EXAMPLES                                   ║
╚════════════════════════════════════════════════════════════════════════════╝

# Basic usage - plot all metrics
from utils import plot_step_wise_training_metrics

plot_step_wise_training_metrics(
    csv_path='extracted/step_wise_training_metrics.csv',
    output_path='metrics.png'
)

# Plot specific metrics only
plot_step_wise_training_metrics(
    csv_path='extracted/step_wise_training_metrics.csv',
    metrics=['train_reward_mean', 'policy_entropy'],
    output_path='selected_metrics.png'
)

# Combined normalized plot
from utils import plot_training_metrics_combined

plot_training_metrics_combined(
    csv_path='extracted/step_wise_training_metrics.csv',
    output_path='combined.png'
)

# Complete workflow with S3 download
from utils import download_and_unpack_s3_tar, plot_step_wise_training_metrics

# Download and extract
files = download_and_unpack_s3_tar(
    bucket_name='my-bucket',
    s3_key='training/output.tar.gz',
    extract_to='./extracted'
)

# Plot metrics
plot_step_wise_training_metrics(
    csv_path='extracted/step_wise_training_metrics.csv',
    output_path='training_metrics.png'
)

╚════════════════════════════════════════════════════════════════════════════╝
""")
