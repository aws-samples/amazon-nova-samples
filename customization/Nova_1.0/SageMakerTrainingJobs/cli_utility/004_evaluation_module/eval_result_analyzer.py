#!/usr/bin/env python3
"""
Evaluation Result Analyzer

This module provides the EvalResultAnalyzer class for analyzing evaluation results
after job completion, including downloading and extracting outputs, getting metrics,
and visualizing results.
"""

import os
import json
import time
import tarfile
import shutil
import tempfile
import subprocess
import http.server
import socketserver
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
from pathlib import Path
import boto3
import sagemaker

# Import pandas and pyarrow for parquet handling
try:
    import pandas as pd
    import pyarrow
    import pyarrow.parquet as pq
    HAS_PARQUET_SUPPORT = True
except ImportError:
    HAS_PARQUET_SUPPORT = False


class EvalResultAnalyzer:
    """Class for analyzing evaluation results after job completion."""
    
    def __init__(
        self,
        sagemaker_session: Optional[sagemaker.Session] = None,
        output_dir: Optional[str] = None
    ):
        """Initialize evaluation result analyzer.
        
        Args:
            sagemaker_session: SageMaker session
            output_dir: Directory to store extracted results
        """
        self.sagemaker_session = sagemaker_session or sagemaker.Session()
        
        # Use a directory within the module instead of an outside folder
        if output_dir:
            self.output_dir = output_dir
        else:
            # Get the directory of the current module
            module_dir = os.path.dirname(os.path.abspath(__file__))
            self.output_dir = os.path.join(module_dir, "eval_results")
        
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_job_output_uri(self, job_name: str) -> str:
        """Get the output S3 URI for a completed training job.
        
        Args:
            job_name: Name of the training job
            
        Returns:
            S3 URI for the job output
        """
        try:
            # Get the training job description
            sm_client = self.sagemaker_session.boto_session.client('sagemaker')
            job_desc = sm_client.describe_training_job(TrainingJobName=job_name)
            
            # Get the output S3 URI
            output_uri = job_desc['OutputDataConfig']['S3OutputPath']
            
            return output_uri
        except Exception as e:
            raise ValueError(f"Error getting output URI for job {job_name}: {e}")
    
    def download_and_extract_output(self, job_name: str, output_uri: Optional[str] = None) -> str:
        """Download and extract the output.tar.gz file for a completed training job.
        
        Args:
            job_name: Name of the training job
            output_uri: S3 URI for the job output (optional, will be retrieved if not provided)
            
        Returns:
            Path to the extracted output directory
        """
        try:
            # Get the output URI if not provided
            if not output_uri:
                output_uri = self.get_job_output_uri(job_name)
            
            # Construct the path to the output.tar.gz file
            output_tar_uri = f"{output_uri}/{job_name}/output/output.tar.gz"
            
            # Create a temporary directory for downloading
            temp_dir = tempfile.mkdtemp()
            temp_tar_path = os.path.join(temp_dir, "output.tar.gz")
            
            print(f"Downloading output from {output_tar_uri}...")
            
            # Parse the S3 URI
            parsed_uri = urlparse(output_tar_uri)
            bucket = parsed_uri.netloc
            key = parsed_uri.path.lstrip('/')
            
            # Download the file
            s3_client = self.sagemaker_session.boto_session.client('s3')
            s3_client.download_file(bucket, key, temp_tar_path)
            
            # Create extraction directory
            extract_dir = os.path.join(self.output_dir, job_name)
            os.makedirs(extract_dir, exist_ok=True)
            
            print(f"Extracting output to {extract_dir}...")
            
            # Extract the tar file
            with tarfile.open(temp_tar_path, "r:gz") as tar:
                tar.extractall(path=extract_dir)
            
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
            
            print(f"✅ Output extracted successfully to {extract_dir}")
            
            # List the top-level directories to help with debugging
            print("Extracted directory structure:")
            for item in os.listdir(extract_dir):
                item_path = os.path.join(extract_dir, item)
                if os.path.isdir(item_path):
                    print(f"  - {item}/ (directory)")
                    # List first level of subdirectories
                    for subitem in os.listdir(item_path):
                        subitem_path = os.path.join(item_path, subitem)
                        if os.path.isdir(subitem_path):
                            print(f"    - {subitem}/ (directory)")
                        else:
                            print(f"    - {subitem} (file)")
                else:
                    print(f"  - {item} (file)")
            
            return extract_dir
        except Exception as e:
            raise ValueError(f"Error downloading and extracting output for job {job_name}: {e}")
    
    def get_metrics(self, job_name: str, extract_dir: Optional[str] = None) -> Dict[str, Any]:
        """Get evaluation metrics from the extracted output.
        
        Args:
            job_name: Name of the training job
            extract_dir: Path to the extracted output directory (optional)
            
        Returns:
            Dictionary containing evaluation metrics
        """
        try:
            # Get the extract directory if not provided
            if not extract_dir:
                extract_dir = os.path.join(self.output_dir, job_name)
                if not os.path.exists(extract_dir):
                    extract_dir = self.download_and_extract_output(job_name)
            
            # Look for metrics files in the eval_results directory
            eval_results_dir = os.path.join(extract_dir, job_name, "eval_results")
            
            if not os.path.exists(eval_results_dir):
                raise ValueError(f"Eval results directory not found: {eval_results_dir}")
            
            # Check for nested job directory structure
            nested_job_dir = os.path.join(eval_results_dir, job_name)
            if os.path.exists(nested_job_dir):
                # Look for metrics.json file in nested directory
                nested_metrics_file = os.path.join(nested_job_dir, "metrics.json")
                if os.path.exists(nested_metrics_file):
                    with open(nested_metrics_file, 'r') as f:
                        metrics = json.load(f)
                    return metrics
                
                # Look for other JSON files in nested directory
                nested_json_files = [f for f in os.listdir(nested_job_dir) if f.endswith('.json')]
                if nested_json_files:
                    metrics = {}
                    for json_file in nested_json_files:
                        with open(os.path.join(nested_job_dir, json_file), 'r') as f:
                            file_metrics = json.load(f)
                            metrics[json_file] = file_metrics
                    return metrics
            
            # Look for metrics.json file in standard directory
            metrics_file = os.path.join(eval_results_dir, "metrics.json")
            if os.path.exists(metrics_file):
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
                return metrics
            
            # If metrics.json doesn't exist, look for other JSON files
            json_files = [f for f in os.listdir(eval_results_dir) if f.endswith('.json')]
            if json_files:
                metrics = {}
                for json_file in json_files:
                    with open(os.path.join(eval_results_dir, json_file), 'r') as f:
                        file_metrics = json.load(f)
                        metrics[json_file] = file_metrics
                return metrics
            
            raise ValueError(f"No metrics files found in {eval_results_dir}")
        except Exception as e:
            raise ValueError(f"Error getting metrics for job {job_name}: {e}")
    
    def get_raw_inferences(self, job_name: str, extract_dir: Optional[str] = None) -> str:
        """Get raw inference results from the extracted output.
        
        Args:
            job_name: Name of the training job
            extract_dir: Path to the extracted output directory (optional)
            
        Returns:
            Path to the directory containing raw inferences
        """
        try:
            # Get the extract directory if not provided
            if not extract_dir:
                extract_dir = os.path.join(self.output_dir, job_name)
                if not os.path.exists(extract_dir):
                    extract_dir = self.download_and_extract_output(job_name)
            
            # Look for raw inferences in the eval_results directory
            eval_results_dir = os.path.join(extract_dir, job_name, "eval_results")
            
            if not os.path.exists(eval_results_dir):
                raise ValueError(f"Eval results directory not found: {eval_results_dir}")
            
            # Check for nested job directory structure
            nested_job_dir = os.path.join(eval_results_dir, job_name)
            if os.path.exists(nested_job_dir):
                # Check for JSONL files in nested directory
                jsonl_files = [f for f in os.listdir(nested_job_dir) if f.endswith('.jsonl')]
                if jsonl_files:
                    print(f"Found raw inference files in nested directory: {jsonl_files}")
                    return nested_job_dir
                
                # Look for parquet directories in nested directory
                for root, dirs, files in os.walk(nested_job_dir):
                    if any(f.endswith('.parquet') for f in files):
                        print(f"Found parquet files in nested directory: {root}")
                        return nested_job_dir
            
            # Look for JSONL files in standard directory
            jsonl_files = [f for f in os.listdir(eval_results_dir) if f.endswith('.jsonl')]
            if jsonl_files:
                print(f"Found raw inference files: {jsonl_files}")
                return eval_results_dir
            
            # Look for parquet directories in standard directory
            parquet_dirs = []
            for root, dirs, files in os.walk(eval_results_dir):
                if any(f.endswith('.parquet') for f in files):
                    parquet_dirs.append(root)
            
            if parquet_dirs:
                print(f"Found parquet directories: {parquet_dirs}")
                return eval_results_dir
            
            raise ValueError(f"No raw inference files found in {eval_results_dir}")
        except Exception as e:
            raise ValueError(f"Error getting raw inferences for job {job_name}: {e}")
    
    def get_tensorboard_logs(self, job_name: str, extract_dir: Optional[str] = None) -> str:
        """Get TensorBoard logs from the extracted output.
        
        Args:
            job_name: Name of the training job
            extract_dir: Path to the extracted output directory (optional)
            
        Returns:
            Path to the directory containing TensorBoard logs
        """
        try:
            # Get the extract directory if not provided
            if not extract_dir:
                extract_dir = os.path.join(self.output_dir, job_name)
                if not os.path.exists(extract_dir):
                    extract_dir = self.download_and_extract_output(job_name)
            
            print(f"Looking for TensorBoard logs in: {extract_dir}")
            
            # First, try a comprehensive search for TensorBoard logs
            for root, dirs, files in os.walk(extract_dir):
                if "tensorboard_results" in dirs:
                    tensorboard_dir = os.path.join(root, "tensorboard_results")
                    print(f"Found tensorboard_results directory at: {tensorboard_dir}")
                    return tensorboard_dir
                
                if any(f.startswith('events.out.tfevents') for f in files):
                    print(f"Found events.out.tfevents files at: {root}")
                    return root
            
            # If we didn't find anything with the comprehensive search, try specific paths
            
            # Look for TensorBoard logs in the eval_results directory
            eval_results_dir = os.path.join(extract_dir, job_name, "eval_results")
            print(f"Checking for eval_results directory at: {eval_results_dir}")
            
            if os.path.exists(eval_results_dir):
                # Look for tensorboard_results directory in eval_results
                tensorboard_dir = os.path.join(eval_results_dir, "tensorboard_results")
                if os.path.exists(tensorboard_dir):
                    print(f"Found tensorboard_results in eval_results: {tensorboard_dir}")
                    return tensorboard_dir
                
                # Check for nested job directory structure
                nested_job_dir = os.path.join(eval_results_dir, job_name)
                if os.path.exists(nested_job_dir):
                    nested_tensorboard_dir = os.path.join(nested_job_dir, "tensorboard_results")
                    if os.path.exists(nested_tensorboard_dir):
                        print(f"Found tensorboard_results in nested job dir: {nested_tensorboard_dir}")
                        return nested_tensorboard_dir
            
            # Try looking directly in the job directory
            direct_tensorboard_dir = os.path.join(extract_dir, "tensorboard_results")
            if os.path.exists(direct_tensorboard_dir):
                print(f"Found tensorboard_results directly in extract dir: {direct_tensorboard_dir}")
                return direct_tensorboard_dir
            
            # Try looking in the job_name directory
            job_dir_tensorboard = os.path.join(extract_dir, job_name, "tensorboard_results")
            if os.path.exists(job_dir_tensorboard):
                print(f"Found tensorboard_results in job dir: {job_dir_tensorboard}")
                return job_dir_tensorboard
            
            # List all directories to help with debugging
            print("Available directories:")
            for root, dirs, files in os.walk(extract_dir):
                print(f"  - {root}")
                for d in dirs:
                    print(f"    - {d}/")
                for f in files:
                    if f.startswith('events.out.tfevents'):
                        print(f"    - {f} (TensorBoard event file)")
            
            raise ValueError(f"No TensorBoard logs found in {extract_dir}")
        except Exception as e:
            raise ValueError(f"Error getting TensorBoard logs for job {job_name}: {e}")
    
    def visualize_tensorboard(self, tensorboard_dir: str, port: int = 6006) -> Tuple[subprocess.Popen, int]:
        """Launch TensorBoard to visualize logs.
        
        Args:
            tensorboard_dir: Path to the directory containing TensorBoard logs
            port: Port to use for TensorBoard server
            
        Returns:
            Tuple of (TensorBoard process, port)
        """
        try:
            # Check if TensorBoard is installed
            try:
                subprocess.run(["tensorboard", "--version"], check=True, capture_output=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                raise ValueError("TensorBoard is not installed. Please install it with 'pip install tensorboard'")
            
            # Launch TensorBoard
            print(f"Launching TensorBoard on port {port}...")
            tensorboard_process = subprocess.Popen(
                ["tensorboard", "--logdir", tensorboard_dir, "--port", str(port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait a moment for TensorBoard to start
            time.sleep(2)
            
            # Check if TensorBoard started successfully
            if tensorboard_process.poll() is not None:
                stderr = tensorboard_process.stderr.read().decode('utf-8')
                raise ValueError(f"Failed to start TensorBoard: {stderr}")
            
            print(f"✅ TensorBoard running at http://localhost:{port}")
            print("Press Ctrl+C to stop TensorBoard when finished")
            
            return tensorboard_process, port
        except Exception as e:
            raise ValueError(f"Error visualizing TensorBoard: {e}")
    
    def convert_parquet_to_jsonl(self, parquet_dir: str, output_file: Optional[str] = None) -> str:
        """Convert parquet files to JSONL format.
        
        Args:
            parquet_dir: Path to the directory containing parquet files
            output_file: Path to the output JSONL file (optional)
            
        Returns:
            Path to the output JSONL file
        """
        try:
            if not HAS_PARQUET_SUPPORT:
                raise ValueError("Parquet support is not available. Please install pandas and pyarrow with 'pip install pandas pyarrow'")
            
            # Find all parquet files in the directory (recursively)
            parquet_files = []
            for root, dirs, files in os.walk(parquet_dir):
                for file in files:
                    if file.endswith('.parquet'):
                        parquet_files.append(os.path.join(root, file))
            
            if not parquet_files:
                raise ValueError(f"No parquet files found in {parquet_dir}")
            
            print(f"Found {len(parquet_files)} parquet files")
            
            # Create output file path if not provided
            if not output_file:
                output_file = os.path.join(os.path.dirname(parquet_dir), "raw_inferences.jsonl")
            
            # Read all parquet files and convert to JSONL
            all_data = []
            for parquet_file in parquet_files:
                print(f"Reading {parquet_file}...")
                table = pq.read_table(parquet_file)
                df = table.to_pandas()
                
                # Convert DataFrame to list of dictionaries
                records = df.to_dict(orient='records')
                all_data.extend(records)
            
            # Write to JSONL file
            with open(output_file, 'w', encoding='utf-8') as f:
                for record in all_data:
                    # Convert any non-serializable objects to strings
                    serializable_record = {}
                    for key, value in record.items():
                        if isinstance(value, (str, int, float, bool, type(None))):
                            serializable_record[key] = value
                        else:
                            serializable_record[key] = str(value)
                    
                    f.write(json.dumps(serializable_record) + '\n')
            
            print(f"✅ Converted {len(all_data)} records to JSONL format")
            print(f"Output saved to: {output_file}")
            
            return output_file
        except Exception as e:
            raise ValueError(f"Error converting parquet to JSONL: {e}")
    
    def create_visual_failure_analysis(self, jsonl_file: str, output_dir: Optional[str] = None, port: int = 8000) -> Tuple[str, int]:
        """Create a visual failure analysis UI for analyzing JSONL inference results.
        
        Args:
            jsonl_file: Path to the JSONL file containing inference results
            output_dir: Directory to store the HTML UI files (optional)
            port: Port to use for the HTTP server
            
        Returns:
            Tuple of (HTML file path, server port)
        """
        try:
            # Import the visual_analysis module using direct import
            try:
                # Try direct import first
                from visual_analysis import create_visual_failure_analysis as create_visual_ui
            except ImportError:
                # If direct import fails, try to find the module in the current directory
                import sys
                import os
                current_dir = os.path.dirname(os.path.abspath(__file__))
                if current_dir not in sys.path:
                    sys.path.append(current_dir)
                
                # Try again with the updated path
                try:
                    from visual_analysis import create_visual_failure_analysis as create_visual_ui
                except ImportError:
                    # As a last resort, try with the full path
                    visual_analysis_path = os.path.join(current_dir, "visual_analysis.py")
                    if os.path.exists(visual_analysis_path):
                        import importlib.util
                        spec = importlib.util.spec_from_file_location("visual_analysis", visual_analysis_path)
                        visual_analysis = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(visual_analysis)
                        create_visual_ui = visual_analysis.create_visual_failure_analysis
                    else:
                        raise ImportError(f"Could not find visual_analysis.py in {current_dir}")
            
            # Use the imported function to create the visual failure analysis UI
            return create_visual_ui(jsonl_file, output_dir, port)
        except Exception as e:
            raise ValueError(f"Error creating visual failure analysis UI: {e}")
