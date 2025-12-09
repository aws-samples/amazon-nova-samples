#!/usr/bin/env python3
"""
Nova Model Artifact Analysis Module

This module analyzes Nova model training artifacts including:
1. Model performance metrics
2. Training logs analysis
3. Model artifact validation
4. Training job status monitoring
5. Model comparison and benchmarking

Usage:
python model_artifact_analysis.py --job-name my-training-job --analysis-type all
"""

import boto3
import json
import os
import sys
import argparse
import time
import tarfile
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

class NovaModelAnalyzer:
    """Analyzer for Nova model training artifacts and performance."""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.sagemaker_client = boto3.client('sagemaker', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)
        self.logs_client = boto3.client('logs', region_name=region)
    
    def get_training_job_details(self, job_name: str) -> Dict[str, Any]:
        """Get detailed information about a training job."""
        try:
            response = self.sagemaker_client.describe_training_job(TrainingJobName=job_name)
            return response
        except Exception as e:
            raise Exception(f"Failed to get training job details: {e}")
    
    def analyze_training_metrics(self, job_name: str) -> Dict[str, Any]:
        """Analyze training metrics from CloudWatch logs."""
        try:
            job_details = self.get_training_job_details(job_name)
            log_group = f"/aws/sagemaker/TrainingJobs/{job_name}"
            
            # Get log streams
            log_streams = self.logs_client.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True
            )
            
            metrics = {
                'training_loss': [],
                'validation_loss': [],
                'learning_rate': [],
                'timestamps': []
            }
            
            # Parse logs for metrics
            for stream in log_streams['logStreams']:
                events = self.logs_client.get_log_events(
                    logGroupName=log_group,
                    logStreamName=stream['logStreamName']
                )
                
                for event in events['events']:
                    message = event['message']
                    timestamp = event['timestamp']
                    
                    # Extract metrics from log messages
                    if 'loss:' in message.lower():
                        # Parse training loss
                        pass
                    if 'val_loss:' in message.lower():
                        # Parse validation loss
                        pass
            
            return metrics
        except Exception as e:
            print(f"Warning: Could not analyze training metrics: {e}")
            return {}
    
    def list_s3_artifacts(self, s3_model_path: str) -> List[str]:
        """List available artifacts in the S3 path for debugging."""
        try:
            # Parse S3 path
            bucket = s3_model_path.replace('s3://', '').split('/')[0]
            prefix = '/'.join(s3_model_path.replace('s3://', '').split('/')[1:-1])  # Remove filename
            
            print(f"🔍 Listing S3 objects in: s3://{bucket}/{prefix}")
            
            # List objects in S3
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=100
            )
            
            artifacts = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    artifacts.append(obj['Key'])
                    print(f"   📄 Found: s3://{bucket}/{obj['Key']} ({obj['Size']} bytes)")
            else:
                print(f"   ⚠️  No objects found in s3://{bucket}/{prefix}")
            
            return artifacts
            
        except Exception as e:
            print(f"⚠️  Could not list S3 artifacts: {e}")
            return []

    def download_and_extract_artifacts(self, s3_model_path: str, extract_dir: str = None) -> str:
        """Download and extract model artifacts from S3."""
        try:
            print("📥 Downloading model artifacts...")
            
            # Parse S3 path
            bucket = s3_model_path.replace('s3://', '').split('/')[0]
            key = '/'.join(s3_model_path.replace('s3://', '').split('/')[1:])
            
            print(f"🔍 Checking S3 location: s3://{bucket}/{key}")
            
            # Debug: List all objects in the bucket with similar prefix to verify correct path
            prefix = '/'.join(key.split('/')[:-1])
            print(f"🔍 Listing all objects with prefix: s3://{bucket}/{prefix}")
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=bucket,
                    Prefix=prefix
                )
                if 'Contents' in response:
                    print(f"Found {len(response['Contents'])} objects with this prefix:")
                    for obj in response['Contents'][:10]:  # Show first 10 objects
                        print(f"   - s3://{bucket}/{obj['Key']}")
                else:
                    print("No objects found with this prefix!")
            except Exception as e:
                print(f"Error listing objects: {e}")
            
            # Check if the object exists first
            try:
                self.s3_client.head_object(Bucket=bucket, Key=key)
            except self.s3_client.exceptions.NoSuchKey:
                # List available artifacts for debugging
                print("❌ S3 object not found. Listing available artifacts:")
                self.list_s3_artifacts(s3_model_path)
                raise Exception(f"S3 object not found: s3://{bucket}/{key}")
            except Exception as e:
                if "404" in str(e) or "Not Found" in str(e):
                    # List available artifacts for debugging
                    print("❌ S3 object not found. Listing available artifacts:")
                    self.list_s3_artifacts(s3_model_path)
                    raise Exception(f"S3 object not found: s3://{bucket}/{key}")
                else:
                    raise Exception(f"Error accessing S3 object: {e}")
            
            # Create persistent directory in current working directory if not provided
            if extract_dir is None:
                # Extract job name from S3 path for a more descriptive directory name
                job_name = key.split('/')[-3] if len(key.split('/')) >= 3 else 'unknown_job'
                extract_dir = os.path.join(os.getcwd(), 'extracted_artifacts', job_name)
                os.makedirs(extract_dir, exist_ok=True)
                print(f"📁 Created persistent directory for artifacts: {extract_dir}")
            
            # Download the tar.gz file
            local_tar_path = os.path.join(extract_dir, 'output.tar.gz')
            
            try:
                self.s3_client.download_file(bucket, key, local_tar_path)
                print(f"✅ Downloaded artifacts to: {local_tar_path}")
            except Exception as e:
                if "404" in str(e) or "Not Found" in str(e):
                    raise Exception(f"S3 object not found during download: s3://{bucket}/{key}")
                else:
                    raise Exception(f"Failed to download from S3: {e}")
            
            # Verify the downloaded file exists and has content
            if not os.path.exists(local_tar_path):
                raise Exception(f"Downloaded file not found: {local_tar_path}")
            
            file_size = os.path.getsize(local_tar_path)
            if file_size == 0:
                raise Exception(f"Downloaded file is empty: {local_tar_path}")
            
            print(f"📊 Downloaded file size: {file_size / (1024*1024):.2f} MB")
            
            # Extract the tar.gz file
            print("📦 Extracting artifacts...")
            try:
                with tarfile.open(local_tar_path, 'r:gz') as tar:
                    tar.extractall(path=extract_dir)
                print(f"✅ Extracted artifacts to: {extract_dir}")
            except tarfile.ReadError as e:
                raise Exception(f"Failed to extract tar.gz file (may be corrupted): {e}")
            except Exception as e:
                raise Exception(f"Failed to extract artifacts: {e}")
            
            return extract_dir
            
        except Exception as e:
            # Clean up on failure
            if extract_dir and os.path.exists(extract_dir):
                try:
                    shutil.rmtree(extract_dir)
                except:
                    pass
            raise Exception(f"Failed to download and extract artifacts: {e}")
    
    def find_escrow_model_uri(self, extract_dir: str) -> str:
        """Find the escrow_model_uri from manifest.json."""
        try:
            # First check if manifest.json is directly in the extract_dir
            manifest_path = os.path.join(extract_dir, 'manifest.json')
            
            if not os.path.exists(manifest_path):
                # Try alternative paths
                for root, dirs, files in os.walk(extract_dir):
                    if 'manifest.json' in files:
                        manifest_path = os.path.join(root, 'manifest.json')
                        break
                else:
                    raise FileNotFoundError("manifest.json not found in extracted artifacts")
            
            print(f"📄 Reading manifest from: {manifest_path}")
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            escrow_model_uri = manifest.get('checkpoint_s3_bucket')
            if not escrow_model_uri:
                raise KeyError("checkpoint_s3_bucket not found in manifest.json")
            
            print(f"🔗 Found escrow model URI: {escrow_model_uri}")
            return escrow_model_uri
            
        except Exception as e:
            raise Exception(f"Failed to find escrow model URI: {e}")
    
    def analyze_training_loss_curve(self, extract_dir: str, job_name: str) -> Dict[str, Any]:
        """Analyze training loss curve from extracted artifacts."""
        try:
            # Print the contents of the extracted directory to see what files are available
            print("📂 Listing contents of extracted directory:")
            for root, dirs, files in os.walk(extract_dir):
                if 'train_output' in root:
                    print(f"Contents of {root}:")
                    for file in files:
                        print(f"  - {file}")
            
            # Check specifically for the expected files
            train_output_dir = os.path.join(extract_dir, 'tmp', 'train_output')
            if os.path.exists(train_output_dir):
                print(f"\n📂 Contents of {train_output_dir}:")
                for file in os.listdir(train_output_dir):
                    print(f"  - {file}")
            else:
                print(f"\n❌ Directory not found: {train_output_dir}")
                
                # Try alternative path
                alt_train_output_dir = os.path.join(extract_dir, 'train_output')
                if os.path.exists(alt_train_output_dir):
                    print(f"📂 Contents of {alt_train_output_dir}:")
                    for file in os.listdir(alt_train_output_dir):
                        print(f"  - {file}")
            
            print("\n📈 Analyzing training loss curve...")
            
            # Look for the metrics files at the same level as manifest.json
            # First find the manifest.json file
            manifest_path = None
            for root, dirs, files in os.walk(extract_dir):
                if 'manifest.json' in files:
                    manifest_path = os.path.join(root, 'manifest.json')
                    break
            
            if manifest_path:
                # The metrics files should be in the same directory as manifest.json
                manifest_dir = os.path.dirname(manifest_path)
                print(f"Looking for metrics files in the same directory as manifest.json: {manifest_dir}")
                
                possible_train_paths = [
                    os.path.join(manifest_dir, 'step_wise_training_metrics.csv')
                ]
                
                possible_val_paths = [
                    os.path.join(manifest_dir, 'validation_metrics.csv')
                ]
            else:
                # Fallback to the original paths if manifest.json is not found
                possible_train_paths = [
                    os.path.join(extract_dir, 'step_wise_training_metrics.csv'),
                    os.path.join(extract_dir, 'tmp', 'train_output', 'step_wise_training_metrics.csv'),
                    os.path.join(extract_dir, 'train_output', 'step_wise_training_metrics.csv')
                ]
                
                possible_val_paths = [
                    os.path.join(extract_dir, 'validation_metrics.csv'),
                    os.path.join(extract_dir, 'tmp', 'train_output', 'validation_metrics.csv'),
                    os.path.join(extract_dir, 'train_output', 'validation_metrics.csv')
                ]
            
            # Find the first existing train and val paths
            train_csv_path = next((path for path in possible_train_paths if os.path.exists(path)), None)
            val_csv_path = next((path for path in possible_val_paths if os.path.exists(path)), None)
            
            if train_csv_path:
                print(f"Found training metrics at: {train_csv_path}")
            else:
                print("Training metrics file (step_wise_training_metrics.csv) not found in expected locations")
                
            if val_csv_path:
                print(f"Found validation metrics at: {val_csv_path}")
            else:
                print("Validation metrics file (validation_metrics.csv) not found in expected locations")
            
            training_losses = []
            validation_losses = []
            steps = []
            
            # Try to read the specific CSV files
            train_df = None
            val_df = None
            
            if os.path.exists(train_csv_path):
                try:
                    print(f"📖 Reading training metrics: {train_csv_path}")
                    train_df = pd.read_csv(train_csv_path)
                    if 'training_loss' in train_df.columns and 'step_number' in train_df.columns:
                        training_losses = train_df['training_loss'].dropna().tolist()
                        steps = train_df['step_number'].dropna().tolist()
                        print(f"✅ Found {len(training_losses)} training loss values")
                except Exception as e:
                    print(f"⚠️  Could not parse training CSV {train_csv_path}: {e}")
            
            if os.path.exists(val_csv_path):
                try:
                    print(f"📖 Reading validation metrics: {val_csv_path}")
                    val_df = pd.read_csv(val_csv_path)
                    if 'validation_loss' in val_df.columns:
                        validation_losses = val_df['validation_loss'].dropna().tolist()
                        print(f"✅ Found {len(validation_losses)} validation loss values")
                except Exception as e:
                    print(f"⚠️  Could not parse validation CSV {val_csv_path}: {e}")
            
            # If specific CSV files not found, provide clear message
            if not training_losses and not validation_losses:
                print("📊 Specific metrics files (step_wise_training_metrics.csv and validation_metrics.csv) not found")
                metrics_files = []
                
                # Only search for the exact files we need
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file == 'step_wise_training_metrics.csv' or file == 'validation_metrics.csv':
                            metrics_files.append(os.path.join(root, file))
                            print(f"Found metrics file in unexpected location: {os.path.join(root, file)}")
                
                print(f"📊 Found {len(metrics_files)} potential metrics files")
                
                # Parse general metrics files
                epochs = []
                for metrics_file in metrics_files:
                    try:
                        print(f"📖 Parsing: {metrics_file}")
                        
                        if metrics_file.endswith('.csv'):
                            try:
                                df = pd.read_csv(metrics_file)
                                
                                # Look for common column names
                                loss_cols = [col for col in df.columns if 'loss' in col.lower() and not any(x in col.lower() for x in ['val', 'valid', 'validation'])]
                                val_loss_cols = [col for col in df.columns if ('val' in col.lower() or 'valid' in col.lower() or 'validation' in col.lower()) and 'loss' in col.lower()]
                                epoch_cols = [col for col in df.columns if 'epoch' in col.lower()]
                                step_cols = [col for col in df.columns if any(x in col.lower() for x in ['step', 'iter', 'iteration', 'batch'])]
                                
                                print(f"Found columns: {df.columns.tolist()}")
                                
                                if loss_cols and not training_losses:
                                    print(f"Using column '{loss_cols[0]}' for training loss")
                                    training_losses.extend(df[loss_cols[0]].dropna().tolist())
                                
                                if val_loss_cols and not validation_losses:
                                    print(f"Using column '{val_loss_cols[0]}' for validation loss")
                                    validation_losses.extend(df[val_loss_cols[0]].dropna().tolist())
                                
                                if epoch_cols:
                                    epochs.extend(df[epoch_cols[0]].dropna().tolist())
                                elif step_cols and not steps:
                                    steps.extend(df[step_cols[0]].dropna().tolist())
                                    
                            except Exception as e:
                                print(f"⚠️  Could not parse CSV {metrics_file}: {e}")
                                continue
                    
                    except Exception as e:
                        print(f"⚠️  Could not parse {metrics_file}: {e}")
                        continue
            
            # Create loss curve visualization using the specific plotting approach
            loss_curve_path = self.create_loss_curve_plot_from_csv(
                train_df, val_df, training_losses, validation_losses, steps, job_name
            )
            
            # Analyze loss trends
            analysis = self.analyze_loss_trends(training_losses, validation_losses)
            
            # Count how many metrics files were found
            metrics_files_count = 0
            if train_df is not None:
                metrics_files_count += 1
            if val_df is not None:
                metrics_files_count += 1
            
            return {
                'training_losses': training_losses,
                'validation_losses': validation_losses,
                'epochs': [],
                'steps': steps,
                'loss_curve_plot': loss_curve_path,
                'analysis': analysis,
                'metrics_files_found': metrics_files_count
            }
            
        except Exception as e:
            print(f"⚠️  Error analyzing training loss curve: {e}")
            return {
                'error': str(e),
                'training_losses': [],
                'validation_losses': [],
                'epochs': [],
                'steps': []
            }
    
    def create_loss_curve_plot_from_csv(self, train_df, val_df, training_losses: List[float], 
                                       validation_losses: List[float], steps: List[int], job_name: str) -> str:
        """Create matplotlib plot using the specific CSV approach."""
        try:
            plt.figure(figsize=(10, 6))
            
            has_data = False
            
            # Use DataFrame approach if available
            if train_df is not None and 'step_number' in train_df.columns and 'training_loss' in train_df.columns:
                plt.plot(train_df['step_number'], train_df['training_loss'], label='Training Loss', color='blue')
                has_data = True
            elif training_losses:
                # If we have training losses but no steps, create indices
                if steps and len(steps) >= len(training_losses):
                    plt.plot(steps[:len(training_losses)], training_losses, label='Training Loss', color='blue')
                else:
                    # Create step indices if no steps provided or insufficient steps
                    x_values = list(range(len(training_losses)))
                    plt.plot(x_values, training_losses, label='Training Loss', color='blue')
                has_data = True
            
            if val_df is not None and 'step_number' in val_df.columns and 'validation_loss' in val_df.columns:
                plt.plot(val_df['step_number'], val_df['validation_loss'], label='Validation Loss', color='red')
                has_data = True
            elif validation_losses:
                # Use same steps or create indices
                if steps and len(steps) >= len(validation_losses):
                    val_steps = steps[:len(validation_losses)]
                else:
                    val_steps = list(range(len(validation_losses)))
                plt.plot(val_steps, validation_losses, label='Validation Loss', color='red')
                has_data = True
            
            plt.xlabel('Step Number')
            plt.ylabel('Loss')
            plt.title('Training vs Validation Loss')
            
            # Only add legend if we have data to plot
            if has_data:
                plt.legend()
            else:
                # Add a message when no data is available
                plt.text(0.5, 0.5, 'No training data available', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=plt.gca().transAxes, fontsize=12)
            
            plt.grid(True, alpha=0.3)
            
            # Create output directory in current working directory
            current_dir = os.getcwd()
            plots_dir = os.path.join(current_dir, 'train_loss_curves')
            
            # Create the directory if it doesn't exist
            os.makedirs(plots_dir, exist_ok=True)
            
            # Save plot in the current directory structure
            plot_filename = f'{job_name}_loss_curve.png'
            plot_path = os.path.join(plots_dir, plot_filename)
            
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"📊 Loss curve plot saved to: {plot_path}")
            return plot_path
            
        except Exception as e:
            print(f"⚠️  Error creating loss curve plot: {e}")
            return ""

    def create_loss_curve_plot(self, training_losses: List[float], validation_losses: List[float], 
                              epochs: List[int], steps: List[int], job_name: str, output_dir: str) -> str:
        """Create matplotlib plot of training loss curve."""
        try:
            plt.figure(figsize=(12, 8))
            
            # Determine x-axis (prefer epochs, fallback to steps or indices)
            if epochs and len(epochs) == len(training_losses):
                x_axis = epochs
                x_label = 'Epoch'
            elif steps and len(steps) == len(training_losses):
                x_axis = steps
                x_label = 'Step'
            else:
                x_axis = list(range(len(training_losses)))
                x_label = 'Iteration'
            
            # Plot training loss
            if training_losses:
                plt.plot(x_axis[:len(training_losses)], training_losses, 
                        label='Training Loss', color='blue', linewidth=2)
            
            # Plot validation loss if available
            if validation_losses:
                val_x = x_axis[:len(validation_losses)] if len(validation_losses) <= len(x_axis) else list(range(len(validation_losses)))
                plt.plot(val_x, validation_losses, 
                        label='Validation Loss', color='red', linewidth=2, linestyle='--')
            
            plt.xlabel(x_label)
            plt.ylabel('Loss')
            plt.title(f'Training Loss Curve - {job_name}')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Add trend analysis
            if len(training_losses) > 1:
                # Add trend line for training loss
                z = np.polyfit(range(len(training_losses)), training_losses, 1)
                p = np.poly1d(z)
                plt.plot(x_axis[:len(training_losses)], p(range(len(training_losses))), 
                        "g--", alpha=0.8, label=f'Trend (slope: {z[0]:.6f})')
                plt.legend()
            
            # Create output directory in current working directory
            current_dir = os.getcwd()
            plots_dir = os.path.join(current_dir, 'train_loss_curves')
            
            # Create the directory if it doesn't exist
            os.makedirs(plots_dir, exist_ok=True)
            
            # Save plot in the current directory structure
            plot_filename = f'{job_name}_loss_curve.png'
            plot_path = os.path.join(plots_dir, plot_filename)
            
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"📊 Loss curve plot saved to: {plot_path}")
            return plot_path
            
        except Exception as e:
            print(f"⚠️  Error creating loss curve plot: {e}")
            return ""
    
    def analyze_loss_trends(self, training_losses: List[float], validation_losses: List[float]) -> Dict[str, Any]:
        """Analyze trends in the loss curves."""
        analysis = {}
        
        try:
            if training_losses:
                analysis['training_loss'] = {
                    'initial_loss': training_losses[0],
                    'final_loss': training_losses[-1],
                    'min_loss': min(training_losses),
                    'max_loss': max(training_losses),
                    'loss_reduction': training_losses[0] - training_losses[-1],
                    'loss_reduction_percent': ((training_losses[0] - training_losses[-1]) / training_losses[0]) * 100 if training_losses[0] != 0 else 0,
                    'convergence_assessment': self._assess_convergence(training_losses)
                }
            
            if validation_losses:
                analysis['validation_loss'] = {
                    'initial_loss': validation_losses[0],
                    'final_loss': validation_losses[-1],
                    'min_loss': min(validation_losses),
                    'max_loss': max(validation_losses),
                    'loss_reduction': validation_losses[0] - validation_losses[-1],
                    'loss_reduction_percent': ((validation_losses[0] - validation_losses[-1]) / validation_losses[0]) * 100 if validation_losses[0] != 0 else 0
                }
                
                # Check for overfitting
                if training_losses and len(training_losses) == len(validation_losses):
                    analysis['overfitting_check'] = self._check_overfitting(training_losses, validation_losses)
            
        except Exception as e:
            analysis['error'] = str(e)
        
        return analysis
    
    def _assess_convergence(self, losses: List[float]) -> str:
        """Assess if the training has converged."""
        if len(losses) < 10:
            return "insufficient_data"
        
        # Check last 10% of training for stability
        last_portion = losses[-max(10, len(losses)//10):]
        
        # Calculate variance in the last portion
        variance = np.var(last_portion)
        mean_loss = np.mean(last_portion)
        
        # Calculate coefficient of variation
        cv = (np.sqrt(variance) / mean_loss) if mean_loss != 0 else float('inf')
        
        if cv < 0.01:
            return "converged"
        elif cv < 0.05:
            return "likely_converged"
        elif cv < 0.1:
            return "possibly_converged"
        else:
            return "not_converged"
    
    def _check_overfitting(self, train_losses: List[float], val_losses: List[float]) -> Dict[str, Any]:
        """Check for signs of overfitting."""
        try:
            # Compare trends in last 20% of training
            split_point = max(1, len(train_losses) * 4 // 5)
            
            train_recent = train_losses[split_point:]
            val_recent = val_losses[split_point:]
            
            if len(train_recent) < 2 or len(val_recent) < 2:
                return {"status": "insufficient_data"}
            
            # Calculate trends
            train_trend = np.polyfit(range(len(train_recent)), train_recent, 1)[0]
            val_trend = np.polyfit(range(len(val_recent)), val_recent, 1)[0]
            
            # Check if validation loss is increasing while training loss decreases
            if train_trend < -0.001 and val_trend > 0.001:
                return {
                    "status": "overfitting_detected",
                    "train_trend": train_trend,
                    "val_trend": val_trend
                }
            elif abs(train_trend) < 0.001 and abs(val_trend) < 0.001:
                return {
                    "status": "stable",
                    "train_trend": train_trend,
                    "val_trend": val_trend
                }
            else:
                return {
                    "status": "normal",
                    "train_trend": train_trend,
                    "val_trend": val_trend
                }
                
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def validate_model_artifacts(self, s3_model_path: str) -> Dict[str, Any]:
        """Validate model artifacts in S3."""
        try:
            # Parse S3 path
            bucket = s3_model_path.replace('s3://', '').split('/')[0]
            prefix = '/'.join(s3_model_path.replace('s3://', '').split('/')[1:])
            
            # List objects in S3
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix
            )
            
            artifacts = []
            total_size = 0
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    artifacts.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })
                    total_size += obj['Size']
            
            # Check for required files
            required_files = ['manifest.json', 'model.tar.gz']
            found_files = [artifact['key'].split('/')[-1] for artifact in artifacts]
            missing_files = [f for f in required_files if f not in found_files]
            
            return {
                'artifacts': artifacts,
                'total_size_mb': total_size / (1024 * 1024),
                'artifact_count': len(artifacts),
                'missing_files': missing_files,
                'validation_status': 'PASS' if not missing_files else 'FAIL'
            }
        except Exception as e:
            return {
                'validation_status': 'ERROR',
                'error': str(e)
            }
    
    def analyze_training_job(self, job_name: str) -> Dict[str, Any]:
        """Comprehensive analysis of a training job."""
        print(f"🔍 Analyzing training job: {job_name}")
        
        analysis_results = {
            'job_name': job_name,
            'analysis_timestamp': datetime.now().isoformat(),
            'job_details': {},
            'metrics': {},
            'loss_analysis': {},
            'escrow_model_uri': None,
            'recommendations': []
        }
        
        extract_dir = None
        
        try:
            # Get job details
            print("📊 Getting job details...")
            job_details = self.get_training_job_details(job_name)
            job_details['ModelArtifacts']['S3ModelArtifacts']  =  "/".join(job_details.get('ModelArtifacts', {}).get('S3ModelArtifacts').split("/")[:-1])+"/output.tar.gz"
            analysis_results['job_details'] = {
                'status': job_details.get('TrainingJobStatus'),
                'creation_time': job_details.get('CreationTime').isoformat() if job_details.get('CreationTime') else None,
                'training_start_time': job_details.get('TrainingStartTime').isoformat() if job_details.get('TrainingStartTime') else None,
                'training_end_time': job_details.get('TrainingEndTime').isoformat() if job_details.get('TrainingEndTime') else None,
                'instance_type': job_details.get('ResourceConfig', {}).get('InstanceType'),
                'instance_count': job_details.get('ResourceConfig', {}).get('InstanceCount'),
                'model_artifacts': "/".join(job_details.get('ModelArtifacts', {}).get('S3ModelArtifacts').split("/")[:-1])+"/output.tar.gz"
            }
            # Calculate training duration
            if job_details.get('TrainingStartTime') and job_details.get('TrainingEndTime'):
                duration = job_details['TrainingEndTime'] - job_details['TrainingStartTime']
                analysis_results['job_details']['training_duration_minutes'] = duration.total_seconds() / 60
            
            # Download and extract artifacts for detailed analysis
            if job_details.get('ModelArtifacts', {}).get('S3ModelArtifacts'):
                try:
                    s3_model_path = job_details['ModelArtifacts']['S3ModelArtifacts']
                    
                    # Download and extract artifacts
                    extract_dir = self.download_and_extract_artifacts(s3_model_path)
                    
                    # Find escrow model URI from manifest.json
                    try:
                        escrow_model_uri = self.find_escrow_model_uri(extract_dir)
                        analysis_results['escrow_model_uri'] = escrow_model_uri
                    except Exception as e:
                        print(f"⚠️  Could not find escrow model URI: {e}")
                        analysis_results['escrow_model_uri'] = None
                    
                    # Analyze training loss curve
                    loss_analysis = self.analyze_training_loss_curve(extract_dir, job_name)
                    analysis_results['loss_analysis'] = loss_analysis
                    
                except Exception as e:
                    print(f"⚠️  Could not download/analyze artifacts: {e}")
                    analysis_results['loss_analysis'] = {'error': str(e)}
            
            # Analyze metrics from CloudWatch (fallback if artifact analysis fails)
            print("📈 Analyzing CloudWatch metrics...")
            cloudwatch_metrics = self.analyze_training_metrics(job_name)
            analysis_results['metrics'] = cloudwatch_metrics
            
            # Generate recommendations
            analysis_results['recommendations'] = self._generate_recommendations(analysis_results)
            
            print("✅ Analysis completed successfully!")
            return analysis_results
            
        except Exception as e:
            analysis_results['error'] = str(e)
            print(f"❌ Analysis failed: {e}")
            return analysis_results
        
        finally:
            # No longer cleaning up the directory since we want it to persist
            if extract_dir and os.path.exists(extract_dir):
                print(f"📁 Artifacts remain available for inspection at: {extract_dir}")
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis results."""
        recommendations = []
        
        job_details = analysis.get('job_details', {})
        
        # Check training status
        if job_details.get('status') == 'Failed':
            recommendations.append("Training job failed. Check CloudWatch logs for error details.")
        
        # Check training duration
        duration = job_details.get('training_duration_minutes', 0)
        if duration > 1440:  # 24 hours
            recommendations.append("Training took longer than 24 hours. Consider optimizing hyperparameters or using more instances.")
        
        # Note: Artifact validation recommendations removed as artifacts section is excluded from report
        
        return recommendations
    
    def compare_training_jobs(self, job_names: List[str]) -> Dict[str, Any]:
        """Compare multiple training jobs."""
        print(f"🔄 Comparing {len(job_names)} training jobs...")
        
        comparison = {
            'jobs': [],
            'comparison_timestamp': datetime.now().isoformat(),
            'summary': {}
        }
        
        for job_name in job_names:
            try:
                analysis = self.analyze_training_job(job_name)
                comparison['jobs'].append(analysis)
            except Exception as e:
                print(f"❌ Failed to analyze job {job_name}: {e}")
        
        # Generate comparison summary
        if comparison['jobs']:
            successful_jobs = [job for job in comparison['jobs'] if job['job_details'].get('status') == 'Completed']
            failed_jobs = [job for job in comparison['jobs'] if job['job_details'].get('status') == 'Failed']
            
            comparison['summary'] = {
                'total_jobs': len(comparison['jobs']),
                'successful_jobs': len(successful_jobs),
                'failed_jobs': len(failed_jobs),
                'success_rate': len(successful_jobs) / len(comparison['jobs']) * 100 if comparison['jobs'] else 0
            }
            
            if successful_jobs:
                durations = [job['job_details'].get('training_duration_minutes', 0) for job in successful_jobs]
                comparison['summary']['avg_training_duration_minutes'] = sum(durations) / len(durations)
                comparison['summary']['fastest_job'] = min(successful_jobs, key=lambda x: x['job_details'].get('training_duration_minutes', float('inf')))['job_name']
                comparison['summary']['slowest_job'] = max(successful_jobs, key=lambda x: x['job_details'].get('training_duration_minutes', 0))['job_name']
        
        return comparison
    
    def export_analysis_report(self, analysis: Dict[str, Any], output_file: str):
        """Export analysis results to a file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            print(f"📄 Analysis report exported to: {output_file}")
        except Exception as e:
            print(f"❌ Failed to export report: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Analyze Nova model training artifacts",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--job-name",
        required=True,
        help="SageMaker training job name to analyze"
    )
    
    parser.add_argument(
        "--analysis-type",
        choices=['basic', 'metrics', 'artifacts', 'all'],
        default='all',
        help="Type of analysis to perform"
    )
    
    parser.add_argument(
        "--compare-jobs",
        nargs='+',
        help="List of job names to compare"
    )
    
    parser.add_argument(
        "--output-file",
        help="Output file for analysis report (JSON format)"
    )
    
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region"
    )
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = NovaModelAnalyzer(region=args.region)
    
    try:
        if args.compare_jobs:
            # Compare multiple jobs
            comparison = analyzer.compare_training_jobs(args.compare_jobs)
            
            if args.output_file:
                analyzer.export_analysis_report(comparison, args.output_file)
            else:
                print(json.dumps(comparison, indent=2, default=str))
        else:
            # Analyze single job
            analysis = analyzer.analyze_training_job(args.job_name)
            
            if args.output_file:
                analyzer.export_analysis_report(analysis, args.output_file)
            else:
                print(json.dumps(analysis, indent=2, default=str))
                
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
