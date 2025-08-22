#!/usr/bin/env python3
"""
Model Output Evaluation Script
Compares model outputs from result files with ground truth answers.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd


def load_answer_files(answers_dir: str = "answers") -> pd.DataFrame:
    """
    Load all answer files from the answers directory and return as pandas DataFrame.
    
    Args:
        answers_dir: Directory containing answer files
        
    Returns:
        pandas DataFrame with columns 'Id' and 'ground_truth'
    """
    answers_list = []
    answers_path = Path(answers_dir)
    
    if not answers_path.exists():
        print(f"Warning: Answers directory {answers_dir} not found")
        return pd.DataFrame(columns=['Id', 'ground_truth'])
    
    for file_path in answers_path.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        answer_data = json.loads(line)
                        record_id = answer_data.get('id')
                        if record_id:
                            answers_list.append({
                                'Id': record_id,
                                'ground_truth': answer_data.get('ground_truth', [])
                            })
        except Exception as e:
            print(f"Error loading answer file {file_path}: {e}")
    
    return pd.DataFrame(answers_list)


def _is_refusal_response(text: str) -> bool:
    """
    Check if the text contains a refusal response indicating the model cannot answer.
    
    Args:
        text: The text to check
        
    Returns:
        True if the text contains a refusal response, False otherwise
    """
    import re
    
    # Patterns to match various forms of refusal responses
    refusal_patterns = [
        r"cannot\s+answer",           # "cannot answer"
        r"can't\s+answer",            # "can't answer"
        r"unable\s+to\s+answer",      # "unable to answer"
        r"I\s+don't\s+know",          # "I don't know"
        r"I\s+cannot\s+help",         # "I cannot help"
        r"I\s+can't\s+help",          # "I can't help"
    ]
    
    # Check each pattern (case insensitive)
    for pattern in refusal_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False


def extract_function_calls_from_tool_config(record: Dict[str, Any], record_id: str = None, filename: str = None) -> List[Dict[str, Any]]:
    """
    Extract function calls from tool config result files.
    
    Args:
        record: Single record from a tool config result file
        record_id: Record ID for error logging (optional)
        filename: Filename for error logging (optional)
        
    Returns:
        List of function calls with name and parameters
    """
    function_calls = []
    
    try:
        content = record.get("modelOutput", {}).get("output", {}).get("message", {}).get("content", [])
        
        # Check if any content contains a refusal response - treat as empty list
        for item in content:
            if "text" in item and _is_refusal_response(item["text"]):
                return []
        
        for item in content:
            if "toolUse" in item:
                tool_use = item["toolUse"]
                function_call = {
                    "name": tool_use.get("name"),
                    "parameters": tool_use.get("input", {})
                }
                function_calls.append(function_call)
    except Exception as e:
        _log_processing_error(record_id, f"Error extracting from tool config record: {e}", filename)
    
    return function_calls


def extract_function_calls_from_regular(record: Dict[str, Any], record_id: str = None, filename: str = None) -> List[Dict[str, Any]]:
    """
    Extract function calls from regular (prompt-only) result files.
    
    Args:
        record: Single record from a regular result file
        record_id: Record ID for error logging (optional)
        filename: Filename for error logging (optional)
        
    Returns:
        List of function calls with name and parameters
    """
    function_calls = []
    
    try:
        content = record.get("modelOutput", {}).get("output", {}).get("message", {}).get("content", [])
        
        for item in content:
            if "text" in item:
                text = item["text"]
                
                # Check if text contains a refusal response - treat as empty list
                if _is_refusal_response(text):
                    return []
                
                # Try to extract JSON from text (may be wrapped in markdown code blocks)
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to find plain JSON
                    json_match = re.search(r'(\{[^{}]*"name"[^{}]*"parameters"[^{}]*\})', text)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # Fallback: assume entire text is JSON
                        json_str = text.strip()
                
                try:
                    function_data = json.loads(json_str)
                    if "name" in function_data and "parameters" in function_data:
                        function_call = {
                            "name": function_data["name"],
                            "parameters": function_data["parameters"]
                        }
                        function_calls.append(function_call)
                except json.JSONDecodeError:
                    # Don't log error for refusal responses - they're intentional
                    if not _is_refusal_response(text):
                        _log_parsing_error(record_id, text, filename)
                    
    except Exception as e:
        _log_processing_error(record_id, f"Error extracting from regular record: {e}", filename)
    
    return function_calls


def _log_parsing_error(record_id: str, text: str, filename: str = None, log_file: str = "logs/parsing_errors.log"):
    """
    Log JSON parsing errors to a file instead of printing to console.
    
    Args:
        record_id: The record ID where the error occurred
        text: The text that failed to parse
        filename: The filename where the error occurred
        log_file: Path to the log file
    """
    import os
    from datetime import datetime
    
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    timestamp = datetime.now().isoformat()
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] PARSING_ERROR - File: {filename or 'unknown'} - Record ID: {record_id or 'unknown'}\n")
        f.write(f"Failed to parse JSON from text: {text[:200]}...\n")
        f.write("-" * 80 + "\n")


def _log_processing_error(record_id: str, error_message: str, filename: str = None, log_file: str = "logs/processing_errors.log"):
    """
    Log processing errors to a file instead of printing to console.
    
    Args:
        record_id: The record ID where the error occurred
        error_message: The error message
        filename: The filename where the error occurred
        log_file: Path to the log file
    """
    import os
    from datetime import datetime
    
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    timestamp = datetime.now().isoformat()
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] PROCESSING_ERROR - File: {filename or 'unknown'} - Record ID: {record_id or 'unknown'}\n")
        f.write(f"{error_message}\n")
        f.write("-" * 80 + "\n")


def _log_mismatch(record_id: str, extracted_calls: List[Dict[str, Any]], ground_truth: List[Dict[str, Any]],
                  mismatch_reason: str, filename: str = None, log_file: str = "logs/mismatches.log"):
    """
    Log function call mismatches to a file for detailed analysis.
    
    Args:
        record_id: The record ID where the mismatch occurred
        extracted_calls: The function calls extracted from model output
        ground_truth: The expected ground truth function calls
        mismatch_reason: Reason for the mismatch
        filename: The filename where the mismatch occurred
        log_file: Path to the log file
    """
    import os
    from datetime import datetime
    
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    timestamp = datetime.now().isoformat()
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] MISMATCH - File: {filename or 'unknown'} - Record ID: {record_id or 'unknown'}\n")
        f.write(f"Reason: {mismatch_reason}\n")
        f.write(f"Model Output: {json.dumps(extracted_calls, indent=2) if extracted_calls else 'No function calls extracted'}\n")
        f.write(f"Expected Answer: {json.dumps(ground_truth, indent=2) if ground_truth else 'No expected function calls'}\n")
        f.write("-" * 80 + "\n")


def _sanitize_tool_name(name: str) -> str:
    """
    Sanitize tool names to comply with Bedrock converse API naming rules.
    Pattern: [a-zA-Z0-9_-]+
    
    Args:
        name: Original tool name
        
    Returns:
        Sanitized tool name compliant with Bedrock naming rules
    """
    import re
    
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    
    # Ensure it doesn't start with a number or special character
    if sanitized and not sanitized[0].isalpha():
        sanitized = 'tool_' + sanitized
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = 'unnamed_tool'
    
    return sanitized


def evaluate_live_relevance(record_id: str, extracted_calls: List[Dict[str, Any]],
                          question_data: Dict[str, Any], ground_truth: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Evaluate live_relevance records: Model should contain at least 1 function call whose name is in the tool list from the question.
    
    Args:
        record_id: The record identifier
        extracted_calls: Function calls extracted from model output
        question_data: Question data containing available tools
        ground_truth: Ground truth function calls (not used for this evaluation type)
        
    Returns:
        Tuple of (is_match, details_message)
    """
    if not extracted_calls:
        return False, "No function calls extracted"
    
    # Get available tool names from question data
    available_tools = set()
    if "function" in question_data:
        for func in question_data["function"]:
            tool_name = func.get("name", "")
            available_tools.add(tool_name)
            # Also add sanitized version for comparison
            available_tools.add(_sanitize_tool_name(tool_name))
    
    if not available_tools:
        return False, "No available tools found in question data"
    
    # Check if any extracted call matches available tools
    for call in extracted_calls:
        extracted_name = call.get("name", "")
        sanitized_name = _sanitize_tool_name(extracted_name)
        
        if extracted_name in available_tools or sanitized_name in available_tools:
            return True, f"Found matching tool call: {extracted_name}"
    
    return False, f"No extracted calls match available tools. Extracted: {[call.get('name', '') for call in extracted_calls]}, Available: {list(available_tools)}"


def evaluate_irrelevance(record_id: str, extracted_calls: List[Dict[str, Any]],
                        question_data: Dict[str, Any], ground_truth: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Evaluate irrelevance records: Model should return an empty list (no function calls).
    
    Args:
        record_id: The record identifier
        extracted_calls: Function calls extracted from model output
        question_data: Question data (not used for this evaluation type)
        ground_truth: Ground truth function calls (not used for this evaluation type)
        
    Returns:
        Tuple of (is_match, details_message)
    """
    if not extracted_calls:
        return True, "Correctly returned no function calls for irrelevant query"
    
    return False, f"Should have returned no function calls, but got {len(extracted_calls)} calls: {[call.get('name', '') for call in extracted_calls]}"


def evaluate_simple(record_id: str, extracted_calls: List[Dict[str, Any]],
                   question_data: Dict[str, Any], ground_truth: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Evaluate simple records: Model should return 1 and only 1 tool that matches the tool in question/answer.
    
    Args:
        record_id: The record identifier
        extracted_calls: Function calls extracted from model output
        question_data: Question data containing available tools
        ground_truth: Ground truth function calls
        
    Returns:
        Tuple of (is_match, details_message)
    """
    if len(extracted_calls) != 1:
        return False, f"Expected exactly 1 function call, got {len(extracted_calls)}"
    
    if not ground_truth:
        return False, "No ground truth data provided"
    
    extracted = extracted_calls[0]
    gt = ground_truth[0]
    
    # Get function name and parameters from ground truth
    gt_func_name = list(gt.keys())[0]
    gt_params = gt[gt_func_name]
    
    extracted_name = extracted.get("name", "")
    extracted_params = extracted.get("parameters", {})
    
    # Sanitize names for comparison
    sanitized_extracted = _sanitize_tool_name(extracted_name)
    sanitized_gt = _sanitize_tool_name(gt_func_name)
    
    # Check function name match (original or sanitized)
    if extracted_name != gt_func_name and sanitized_extracted != sanitized_gt:
        return False, f"Function name mismatch: '{extracted_name}' (sanitized: '{sanitized_extracted}') vs '{gt_func_name}' (sanitized: '{sanitized_gt}')"
    
    # Check parameters
    for param_name, expected_values in gt_params.items():
        if param_name not in extracted_params:
            # Check if it's an optional parameter (empty string or None in expected values)
            if "" in expected_values or None in expected_values:
                continue
            return False, f"Missing parameter: {param_name}"
        
        extracted_value = extracted_params[param_name]
        
        # Check if extracted value matches any of the expected values
        if extracted_value not in expected_values:
            # Special handling for default/optional values
            if ("" in expected_values or None in expected_values) and extracted_value in ["", None]:
                continue
            return False, f"Parameter '{param_name}' value mismatch: {extracted_value} not in {expected_values}"
    
    return True, "Perfect match"


def evaluate_multiple(record_id: str, extracted_calls: List[Dict[str, Any]],
                     question_data: Dict[str, Any], ground_truth: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Evaluate multiple records: Model should return the same tool and parameter values as the answer.
    
    Args:
        record_id: The record identifier
        extracted_calls: Function calls extracted from model output
        question_data: Question data containing available tools
        ground_truth: Ground truth function calls
        
    Returns:
        Tuple of (is_match, details_message)
    """
    if not extracted_calls and not ground_truth:
        return True, "Both empty - match"
    
    if len(extracted_calls) != len(ground_truth):
        return False, f"Different number of calls: extracted={len(extracted_calls)}, ground_truth={len(ground_truth)}"
    
    if not extracted_calls:
        return False, "No function calls extracted"
    
    if not ground_truth:
        return False, "No ground truth calls"
    
    # Check each ground truth call against extracted calls
    for i, gt in enumerate(ground_truth):
        if i >= len(extracted_calls):
            return False, f"Missing extracted call for ground truth item {i}"
        
        extracted = extracted_calls[i]
        
        # Get function name and parameters from ground truth
        gt_func_name = list(gt.keys())[0]
        gt_params = gt[gt_func_name]
        
        extracted_name = extracted.get("name", "")
        extracted_params = extracted.get("parameters", {})
        
        # Sanitize names for comparison
        sanitized_extracted = _sanitize_tool_name(extracted_name)
        sanitized_gt = _sanitize_tool_name(gt_func_name)
        
        # Check function name match (original or sanitized)
        if extracted_name != gt_func_name and sanitized_extracted != sanitized_gt:
            return False, f"Function name mismatch at position {i}: '{extracted_name}' (sanitized: '{sanitized_extracted}') vs '{gt_func_name}' (sanitized: '{sanitized_gt}')"
        
        # Check parameters
        for param_name, expected_values in gt_params.items():
            if param_name not in extracted_params:
                # Check if it's an optional parameter (empty string or None in expected values)
                if "" in expected_values or None in expected_values:
                    continue
                return False, f"Missing parameter '{param_name}' at position {i}"
            
            extracted_value = extracted_params[param_name]
            
            # Check if extracted value matches any of the expected values
            if extracted_value not in expected_values:
                # Special handling for default/optional values
                if ("" in expected_values or None in expected_values) and extracted_value in ["", None]:
                    continue
                return False, f"Parameter '{param_name}' value mismatch at position {i}: {extracted_value} not in {expected_values}"
    
    return True, "All calls match perfectly"


def compare_with_ground_truth(record_id: str, extracted_calls: List[Dict[str, Any]],
                            question_data: Dict[str, Any], ground_truth: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Compare extracted function calls with ground truth based on record ID prefix.
    
    Args:
        record_id: The record identifier
        extracted_calls: Function calls extracted from model output
        question_data: Question data containing available tools
        ground_truth: Ground truth function calls
        
    Returns:
        Tuple of (is_match, details_message)
    """
    # Determine evaluation type based on record ID prefix
    if record_id.startswith('live_relevance'):
        return evaluate_live_relevance(record_id, extracted_calls, question_data, ground_truth)
    elif record_id.startswith('irrelevance'):
        return evaluate_irrelevance(record_id, extracted_calls, question_data, ground_truth)
    elif record_id.startswith('simple'):
        return evaluate_simple(record_id, extracted_calls, question_data, ground_truth)
    elif record_id.startswith('multiple'):
        return evaluate_multiple(record_id, extracted_calls, question_data, ground_truth)
    else:
        # Fallback to simple evaluation for unknown prefixes
        return evaluate_simple(record_id, extracted_calls, question_data, ground_truth)


def assess_model_output_by_record_id(record_id: str, record: Dict[str, Any], 
                                   ground_truth: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess model output for a specific record ID.
    This is a stub function for detailed analysis.
    
    Args:
        record_id: The record identifier
        record: The model output record
        ground_truth: The ground truth data
        
    Returns:
        Dictionary containing assessment details
    """
    # Stub implementation - can be expanded for detailed analysis
    assessment = {
        "record_id": record_id,
        "has_model_output": bool(record.get("modelOutput")),
        "has_ground_truth": bool(ground_truth.get("ground_truth")),
        "assessment_type": "basic_stub",
        "details": "This is a placeholder for detailed model output assessment"
    }
    
    return assessment


def load_question_data(questions_file: str = "eval/questions.json") -> Dict[str, Dict[str, Any]]:
    """
    Load question data from the questions file.
    
    Args:
        questions_file: Path to the questions JSON file
        
    Returns:
        Dictionary mapping question IDs to question data
    """
    questions = {}
    questions_path = Path(questions_file)
    
    if not questions_path.exists():
        print(f"Warning: Questions file {questions_file} not found")
        return questions
    
    try:
        with open(questions_path, 'r', encoding='utf-8') as f:
            questions_list = json.load(f)
            for question in questions_list:
                question_id = question.get('id')
                if question_id:
                    questions[question_id] = question
    except Exception as e:
        print(f"Error loading questions file {questions_file}: {e}")
    
    return questions


def _get_question_category(record_id: str) -> str:
    """
    Determine the question category from the record ID.
    
    Args:
        record_id: The record identifier
        
    Returns:
        The question category (live_relevance, irrelevance, simple, multiple, unknown)
    """
    if record_id.startswith('live_relevance'):
        return 'live_relevance'
    elif record_id.startswith('irrelevance'):
        return 'irrelevance'
    elif record_id.startswith('simple'):
        return 'simple'
    elif record_id.startswith('multiple'):
        return 'multiple'
    else:
        return 'unknown'


def process_result_file(file_path: Path, answers_df: pd.DataFrame,
                       questions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process a single result file and compare with ground truth using pandas joins.
    
    Args:
        file_path: Path to the result file
        answers_df: DataFrame with ground truth answers (columns: 'Id', 'ground_truth')
        questions: Dictionary of question data
        
    Returns:
        Dictionary containing evaluation results
    """
    results = {
        "file": str(file_path),
        "total_records": 0,
        "matches": 0,
        "mismatches": 0,
        "missing_ground_truth": 0,
        "extraction_errors": 0,
        "details": [],
        "categories": {
            "live_relevance": {"matches": 0, "mismatches": 0, "errors": 0},
            "irrelevance": {"matches": 0, "mismatches": 0, "errors": 0},
            "simple": {"matches": 0, "mismatches": 0, "errors": 0},
            "multiple": {"matches": 0, "mismatches": 0, "errors": 0},
            "unknown": {"matches": 0, "mismatches": 0, "errors": 0}
        }
    }
    
    is_tool_config = "tool_config" in file_path.name
    
    try:
        # Read all records from the file into a list
        records_list = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    record = json.loads(line)
                    record_id = record.get("recordId")
                    if record_id:
                        records_list.append({
                            'recordId': record_id,
                            'record_data': record
                        })
                    else:
                        results["extraction_errors"] += 1
                        results["details"].append({
                            "record_id": "unknown",
                            "status": "error",
                            "message": "No recordId found"
                        })
                except json.JSONDecodeError as e:
                    # JSON decode errors should be treated as mismatches, not errors
                    # This represents a model failure to produce valid output format
                    results["mismatches"] += 1
                    results["details"].append({
                        "record_id": "unknown",
                        "status": "mismatch",
                        "message": f"JSON decode error - model failed to produce valid JSON: {e}"
                    })
        
        if not records_list:
            return results
        
        # Create DataFrame from records
        records_df = pd.DataFrame(records_list)
        results["total_records"] = len(records_df)
        
        # Join with answers DataFrame using pandas merge
        joined_df = records_df.merge(
            answers_df,
            left_on='recordId',
            right_on='Id',
            how='left',
            indicator=True
        )
        
        # Process each joined record
        for idx, row in joined_df.iterrows():
            record_id = row['recordId']
            record = row['record_data']
            
            try:
                # Get question category
                category = _get_question_category(record_id)
                
                # Check if ground truth was found
                if row['_merge'] == 'left_only':
                    results["missing_ground_truth"] += 1
                    results["categories"][category]["errors"] += 1
                    results["details"].append({
                        "record_id": record_id,
                        "status": "error",
                        "message": "No ground truth found"
                    })
                    continue
                
                # Extract function calls based on file type
                if is_tool_config:
                    extracted_calls = extract_function_calls_from_tool_config(record, record_id, str(file_path.name))
                else:
                    extracted_calls = extract_function_calls_from_regular(record, record_id, str(file_path.name))
                
                # Handle cases where no function calls are extracted
                # Note: For irrelevance tests, having no function calls is the correct behavior
                ground_truth_data = row['ground_truth']
                
                # Get question data for this record
                question_data = questions.get(record_id, {})
                
                # Compare with ground truth - let the evaluation logic determine if empty calls are correct
                is_match, message = compare_with_ground_truth(record_id, extracted_calls, question_data, ground_truth_data)
                
                if is_match:
                    results["matches"] += 1
                    results["categories"][category]["matches"] += 1
                    status = "match"
                else:
                    results["mismatches"] += 1
                    results["categories"][category]["mismatches"] += 1
                    status = "mismatch"
                    # Log mismatch details to file
                    _log_mismatch(record_id, extracted_calls, ground_truth_data, message, str(file_path.name))
                
                results["details"].append({
                    "record_id": record_id,
                    "status": status,
                    "message": message,
                    "extracted": extracted_calls,
                    "ground_truth": ground_truth_data
                })
                
            except Exception as e:
                results["extraction_errors"] += 1
                category = _get_question_category(record_id)
                results["categories"][category]["errors"] += 1
                results["details"].append({
                    "record_id": record_id,
                    "status": "error",
                    "message": f"Processing error: {e}"
                })
    
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        results["file_error"] = str(e)
    
    return results


def _parse_filename_info(filename: str) -> Tuple[str, str, str]:
    """
    Parse filename to extract model information and prompting approach.
    
    Args:
        filename: Result filename (e.g., "results_prompt_only_base_nova_micro.jsonl")
        
    Returns:
        Tuple of (prompting_approach, model_type, model_name)
    """
    # Remove extension and "results_" prefix
    name_parts = filename.replace('.jsonl', '').replace('results_', '').split('_')
    
    # Extract prompting approach
    if 'prompt_only' in filename:
        prompting_approach = 'prompt_only'
    elif 'tool_config' in filename:
        prompting_approach = 'tool_config'
    else:
        prompting_approach = 'unknown'
    
    # Extract model type (fine-tuned vs base)
    if 'ft' in name_parts:
        model_type = 'fine-tuned'
    else:
        model_type = 'base'
    
    # Extract model name (nova_micro, nova_lite, etc.)
    model_name = 'unknown'
    for i, part in enumerate(name_parts):
        if part == 'nova' and i + 1 < len(name_parts):
            model_name = f"nova_{name_parts[i + 1]}"
            break
    
    return prompting_approach, model_type, model_name


def export_results_to_csv(all_results: List[Dict[str, Any]], filename: str = "evaluation_results.csv"):
    """
    Export evaluation results to CSV format with files as rows and categories as columns.
    
    Args:
        all_results: List of result dictionaries from process_result_file
        filename: Output CSV filename
    """
    csv_data = []
    
    for file_result in all_results:
        # Extract filename without path
        file_name = Path(file_result["file"]).name
        
        # Parse filename for model and approach information
        prompting_approach, model_type, model_name = _parse_filename_info(file_name)
        
        row_data = {
            "file": file_name,
            "prompting_approach": prompting_approach,
            "model_type": model_type,
            "model_name": model_name,
            "total_records": file_result["total_records"],
            "total_matches": file_result["matches"],
            "total_mismatches": file_result["mismatches"],
            "total_errors": file_result["extraction_errors"] + file_result["missing_ground_truth"],
            "overall_accuracy": round((file_result["matches"] / file_result["total_records"]) * 100, 2) if file_result["total_records"] > 0 else 0
        }
        
        # Add category-specific data
        categories = file_result.get("categories", {})
        for category in ["live_relevance", "irrelevance", "simple", "multiple", "unknown"]:
            if category in categories:
                stats = categories[category]
                total_cat = stats["matches"] + stats["mismatches"] + stats["errors"]
                accuracy = round((stats["matches"] / total_cat) * 100, 1) if total_cat > 0 else 0
                
                row_data[f"{category}_matches"] = stats["matches"]
                row_data[f"{category}_total"] = total_cat
                row_data[f"{category}_accuracy"] = accuracy
            else:
                row_data[f"{category}_matches"] = 0
                row_data[f"{category}_total"] = 0
                row_data[f"{category}_accuracy"] = 0
        
        csv_data.append(row_data)
    
    # Create DataFrame and export to CSV
    df = pd.DataFrame(csv_data)
    df.to_csv(filename, index=False)
    print(f"Results exported to: {filename}")


def main():
    """
    Main function to run the evaluation.
    """
    print("Model Output Evaluation Script")
    print("=" * 50)
    
    # Load answer files as DataFrame
    print("Loading answer files...")
    answers_df = load_answer_files()
    print(f"Loaded {len(answers_df)} ground truth records")
    
    if answers_df.empty:
        print("No ground truth data found. Exiting.")
        return
    
    # Load question data
    print("Loading question data...")
    questions = load_question_data()
    print(f"Loaded {len(questions)} question records")
    
    # Process result files
    results_dir = Path("eval/results")
    if not results_dir.exists():
        print(f"Results directory {results_dir} not found. Exiting.")
        return
    
    all_results = []
    total_records = 0
    total_matches = 0
    total_mismatches = 0
    total_errors = 0
    
    print(f"\nProcessing result files from {results_dir}...")
    for file_path in results_dir.glob("*.jsonl"):
        print(f"\nProcessing {file_path.name}...")
        file_results = process_result_file(file_path, answers_df, questions)
        all_results.append(file_results)
        
        # Update totals
        total_records += file_results["total_records"]
        total_matches += file_results["matches"]
        total_mismatches += file_results["mismatches"]
        total_errors += file_results["extraction_errors"] + file_results["missing_ground_truth"]
        
        # Print file summary
        print(f"  Records: {file_results['total_records']}")
        print(f"  Matches: {file_results['matches']}")
        print(f"  Mismatches: {file_results['mismatches']}")
        print(f"  Errors: {file_results['extraction_errors'] + file_results['missing_ground_truth']}")
        
        # Show accuracy if applicable
        if file_results["total_records"] > 0:
            accuracy = (file_results["matches"] / file_results["total_records"]) * 100
            print(f"  Accuracy: {accuracy:.2f}%")
        
        # Show category breakdown
        categories = file_results.get("categories", {})
        if categories:
            print(f"  Category Breakdown:")
            for category, stats in categories.items():
                total_cat = stats["matches"] + stats["mismatches"] + stats["errors"]
                if total_cat > 0:
                    cat_accuracy = (stats["matches"] / total_cat) * 100 if total_cat > 0 else 0
                    print(f"    {category}: {stats['matches']}/{total_cat} ({cat_accuracy:.1f}%) - Matches: {stats['matches']}, Mismatches: {stats['mismatches']}, Errors: {stats['errors']}")
    
    # Export results to CSV
    print(f"\nExporting results to CSV...")
    export_results_to_csv(all_results)
    
    # Print summary
    print(f"\nProcessed {len(all_results)} files with {total_records} total records.")
    if total_records > 0:
        overall_accuracy = (total_matches / total_records) * 100
        print(f"Overall accuracy: {overall_accuracy:.2f}%")


if __name__ == "__main__":
    main()