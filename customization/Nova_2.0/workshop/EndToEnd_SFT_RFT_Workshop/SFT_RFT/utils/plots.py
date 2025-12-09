import matplotlib.pyplot as plt
import numpy as np
import glob
import os
import pandas as pd
import seaborn as sns
from pathlib import Path
from typing import Optional, List, Union

def find_json_files(path):
    return glob.glob(os.path.join(path, "*.json"))

def plot_metrics(results, title=None):
    # Extract metrics and their standard errors
    metrics = {}
    for key, value in results.items():
        if not key.endswith("_stderr"):
            metrics[key] = {"value": value, "stderr": results.get(f"{key}_stderr", 0)}

    # Sort metrics by value for better visualization
    sorted_metrics = dict(
        sorted(metrics.items(), key=lambda x: x[1]["value"], reverse=True)
    )

    # Prepare data for plotting
    labels = list(sorted_metrics.keys())
    values = [sorted_metrics[label]["value"] for label in labels]
    errors = [sorted_metrics[label]["stderr"] for label in labels]

    # Normalize BLEU score to be on the same scale as other metrics (0-1)
    bleu_index = labels.index("bleu") if "bleu" in labels else -1
    if bleu_index >= 0:
        values[bleu_index] /= 100
        errors[bleu_index] /= 100

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8))

    # Create bar chart
    x = np.arange(len(labels))
    bars = ax.bar(
        x,
        values,
        yerr=errors,
        align="center",
        alpha=0.7,
        capsize=5,
        color="skyblue",
        ecolor="black",
    )

    # Add labels and title
    ax.set_ylabel("Score")
    ax.set_title(title if title else "Evaluation Metrics")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylim(0, 1.0)

    # Add value labels on top of bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        # Convert BLEU back to its original scale for display
        display_value = values[i] * 100 if labels[i] == "bleu" else values[i]
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 0.01,
            f"{display_value:.2f}",
            ha="center",
            va="bottom",
        )

    # Add a note about BLEU
    if bleu_index >= 0:
        ax.text(
            0.5,
            -0.15,
            "Note: BLEU score shown as percentage (original: {:.2f})".format(
                values[bleu_index] * 100
            ),
            transform=ax.transAxes,
            ha="center",
            fontsize=9,
        )

    plt.tight_layout()
    return fig

def plot_grouped_bar_chart(df, title="Model Evaluation Comparison", figsize=(12, 6)):
    """
    Create a grouped bar chart comparing all metrics across models.
    
    Args:
        df: DataFrame with model results (rows=models, columns=metrics)
        title: Title for the plot
        figsize: Figure size tuple (width, height)
    
    Returns:
        fig: Matplotlib figure object
    """
    # Identify the model name column
    if 'model_conf' in df.columns:
        model_col = 'model_conf'
    else:
        model_col = df.columns[0]
    
    # Get metric columns (all except model name column)
    metric_cols = [col for col in df.columns if col != model_col]
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    
    # Setup bar positions
    x = np.arange(len(metric_cols))
    width = 0.8 / len(df)  # Adjust width based on number of models
    
    # Plot bars for each model
    for i, model in enumerate(df[model_col]):
        values = df[df[model_col] == model][metric_cols].values[0]
        bars = ax.bar(x + i * width, values, width, label=model, alpha=0.8)
        
        # Add value labels on top of bars
        for j, bar in enumerate(bars):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 0.01,
                f'{height:.2f}',
                ha='center',
                va='bottom',
                fontsize=9
            )
    
    # Formatting
    ax.set_xlabel('Metrics', fontweight='bold', fontsize=12)
    ax.set_ylabel('Score', fontweight='bold', fontsize=12)
    ax.set_title(title, fontweight='bold', fontsize=14)
    ax.set_xticks(x + width * (len(df) - 1) / 2)
    ax.set_xticklabels(metric_cols, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, 1)  # Assuming metrics are 0-1 scale
    
    plt.tight_layout()
    return fig

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

def plot_model_comparison(df, title="Model Evaluation Comparison", figsize=(14, 8)):
    """
    Create comprehensive plots for model evaluation results.
    
    Args:
        df: DataFrame with model results (rows=models, columns=metrics)
        title: Main title for the plot
        figsize: Figure size tuple (width, height)
    """
    # Identify the model name column (usually first column or named 'model_conf')
    if 'model_conf' in df.columns:
        model_col = 'model_conf'
    else:
        model_col = df.columns[0]
    
    # Get metric columns (all except model name column)
    metric_cols = [col for col in df.columns if col != model_col]
    
    # Set style
    sns.set_style("whitegrid")
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    fig.suptitle(title, fontsize=16, fontweight='bold')
    
    # Plot 1: Grouped Bar Chart
    ax1 = axes[0, 0]
    x = np.arange(len(metric_cols))
    width = 0.25
    
    for i, model in enumerate(df[model_col]):
        values = df[df[model_col] == model][metric_cols].values[0]
        ax1.bar(x + i * width, values, width, label=model, alpha=0.8)
    
    ax1.set_xlabel('Metrics', fontweight='bold')
    ax1.set_ylabel('Score', fontweight='bold')
    ax1.set_title('Grouped Bar Chart - All Metrics')
    ax1.set_xticks(x + width)
    ax1.set_xticklabels(metric_cols, rotation=45, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Heatmap
    ax2 = axes[0, 1]
    heatmap_data = df.set_index(model_col)[metric_cols]
    sns.heatmap(heatmap_data, annot=True, fmt='.2f', cmap='YlGnBu', 
                ax=ax2, cbar_kws={'label': 'Score'})
    ax2.set_title('Heatmap - Performance Overview')
    ax2.set_xlabel('Metrics', fontweight='bold')
    ax2.set_ylabel('Models', fontweight='bold')
    
    # Plot 3: Radar Chart
    ax3 = axes[1, 0]
    angles = np.linspace(0, 2 * np.pi, len(metric_cols), endpoint=False).tolist()
    angles += angles[:1]  # Complete the circle
    
    ax3 = plt.subplot(2, 2, 3, projection='polar')
    
    for model in df[model_col]:
        values = df[df[model_col] == model][metric_cols].values[0].tolist()
        values += values[:1]  # Complete the circle
        ax3.plot(angles, values, 'o-', linewidth=2, label=model)
        ax3.fill(angles, values, alpha=0.15)
    
    ax3.set_xticks(angles[:-1])
    ax3.set_xticklabels(metric_cols, size=8)
    ax3.set_ylim(0, 1)
    ax3.set_title('Radar Chart - Model Comparison')
    ax3.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    ax3.grid(True)
    
    # Plot 4: Line Plot
    ax4 = axes[1, 1]
    for model in df[model_col]:
        values = df[df[model_col] == model][metric_cols].values[0]
        ax4.plot(metric_cols, values, marker='o', linewidth=2, 
                markersize=8, label=model, alpha=0.8)
    
    ax4.set_xlabel('Metrics', fontweight='bold')
    ax4.set_ylabel('Score', fontweight='bold')
    ax4.set_title('Line Plot - Metric Trends')
    ax4.set_xticklabels(metric_cols, rotation=45, ha='right')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim(0, 1)
    
    plt.tight_layout()
    return fig

def plot_single_metric_comparison(df, metric_name, figsize=(10, 6)):
    """
    Plot comparison for a single metric across all models.
    
    Args:
        df: DataFrame with model results
        metric_name: Name of the metric column to plot
        figsize: Figure size tuple
    """
    if 'model_conf' in df.columns:
        model_col = 'model_conf'
    else:
        model_col = df.columns[0]
    
    fig, ax = plt.subplots(figsize=figsize)
    
    models = df[model_col]
    values = df[metric_name]
    
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(models)))
    bars = ax.bar(models, values, color=colors, alpha=0.8, edgecolor='black')
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.3f}',
                ha='center', va='bottom', fontweight='bold')
    
    ax.set_ylabel('Score', fontweight='bold', fontsize=12)
    ax.set_xlabel('Model', fontweight='bold', fontsize=12)
    ax.set_title(f'{metric_name} Comparison', fontweight='bold', fontsize=14)
    ax.set_ylim(0, max(values) * 1.15)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    return fig        