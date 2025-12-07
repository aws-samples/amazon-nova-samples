import json
from typing import Dict, List, Any


def extract_json_from_markdown(text: str) -> str:
    """
    Extract JSON from markdown format with solution tags.

    Handles formats like:
    <|begin_of_solution|>```json
    {"key": "value"}
    ```<|end_of_solution|>

    Args:
        text: Raw text potentially containing solution tags and markdown

    Returns:
        Cleaned JSON string
    """
    if not isinstance(text, str):
        return text

    content = text

    # Remove solution tags if present
    if '<|begin_of_solution|>' in content:
        content = content.split('<|begin_of_solution|>')[-1]
    if '<|end_of_solution|>' in content:
        content = content.split('<|end_of_solution|>')[0]

    # Remove markdown code fences
    content = content.strip()

    # Handle ```json or ```
    if content.startswith('```json'):
        content = content[7:]  # Remove ```json
    elif content.startswith('```'):
        content = content[3:]  # Remove ```

    if content.endswith('```'):
        content = content[:-3]

    # Remove any escaped newlines that might be in the string
    content = content.replace('\\n', '\n')

    return content.strip()


def lambda_handler(event, context):
    """
    AWS Lambda handler function.

    Args:
        event: The Lambda event data
        context: The Lambda context

    Returns:
        List of dictionaries with reward scores
    """
    return lambda_grader(event)


def lambda_grader(samples: list[dict]) -> list[dict]:
    """
    Grade samples by comparing assistant responses against ground truth.

    Args:
        samples: List of dictionaries in OpenAI format

        Example input (List of such sample):
        {   
            "id": "123",
            "messages": [
                {
                    "role": "user",
                    "content": "What tools do I need for stock analysis?"
                },
                {
                    "role": "assistant",
                    "content": "{\"Type\": [\"information_retrieval\"], \"Tools\": [...]}"
                }
            ],            
            "reference_answer": {
                "Type": ["information_retrieval", "analysis"],
                "Information needed": "Stock data",
                "Tools": [
                    {
                        "Tool": "web_search",
                        "Parameters": {"query": "stock price"},
                        "Reasoning": "Get data"
                    }
                ]
            }
        }

    Returns:
        List of dictionaries with reward scores:
        {
            "id": str,
            "aggregate_reward_score": float,
            "metrics_list": [
                {
                    "name": str,
                    "value": float,
                    "type": str  # "Reward" or "Metric"
                }
            ]
        }
    """
    evaluator = QueryAnalysisEvaluator()
    results = []

    for sample in samples:

        sample_id = sample.get("id", "unknown")

        # Extract assistant's response from messages
        assistant_content = ""
        for message in sample.get("messages", []):
            if message.get("role") == "assistant":
                assistant_content = message.get("content", "")
                break

        # Parse assistant's JSON response
        try:
            # Handle solution tags and markdown code blocks
            content = assistant_content.strip()
            print(f"[DEBUG] Original content length: {len(content)}")
            print(f"[DEBUG] First 100 chars: {content[:100]}")

            # Extract JSON from markdown format with solution tags
            content = extract_json_from_markdown(content)
            print(f"[DEBUG] After extraction: {content[:200]}")

            predicted_output = json.loads(content)
            print(f"[DEBUG] Parsed JSON successfully")
            print(f"[DEBUG] Top-level keys: {list(predicted_output.keys())}")

            # Handle nested structure like {"Query analysis": {...}}
            if "Query analysis" in predicted_output:
                print(f"[DEBUG] Found 'Query analysis' key, extracting nested structure")
                predicted_output = predicted_output["Query analysis"]
                print(f"[DEBUG] Extracted keys: {list(predicted_output.keys())}")

            # Normalize predicted output: ensure Type is a list
            if "Type" in predicted_output and isinstance(predicted_output["Type"], str):
                predicted_output["Type"] = [predicted_output["Type"]]
                print(f"[DEBUG] Normalized predicted output Type from string to list")

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"[ERROR] Error parsing JSON for sample {sample_id}: {e}")
            print(f"[ERROR] Content: {assistant_content[:200]}")
            # If parsing fails, return zero scores
            results.append({
                "id": sample_id,
                "aggregate_reward_score": 0.0,
                "metrics_list": [
                    {"name": "schema_valid", "value": 0.0, "type": "Metric"},
                    {"name": "tool_precision", "value": 0.0, "type": "Metric"},
                    {"name": "tool_recall", "value": 0.0, "type": "Metric"},
                    {"name": "tool_f1", "value": 0.0, "type": "Metric"},
                    {"name": "parameter_accuracy", "value": 0.0, "type": "Metric"},
                    {"name": "sequence_accuracy", "value": 0.0, "type": "Metric"},
                    {"name": "overall_score", "value": 0.0, "type": "Reward"}
                ]
            })
            continue

        # Extract ground truth from reference_answer
        if "reference_answer" in sample:
            ground_truth = sample["reference_answer"]

            # Normalize ground truth: ensure Type is a list
            if "Type" in ground_truth and isinstance(ground_truth["Type"], str):
                ground_truth = ground_truth.copy()  # Don't modify original
                ground_truth["Type"] = [ground_truth["Type"]]
                print(f"[DEBUG] Normalized ground truth Type from string to list")
        else:
            # No ground truth available
            results.append({
                "id": sample_id,
                "aggregate_reward_score": 0.0,
                "metrics_list": [
                    {"name": "error", "value": 0.0, "type": "Metric"}
                ]
            })
            continue

        # Evaluate the response
        try:
            print(f"[DEBUG] Starting evaluation for sample {sample_id}")
            print(f"[DEBUG] Ground truth keys: {list(ground_truth.keys())}")
            print(f"[DEBUG] Predicted output keys: {list(predicted_output.keys())}")

            eval_result = evaluator.evaluate(ground_truth, predicted_output)
            print(f"[DEBUG] Evaluation completed successfully")
            print(f"[DEBUG] Schema validation: {eval_result['schema_validation']['passed']}")
            print(f"[DEBUG] Tool matching F1: {eval_result['tool_matching']['f1']}")
            print(f"[DEBUG] Parameter accuracy: {eval_result['parameter_matching']['accuracy']}")
            print(f"[DEBUG] Sequence accuracy: {eval_result['sequence_matching']['sequence_accuracy']}")
        except Exception as e:
            print(f"[ERROR] Exception during evaluation: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            # Return zero scores on evaluation error
            results.append({
                "id": sample_id,
                "aggregate_reward_score": 0.0,
                "metrics_list": [
                    {"name": "evaluation_error", "value": 0.0, "type": "Metric"}
                ]
            })
            continue

        # Calculate aggregate reward score
        aggregate_score = eval_result["overall_score"]
        print(f"[DEBUG] Overall score: {aggregate_score}")

        # Build metrics list
        metrics_list = [
            {
                "name": "schema_valid",
                "value": 1.0 if eval_result["schema_validation"]["passed"] else 0.0,
                "type": "Metric"
            },
            {
                "name": "tool_precision",
                "value": eval_result["tool_matching"]["precision"],
                "type": "Metric"
            },
            {
                "name": "tool_recall",
                "value": eval_result["tool_matching"]["recall"],
                "type": "Metric"
            },
            {
                "name": "tool_f1",
                "value": eval_result["tool_matching"]["f1"],
                "type": "Metric"
            },
            {
                "name": "parameter_accuracy",
                "value": eval_result["parameter_matching"]["accuracy"],
                "type": "Metric"
            },
            {
                "name": "sequence_accuracy",
                "value": eval_result["sequence_matching"]["sequence_accuracy"],
                "type": "Metric"
            },
            {
                "name": "lcs_ratio",
                "value": eval_result["sequence_matching"]["lcs_ratio"],
                "type": "Metric"
            },
            {
                "name": "overall_score",
                "value": aggregate_score,
                "type": "Reward"
            }
        ]

        # Format the result according to required schema
        result = {
            "id": sample_id,
            "aggregate_reward_score": aggregate_score,
            "metrics_list": metrics_list
        }

        results.append(result)

    print("*"*100)
    print(results)
    print("*"*100)

    return results


class QueryAnalysisEvaluator:
    """Evaluator for query analysis outputs"""

    def __init__(self, edit_distance_threshold: float = 0.8):
        """
        Args:
            edit_distance_threshold: Minimum similarity score for string matching (0-1)
        """
        self.edit_distance_threshold = edit_distance_threshold

    def evaluate(self, gold_answer: Dict, inference_output: Dict) -> Dict[str, Any]:
        """
        Evaluate inference output against gold answer

        Args:
            gold_answer: Ground truth query analysis
            inference_output: Model's predicted query analysis

        Returns:
            Dict with all metrics
        """
        schema_result = self.validate_schema(inference_output)
        tool_result = self.evaluate_tools(gold_answer, inference_output)
        param_result = self.evaluate_parameters(gold_answer, inference_output)
        sequence_result = self.evaluate_sequence(gold_answer, inference_output)

        # Calculate overall score
        overall = self._calculate_overall_score(
            schema_result, tool_result, param_result, sequence_result
        )

        return {
            "schema_validation": schema_result,
            "tool_matching": tool_result,
            "parameter_matching": param_result,
            "sequence_matching": sequence_result,
            "overall_score": overall
        }

    # ============= 1. SCHEMA VALIDATION =============
    def validate_schema(self, output: Dict) -> Dict[str, Any]:
        """
        Validate if output matches expected schema

        Returns:
            Dict with 'passed' (bool) and 'errors' (list)
        """
        errors = []

        # Check top-level keys
        required_keys = {"Type", "Information needed", "Tools"}
        if not isinstance(output, dict):
            return {"passed": False, "errors": ["Output is not a dictionary"]}

        missing_keys = required_keys - set(output.keys())
        if missing_keys:
            errors.append(f"Missing required keys: {missing_keys}")

        # Validate Type field
        if "Type" in output:
            if not isinstance(output["Type"], list):
                errors.append("'Type' must be a list")
            elif not all(isinstance(t, str) for t in output["Type"]):
                errors.append("'Type' must be a list of strings")

        # Validate Information needed field
        if "Information needed" in output:
            if not isinstance(output["Information needed"], str):
                errors.append("'Information needed' must be a string")

        # Validate Tools field
        if "Tools" in output:
            if not isinstance(output["Tools"], list):
                errors.append("'Tools' must be a list")
            else:
                for i, tool in enumerate(output["Tools"]):
                    tool_errors = self._validate_tool_schema(tool, i)
                    errors.extend(tool_errors)

        return {
            "passed": len(errors) == 0,
            "errors": errors
        }

    def _validate_tool_schema(self, tool: Any, index: int) -> List[str]:
        """Validate individual tool schema"""
        errors = []

        if not isinstance(tool, dict):
            errors.append(f"Tool at index {index} is not a dictionary")
            return errors

        required_tool_keys = {"Tool", "Parameters", "Reasoning"}
        missing_keys = required_tool_keys - set(tool.keys())
        if missing_keys:
            errors.append(f"Tool at index {index} missing keys: {missing_keys}")

        if "Tool" in tool and not isinstance(tool["Tool"], str):
            errors.append(f"Tool at index {index}: 'Tool' must be a string")

        if "Parameters" in tool and not isinstance(tool["Parameters"], dict):
            errors.append(f"Tool at index {index}: 'Parameters' must be a dict")

        if "Reasoning" in tool and not isinstance(tool["Reasoning"], str):
            errors.append(f"Tool at index {index}: 'Reasoning' must be a string")

        return errors

    # ============= 2. TOOL MATCHING =============
    def evaluate_tools(self, gold: Dict, pred: Dict) -> Dict[str, Any]:
        """
        Evaluate if the right tools are called

        Returns:
            Dict with precision, recall, f1, and details
        """
        if "Tools" not in gold or "Tools" not in pred:
            return {
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "matched_tools": [],
                "missing_tools": [],
                "extra_tools": []
            }

        gold_tools = {tool["Tool"] for tool in gold["Tools"]}
        pred_tools = {tool["Tool"] for tool in pred["Tools"]}

        matched = gold_tools & pred_tools
        missing = gold_tools - pred_tools
        extra = pred_tools - gold_tools

        precision = len(matched) / len(pred_tools) if pred_tools else 0.0
        recall = len(matched) / len(gold_tools) if gold_tools else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "matched_tools": list(matched),
            "missing_tools": list(missing),
            "extra_tools": list(extra)
        }

    # ============= 3. PARAMETER MATCHING =============
    def evaluate_parameters(self, gold: Dict, pred: Dict) -> Dict[str, Any]:
        """
        Evaluate if tools are called with correct parameters
        Uses edit distance for string comparisons

        Returns:
            Dict with accuracy and per-tool parameter scores
        """
        if "Tools" not in gold or "Tools" not in pred:
            return {"accuracy": 0.0, "tool_scores": {}}

        # Create tool name to parameters mapping
        gold_params = {tool["Tool"]: tool.get("Parameters", {}) 
                       for tool in gold["Tools"]}
        pred_params = {tool["Tool"]: tool.get("Parameters", {}) 
                       for tool in pred["Tools"]}

        tool_scores = {}
        total_score = 0.0
        tools_evaluated = 0

        for tool_name in set(gold_params.keys()) & set(pred_params.keys()):
            score = self._compare_parameters(
                gold_params[tool_name], 
                pred_params[tool_name]
            )
            tool_scores[tool_name] = score
            total_score += score
            tools_evaluated += 1

        accuracy = total_score / tools_evaluated if tools_evaluated > 0 else 0.0

        return {
            "accuracy": accuracy,
            "tool_scores": tool_scores
        }

    def _compare_parameters(self, gold_params: Dict, pred_params: Dict) -> float:
        """Compare parameter dictionaries and return similarity score"""
        if not gold_params and not pred_params:
            return 1.0

        if not gold_params or not pred_params:
            return 0.0

        # Check key overlap
        gold_keys = set(gold_params.keys())
        pred_keys = set(pred_params.keys())

        if gold_keys != pred_keys:
            key_score = len(gold_keys & pred_keys) / len(gold_keys | pred_keys)
        else:
            key_score = 1.0

        # Compare values for matching keys
        value_scores = []
        for key in gold_keys & pred_keys:
            gold_val = gold_params[key]
            pred_val = pred_params[key]
            value_scores.append(self._compare_values(gold_val, pred_val))

        value_score = sum(value_scores) / len(value_scores) if value_scores else 0.0

        # Combined score (weighted average)
        return 0.3 * key_score + 0.7 * value_score

    def _compare_values(self, gold_val: Any, pred_val: Any) -> float:
        """Compare individual parameter values"""
        # Handle lists
        if isinstance(gold_val, list) and isinstance(pred_val, list):
            if not gold_val and not pred_val:
                return 1.0
            gold_set = set(str(v) for v in gold_val)
            pred_set = set(str(v) for v in pred_val)
            intersection = len(gold_set & pred_set)
            union = len(gold_set | pred_set)
            return intersection / union if union > 0 else 0.0

        # Handle strings with edit distance
        if isinstance(gold_val, str) and isinstance(pred_val, str):
            return self._string_similarity(gold_val, pred_val)

        # Handle other types with exact match
        return 1.0 if gold_val == pred_val else 0.0

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using character overlap"""
        s1_lower = s1.lower()
        s2_lower = s2.lower()

        if not s1_lower or not s2_lower:
            return 0.0 if s1_lower != s2_lower else 1.0

        # Calculate character-level overlap
        s1_chars = set(s1_lower)
        s2_chars = set(s2_lower)

        intersection = len(s1_chars & s2_chars)
        union = len(s1_chars | s2_chars)

        char_similarity = intersection / union if union > 0 else 0.0

        # Calculate token-level overlap
        s1_tokens = s1_lower.split()
        s2_tokens = s2_lower.split()

        if s1_tokens and s2_tokens:
            token_intersection = len(set(s1_tokens) & set(s2_tokens))
            token_union = len(set(s1_tokens) | set(s2_tokens))
            token_similarity = token_intersection / token_union if token_union > 0 else 0.0
        else:
            token_similarity = char_similarity

        # Combined similarity (weighted average)
        return 0.4 * char_similarity + 0.6 * token_similarity

    # ============= 4. SEQUENCE MATCHING =============
    def evaluate_sequence(self, gold: Dict, pred: Dict) -> Dict[str, Any]:
        """
        Evaluate if tools are called in the correct order

        Returns:
            Dict with sequence accuracy and alignment details
        """
        if "Tools" not in gold or "Tools" not in pred:
            return {
                "sequence_accuracy": 0.0,
                "lcs_ratio": 0.0,
                "correct_positions": 0,
                "total_positions": 0
            }

        gold_sequence = [tool["Tool"] for tool in gold["Tools"]]
        pred_sequence = [tool["Tool"] for tool in pred["Tools"]]

        # Longest Common Subsequence
        lcs_length = self._lcs_length(gold_sequence, pred_sequence)
        lcs_ratio = lcs_length / len(gold_sequence) if gold_sequence else 0.0

        # Positional accuracy (exact matches at same index)
        correct_positions = sum(
            1 for i in range(min(len(gold_sequence), len(pred_sequence)))
            if gold_sequence[i] == pred_sequence[i]
        )

        sequence_accuracy = correct_positions / len(gold_sequence) if gold_sequence else 0.0

        return {
            "sequence_accuracy": sequence_accuracy,
            "lcs_ratio": lcs_ratio,
            "correct_positions": correct_positions,
            "total_positions": len(gold_sequence),
            "gold_sequence": gold_sequence,
            "pred_sequence": pred_sequence
        }

    def _lcs_length(self, seq1: List[str], seq2: List[str]) -> int:
        """Calculate longest common subsequence length"""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])

        return dp[m][n]

    # ============= OVERALL SCORE =============
    def _calculate_overall_score(
        self, 
        schema: Dict, 
        tools: Dict, 
        params: Dict, 
        sequence: Dict
    ) -> float:
        """Calculate weighted overall score"""
        if not schema["passed"]:
            return 0.0

        weights = {
            "tools": 0.3,
            "params": 0.3,
            "sequence": 0.4
        }

        score = (
            weights["tools"] * tools["f1"] +
            weights["params"] * params["accuracy"] +
            weights["sequence"] * sequence["sequence_accuracy"]
        )

        return score

