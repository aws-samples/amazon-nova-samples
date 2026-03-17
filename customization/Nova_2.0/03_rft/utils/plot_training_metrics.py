import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Optional, List, Union


def plot_step_wise_training_metrics(
    csv_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    metrics: Optional[List[str]] = None,
    figsize: tuple = (15, 10),
    style: str = 'darkgrid'
) -> None:
    """
    Plot step-wise training metrics from a CSV file.
    
    Args:
        csv_path (str or Path): Path to the step_wise_training_metrics.csv file
        output_path (str or Path, optional): Path to save the plot. If None, displays the plot.
        metrics (List[str], optional): List of metrics to plot. If None, plots all available metrics.
        figsize (tuple): Figure size (width, height) in inches
        style (str): Seaborn style ('darkgrid', 'whitegrid', 'dark', 'white', 'ticks')
    
    Returns:
        None
    
    Example:
        >>> plot_step_wise_training_metrics(
        ...     csv_path='extracted/step_wise_training_metrics.csv',
        ...     output_path='training_metrics.png'
        ... )
    """
    
    # Set style
    sns.set_style(style)
    
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    print(f"Loaded training metrics with {len(df)} steps")
    print(f"Columns: {list(df.columns)}")
    
    # Define default metrics to plot (exclude step_number and epoch_number)
    if metrics is None:
        metrics = [col for col in df.columns if col not in ['step_number', 'epoch_number']]
    
    # Validate metrics
    for metric in metrics:
        if metric not in df.columns:
            raise ValueError(f"Metric '{metric}' not found in CSV. Available: {list(df.columns)}")
    
    # Calculate number of rows and columns for subplots
    n_metrics = len(metrics)
    n_cols = 2
    n_rows = (n_metrics + 1) // 2
    
    # Create figure and subplots
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    fig.suptitle('Step-Wise Training Metrics', fontsize=16, fontweight='bold')
    
    # Flatten axes array for easier iteration
    if n_rows == 1:
        axes = [axes] if n_cols == 1 else axes
    else:
        axes = axes.flatten()
    
    # Plot each metric
    for idx, metric in enumerate(metrics):
        ax = axes[idx]
        
        # Plot the metric
        ax.plot(df['step_number'], df[metric], linewidth=2, marker='o', 
                markersize=4, alpha=0.7, label=metric)
        
        # Add title and labels
        ax.set_title(metric.replace('_', ' ').title(), fontsize=12, fontweight='bold')
        ax.set_xlabel('Step Number', fontsize=10)
        ax.set_ylabel(metric.replace('_', ' ').title(), fontsize=10)
        
        # Add grid
        ax.grid(True, alpha=0.3)
        
        # Add trend line
        z = np.polyfit(df['step_number'], df[metric], 1)
        p = np.poly1d(z)
        ax.plot(df['step_number'], p(df['step_number']), 
                linestyle='--', alpha=0.5, color='red', linewidth=1.5, 
                label='Trend')
        
        # Add legend
        ax.legend(loc='best', fontsize=8)
        
        # Format y-axis
        ax.ticklabel_format(style='sci', axis='y', scilimits=(-3, 3))
    
    # Hide unused subplots
    for idx in range(n_metrics, len(axes)):
        axes[idx].set_visible(False)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save or display
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\nPlot saved to: {output_path}")
    else:
        plt.show()
    
    # Print summary statistics
    print("\n" + "=" * 80)
    print("TRAINING METRICS SUMMARY")
    print("=" * 80)
    for metric in metrics:
        print(f"\n{metric.replace('_', ' ').title()}:")
        print(f"  Initial: {df[metric].iloc[0]:.6f}")
        print(f"  Final:   {df[metric].iloc[-1]:.6f}")
        print(f"  Mean:    {df[metric].mean():.6f}")
        print(f"  Std:     {df[metric].std():.6f}")
        print(f"  Min:     {df[metric].min():.6f}")
        print(f"  Max:     {df[metric].max():.6f}")
    print("=" * 80)


def plot_training_metrics_combined(
    csv_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    figsize: tuple = (15, 6)
) -> None:
    """
    Plot all training metrics on a single normalized plot for comparison.
    
    Args:
        csv_path (str or Path): Path to the step_wise_training_metrics.csv file
        output_path (str or Path, optional): Path to save the plot. If None, displays the plot.
        figsize (tuple): Figure size (width, height) in inches
    
    Returns:
        None
    """
    
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Get metrics (exclude step_number and epoch_number)
    metrics = [col for col in df.columns if col not in ['step_number', 'epoch_number']]
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    
    # Normalize and plot each metric
    for metric in metrics:
        # Min-max normalization
        normalized = (df[metric] - df[metric].min()) / (df[metric].max() - df[metric].min())
        ax.plot(df['step_number'], normalized, linewidth=2, marker='o', 
                markersize=3, alpha=0.7, label=metric.replace('_', ' ').title())
    
    # Formatting
    ax.set_title('Normalized Training Metrics Comparison', fontsize=14, fontweight='bold')
    ax.set_xlabel('Step Number', fontsize=12)
    ax.set_ylabel('Normalized Value (0-1)', fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=9)
    
    plt.tight_layout()
    
    # Save or display
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Combined plot saved to: {output_path}")
    else:
        plt.show()


# Import numpy for trend line calculation
import numpy as np


if __name__ == "__main__":
    # Example usage
    print("Example usage:")
    print("\nPlot all metrics:")
    print("  plot_step_wise_training_metrics('extracted/step_wise_training_metrics.csv')")
    print("\nPlot specific metrics:")
    print("  plot_step_wise_training_metrics(")
    print("      'extracted/step_wise_training_metrics.csv',")
    print("      metrics=['train_reward_mean', 'policy_entropy']")
    print("  )")
    print("\nSave plot to file:")
    print("  plot_step_wise_training_metrics(")
    print("      'extracted/step_wise_training_metrics.csv',")
    print("      output_path='training_metrics.png'")
    print("  )")
