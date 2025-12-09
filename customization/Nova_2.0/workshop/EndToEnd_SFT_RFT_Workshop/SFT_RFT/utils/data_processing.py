import json
import os
from pathlib import Path
import random
from typing import Union, List, Dict, Any
import tempfile
import shutil


def convert_to_jsonl(input=None, input_dir=None, exclude=None, output_file=None):
    """
    Read JSON file(s), extract cot_examples arrays, write to JSONL

    Args:
        input: Single JSON file path (str)
        input_dir: Directory containing JSON files (str)
        exclude: Files/patterns to exclude (str, list, or None)
                 - Single pattern: "combined_*"
                 - Multiple patterns: ["combined_*", "cases_*", "specific_file.json"]
                 - Specific files: "rule_506_cot_examples.json"
        output_file: Output JSONL file path

    Use either input OR input_dir, not both.
    """
    import fnmatch

    all_examples = []

    # Validate inputs
    if input and input_dir:
        raise ValueError(
            "Specify either 'input' (single file) OR 'input_dir' (directory), not both"
        )
    if not input and not input_dir:
        raise ValueError(
            "Must specify either 'input' (single file) OR 'input_dir' (directory)"
        )

    # Handle exclude parameter
    if exclude is None:
        exclude = []
    elif isinstance(exclude, str):
        exclude = [exclude]
    elif not isinstance(exclude, list):
        exclude = list(exclude)

    # Handle single file
    if input:
        json_files = [Path(input)]
        print(f"Processing single file: {input}")

    # Handle directory with exclusions
    else:
        all_json_files = sorted(Path(input_dir).glob("*.json"))

        # Filter out excluded files
        json_files = []
        for json_file in all_json_files:
            exclude_file = False

            for pattern in exclude:
                # Check if pattern matches filename or full path
                if fnmatch.fnmatch(json_file.name, pattern) or fnmatch.fnmatch(
                    str(json_file), pattern
                ):
                    exclude_file = True
                    print(f"  🚫 Excluding: {json_file.name} (matches '{pattern}')")
                    break

            if not exclude_file:
                json_files.append(json_file)

        print(f"Processing {len(json_files)} files from directory: {input_dir}")
        if exclude:
            print(
                f"Excluded {len(all_json_files) - len(json_files)} files matching: {exclude}"
            )

    # Process files
    for json_file in json_files:
        try:
            with open(json_file, "r") as f:
                data = json.load(f)

            # Extract cot_examples array
            if "cot_examples" in data and isinstance(data["cot_examples"], list):
                examples = data["cot_examples"]
                all_examples.extend(examples)
                print(f"  ✓ {json_file.name}: {len(examples)} examples")
            else:
                print(f"  ⚠ {json_file.name}: no cot_examples found")

        except Exception as e:
            print(f"  ✗ {json_file.name}: {str(e)}")

    # Write to JSONL
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        for example in all_examples:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")

    print(f"\n✓ Wrote {len(all_examples)} examples to {output_file}")
    return output_file


def add_system_prompt(prompt, input_file, output_file=None):
    """
    Add system prompt to JSONL training data

    Args:
        input_file: Path to input JSONL file
        output_file: Path to output file (defaults to input_file with '_with_system.jsonl' suffix)
    """

    SYSTEM_PROMPT = prompt

    # Set output file
    if output_file is None:
        input_path = Path(input_file)
        output_file = input_path.parent / f"{input_path.stem}_with_system.jsonl"

    processed_count = 0

    with open(input_file, "r", encoding="utf-8") as infile, open(
        output_file, "w", encoding="utf-8"
    ) as outfile:

        for line_num, line in enumerate(infile, 1):
            try:
                # Parse the JSON line
                data = json.loads(line.strip())

                # Add system prompt as separate field (not in messages array)
                data["system"] = [{"text": SYSTEM_PROMPT}]

                # Write modified line
                outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
                processed_count += 1

                if processed_count % 100 == 0:
                    print(f"Processed {processed_count} examples...")

            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")
                continue
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
                continue

    print(f"✓ Added system prompt to {processed_count} examples")
    print(f"✓ Output written to: {output_file}")


# Clean final data up
##
def validate_training_data(input_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Validate fine-tuning JSONL data for securities law tool selection

    Args:
        input_path: Path to JSONL file or directory containing JSONL files

    Returns:
        Dict with validation results and detailed error reports
    """

    # Expected system prompt (exact match required)
    EXPECTED_SYSTEM_PROMPT = """You are a securities law tool selection specialist.

Your task: 
1. Classify query type from 8 predefined categories
2. Select appropriate tools, tool input, and tool sequence. Provide reasoning for each tool choice.
3. Focus on connecting SEC regulations, EDGAR filings, and case law through expert tool selection decisions.
4. Output structured JSON format:
```json
"{\"Query analysis\": {\"Type\": \"[predefined_type]\", \"Information needed\": \"[specific_requirements]\", \"Tools\": [{\"Tool\": \"[tool_name]\", \"Parameters\": {[parameter_dict]}, \"Reasoning\": \"[why_this_tool]\"}, {\"Tool\": \"[tool_name_2]\", \"Parameters\": {[parameter_dict_2]}, \"Reasoning\": \"[why_this_tool_2]\"}]}}"
```

AVAILABLE TOOLS: statute_retrieval, case_law_search, compliance_checker, citation_validator

PREDEFINED TYPES: regulatory_definition, judicial_interpretation, compliance_validation, citation_verification, regulatory_compliance_analysis, judicial_compliance_assessment, cross_document_analysis, regulatory_interpretation_research"""

    # Valid tool names and their parameter schemas
    TOOL_SCHEMAS = {
        "statute_retrieval": {"regulation": str},
        "case_law_search": {"query": str},
        "compliance_checker": {
            "query": str,
            "edgar_check": str,
            "regulation": str,
            "case_interpretation_check": str,
        },
        "citation_validator": {"query": str},
    }

    # Valid predefined types
    PREDEFINED_TYPES = {
        "regulatory_definition",
        "judicial_interpretation",
        "compliance_validation",
        "citation_verification",
        "regulatory_compliance_analysis",
        "judicial_compliance_assessment",
        "cross_document_analysis",
        "regulatory_interpretation_research",
    }

    def validate_single_file(file_path: Path) -> Dict[str, Any]:
        """Validate a single JSONL file"""
        results = {
            "file": str(file_path),
            "total_lines": 0,
            "valid_examples": 0,
            "errors": [],
            "warnings": [],
        }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    results["total_lines"] += 1

                    try:
                        # Parse JSON line
                        data = json.loads(line.strip())

                        # Validate structure
                        if not validate_example_structure(data, line_num, results):
                            continue

                        # Validate system prompt
                        if not validate_system_prompt(
                            data, line_num, results, EXPECTED_SYSTEM_PROMPT
                        ):
                            continue

                        # Validate user message
                        if not validate_user_message(data, line_num, results):
                            continue

                        # Validate assistant message
                        if not validate_assistant_message(
                            data, line_num, results, TOOL_SCHEMAS, PREDEFINED_TYPES
                        ):
                            continue

                        results["valid_examples"] += 1

                    except json.JSONDecodeError as e:
                        results["errors"].append(
                            f"Line {line_num}: Invalid JSON - {str(e)}"
                        )
                    except Exception as e:
                        results["errors"].append(
                            f"Line {line_num}: Unexpected error - {str(e)}"
                        )

        except FileNotFoundError:
            results["errors"].append(f"File not found: {file_path}")
        except Exception as e:
            results["errors"].append(f"Error reading file: {str(e)}")

        return results

    def validate_example_structure(data: Dict, line_num: int, results: Dict) -> bool:
        """Validate basic conversation structure"""
        if not isinstance(data, dict):
            results["errors"].append(
                f"Line {line_num}: Root must be dict, got {type(data)}"
            )
            return False

        if "messages" not in data:
            results["errors"].append(f"Line {line_num}: Missing 'messages' field")
            return False

        if not isinstance(data["messages"], list):
            results["errors"].append(
                f"Line {line_num}: 'messages' must be list, got {type(data['messages'])}"
            )
            return False

        if len(data["messages"]) != 2:  # user, assistant
            results["errors"].append(
                f"Line {line_num}: Expected 2 messages (user, assistant), got {len(data['messages'])}"
            )
            return False

        if "system" not in data:
            results["errors"].append(f"Line {line_num}: Missing 'system' field")
            return False

        return True

    def validate_system_prompt(
        data: Dict, line_num: int, results: Dict, expected_prompt: str
    ) -> bool:
        """Validate system prompt matches exactly"""
        system_field = data.get("system", [])

        if not isinstance(system_field, list) or len(system_field) != 1:
            results["errors"].append(
                f"Line {line_num}: System field must be list with 1 element"
            )
            return False

        text = system_field[0].get("text", "")
        if text != expected_prompt:
            results["errors"].append(
                f"Line {line_num}: System prompt does not match expected prompt"
            )
            return False

        return True

    def validate_user_message(data: Dict, line_num: int, results: Dict) -> bool:
        """Validate user message structure and content"""
        user_msg = data["messages"][0]

        if user_msg.get("role") != "user":
            results["errors"].append(
                f"Line {line_num}: First message must have role 'user', got '{user_msg.get('role')}'"
            )
            return False

        content = user_msg.get("content", [])
        if not isinstance(content, list) or len(content) != 1:
            results["errors"].append(
                f"Line {line_num}: User content must be list with 1 element"
            )
            return False

        text = content[0].get("text", "")
        if not isinstance(text, str) or not text.strip():
            results["errors"].append(
                f"Line {line_num}: User message must contain non-empty string"
            )
            return False

        return True

    def validate_assistant_message(
        data: Dict,
        line_num: int,
        results: Dict,
        tool_schemas: Dict,
        predefined_types: set,
    ) -> bool:
        """Validate assistant message structure and JSON content"""
        assistant_msg = data["messages"][1]

        if assistant_msg.get("role") != "assistant":
            results["errors"].append(
                f"Line {line_num}: Second message must have role 'assistant', got '{assistant_msg.get('role')}'"
            )
            return False

        content = assistant_msg.get("content", [])
        if not isinstance(content, list) or len(content) != 1:
            results["errors"].append(
                f"Line {line_num}: Assistant content must be list with 1 element"
            )
            return False

        text = content[0].get("text", "")
        if not isinstance(text, str):
            results["errors"].append(
                f"Line {line_num}: Assistant content text must be string"
            )
            return False

        # Parse the JSON content
        try:
            response_data = json.loads(text)
        except json.JSONDecodeError as e:
            results["errors"].append(
                f"Line {line_num}: Assistant response not valid JSON - {str(e)}"
            )
            return False

        # Validate Query analysis structure
        if "Query analysis" not in response_data:
            results["errors"].append(f"Line {line_num}: Missing 'Query analysis' field")
            return False

        query_analysis = response_data["Query analysis"]

        # Validate Type
        if "Type" not in query_analysis:
            results["errors"].append(f"Line {line_num}: Missing 'Type' field")
            return False

        if query_analysis["Type"] not in predefined_types:
            results["errors"].append(
                f"Line {line_num}: Invalid Type '{query_analysis['Type']}', must be one of: {predefined_types}"
            )
            return False

        # Validate Information needed
        if "Information needed" not in query_analysis:
            results["errors"].append(
                f"Line {line_num}: Missing 'Information needed' field"
            )
            return False

        if not isinstance(query_analysis["Information needed"], str):
            results["errors"].append(
                f"Line {line_num}: 'Information needed' must be string"
            )
            return False

        # Validate Tools array
        if "Tools" not in query_analysis:
            results["errors"].append(f"Line {line_num}: Missing 'Tools' field")
            return False

        tools = query_analysis["Tools"]
        if not isinstance(tools, list) or len(tools) == 0:
            results["errors"].append(f"Line {line_num}: 'Tools' must be non-empty list")
            return False

        # Validate each tool
        for i, tool in enumerate(tools):
            if not validate_tool(tool, line_num, i, results, tool_schemas):
                return False

        return True

    def validate_tool(
        tool: Dict, line_num: int, tool_idx: int, results: Dict, tool_schemas: Dict
    ) -> bool:
        """Validate individual tool structure and parameters"""

        # Check tool structure
        required_fields = ["Tool", "Parameters", "Reasoning"]
        for field in required_fields:
            if field not in tool:
                results["errors"].append(
                    f"Line {line_num}, Tool {tool_idx}: Missing '{field}' field"
                )
                return False

        # Validate Tool name
        tool_name = tool["Tool"]
        if tool_name not in tool_schemas:
            results["errors"].append(
                f"Line {line_num}, Tool {tool_idx}: Invalid tool '{tool_name}', must be one of: {list(tool_schemas.keys())}"
            )
            return False

        # Validate Parameters
        parameters = tool["Parameters"]
        if not isinstance(parameters, dict):
            results["errors"].append(
                f"Line {line_num}, Tool {tool_idx}: Parameters must be dict, got {type(parameters)}"
            )
            return False

        # Check parameter schema
        expected_schema = tool_schemas[tool_name]

        # Check all required parameters are present
        for param_name, param_type in expected_schema.items():
            if param_name not in parameters:
                results["errors"].append(
                    f"Line {line_num}, Tool {tool_idx}: Missing required parameter '{param_name}'"
                )
                return False

            param_value = parameters[param_name]
            if not isinstance(param_value, param_type):
                results["errors"].append(
                    f"Line {line_num}, Tool {tool_idx}: Parameter '{param_name}' must be {param_type.__name__}, got {type(param_value)}"
                )
                return False

        # Check no extra parameters
        for param_name in parameters:
            if param_name not in expected_schema:
                results["warnings"].append(
                    f"Line {line_num}, Tool {tool_idx}: Unexpected parameter '{param_name}'"
                )

        # Validate Reasoning
        reasoning = tool["Reasoning"]
        if not isinstance(reasoning, str) or not reasoning.strip():
            results["errors"].append(
                f"Line {line_num}, Tool {tool_idx}: Reasoning must be non-empty string"
            )
            return False

        return True

    # Main validation logic
    input_path = Path(input_path)

    if input_path.is_file():
        # Single file
        file_results = validate_single_file(input_path)
        return {
            "validation_type": "single_file",
            "results": [file_results],
            "summary": {
                "total_files": 1,
                "total_examples": file_results["total_lines"],
                "valid_examples": file_results["valid_examples"],
                "error_count": len(file_results["errors"]),
                "warning_count": len(file_results["warnings"]),
            },
        }

    elif input_path.is_dir():
        # Directory of files
        jsonl_files = list(input_path.glob("*.jsonl"))

        if not jsonl_files:
            return {
                "validation_type": "directory",
                "error": f"No JSONL files found in {input_path}",
                "results": [],
            }

        all_results = []
        total_examples = 0
        total_valid = 0
        total_errors = 0
        total_warnings = 0

        for file_path in jsonl_files:
            file_results = validate_single_file(file_path)
            all_results.append(file_results)

            total_examples += file_results["total_lines"]
            total_valid += file_results["valid_examples"]
            total_errors += len(file_results["errors"])
            total_warnings += len(file_results["warnings"])

        return {
            "validation_type": "directory",
            "results": all_results,
            "summary": {
                "total_files": len(jsonl_files),
                "total_examples": total_examples,
                "valid_examples": total_valid,
                "error_count": total_errors,
                "warning_count": total_warnings,
                "validation_rate": (
                    f"{(total_valid/total_examples*100):.1f}%"
                    if total_examples > 0
                    else "0%"
                ),
            },
        }

    else:
        return {
            "validation_type": "error",
            "error": f"Path does not exist: {input_path}",
            "results": [],
        }


def categorize_errors(all_errors: List[str]) -> Dict[str, Dict[str, Any]]:
    """Categorize and summarize errors by type"""
    categories = {}

    for error in all_errors:
        # Determine error category
        if "Assistant response not valid JSON" in error:
            if "Expecting ','" in error:
                category = "JSON Parsing - Missing Comma"
            elif "Expecting ':'" in error:
                category = "JSON Parsing - Missing Colon"
            elif "Expecting '}'" in error:
                category = "JSON Parsing - Missing Brace"
            else:
                category = "JSON Parsing - Other"
        elif "Invalid Type" in error:
            category = "Invalid Predefined Type"
        elif "Missing required parameter" in error:
            category = "Missing Tool Parameters"
        elif "Parameter" in error and "must be" in error:
            category = "Wrong Parameter Type"
        elif "System prompt does not match" in error:
            category = "System Prompt Mismatch"
        elif "Missing 'Query analysis'" in error:
            category = "Missing Query Analysis Structure"
        elif "must have role" in error:
            category = "Invalid Message Role"
        elif "Invalid tool" in error:
            category = "Invalid Tool Name"
        else:
            category = "Other Error"

        if category not in categories:
            categories[category] = {"count": 0, "examples": []}

        categories[category]["count"] += 1
        if len(categories[category]["examples"]) < 3:  # Keep first 3 examples
            categories[category]["examples"].append(error)

    return categories


def categorize_warnings(all_warnings: List[str]) -> Dict[str, Dict[str, Any]]:
    """Categorize and summarize warnings by type"""
    categories = {}

    for warning in all_warnings:
        if "Unexpected parameter" in warning:
            category = "Unexpected Tool Parameters"
        else:
            category = "Other Warning"

        if category not in categories:
            categories[category] = {"count": 0, "examples": []}

        categories[category]["count"] += 1
        if len(categories[category]["examples"]) < 3:
            categories[category]["examples"].append(warning)

    return categories


def print_validation_report(validation_results: Dict[str, Any]) -> None:
    """Print formatted validation report with error summarization"""

    print("🔍 TRAINING DATA VALIDATION REPORT")
    print("=" * 50)

    if "error" in validation_results:
        print(f"❌ ERROR: {validation_results['error']}")
        return

    summary = validation_results["summary"]
    print(f"📁 Files processed: {summary['total_files']}")
    print(f"📊 Total examples: {summary['total_examples']}")
    print(f"✅ Valid examples: {summary['valid_examples']}")
    print(f"❌ Errors: {summary['error_count']}")
    print(f"⚠️ Warnings: {summary['warning_count']}")

    if "validation_rate" in summary:
        print(f"📈 Validation rate: {summary['validation_rate']}")

    # Collect all errors and warnings for categorization
    all_errors = []
    all_warnings = []

    for file_result in validation_results["results"]:
        all_errors.extend(file_result["errors"])
        all_warnings.extend(file_result["warnings"])

    # Show error summary
    if all_errors:
        print(f"\n🚨 ERROR SUMMARY:")
        error_categories = categorize_errors(all_errors)

        for category, details in sorted(
            error_categories.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            print(f"   {category}: {details['count']} occurrences")
            if details["examples"]:
                for example in details["examples"]:
                    print(f"     • {example}")
                if details["count"] > len(details["examples"]):
                    print(
                        f"     ... and {details['count'] - len(details['examples'])} more"
                    )
            print()

    # Show warning summary
    if all_warnings:
        print(f"⚠️ WARNING SUMMARY:")
        warning_categories = categorize_warnings(all_warnings)

        for category, details in sorted(
            warning_categories.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            print(f"   {category}: {details['count']} occurrences")
            if details["examples"]:
                for example in details["examples"]:
                    print(f"     • {example}")
                if details["count"] > len(details["examples"]):
                    print(
                        f"     ... and {details['count'] - len(details['examples'])} more"
                    )
            print()

    # Show file-by-file summary for directories
    if (
        validation_results["validation_type"] == "directory"
        and len(validation_results["results"]) > 1
    ):
        print(f"📋 FILE SUMMARY:")

        for file_result in validation_results["results"]:
            file_name = Path(file_result["file"]).name
            valid_rate = (
                f"{(file_result['valid_examples']/file_result['total_lines']*100):.1f}%"
                if file_result["total_lines"] > 0
                else "0%"
            )

            status = "✅" if len(file_result["errors"]) == 0 else "❌"
            error_count = len(file_result["errors"])
            warning_count = len(file_result["warnings"])

            print(
                f"{status} {file_name}: {file_result['valid_examples']}/{file_result['total_lines']} valid ({valid_rate}) - {error_count} errors, {warning_count} warnings"
            )


def validate_and_report(
    input_path: str,
    output_path: str = None,
    fix: bool = False,
    fix_inplace: bool = True,
) -> Dict[str, Any]:
    """
    Single function to validate training data and generate complete report

    Args:
        input_path: Path to JSONL file or directory
        output_path: Path to save validation report (defaults to input_path + '_validation_report.json')
        fix: If True, removes erroneous lines from the file
        fix_inplace: If True, modifies original file; if False, creates new file with suffix

    Returns:
        Validation results dict
    """
    results = validate_training_data(input_path)

    if output_path is not None:
        input_name = Path(input_path).stem
        output_path = f"{input_name}_validation_report.json"
        # Save detailed report to JSON
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"💾 Validation report saved to: {output_path}")
    print_validation_report(results)

    # Fix errors if requested and if we have a single file with errors
    if fix and results.get("validation_type") == "single_file" and results["results"]:
        file_result = results["results"][0]

        if file_result["errors"] or file_result["warnings"]:
            # Extract line numbers from error and warning messages
            problematic_lines = set()
            for error in file_result["errors"]:
                # Parse line number from error message format "Line X: ..." or "Line X, Tool Y: ..."
                if error.startswith("Line "):
                    try:
                        # Handle both "Line 870:" and "Line 870, Tool 1:" formats
                        line_part = error.split(":")[
                            0
                        ]  # Get "Line 870" or "Line 870, Tool 1"
                        if ", Tool " in line_part:
                            line_num = int(
                                line_part.split(",")[0].split(" ")[1]
                            )  # Extract from "Line 870, Tool 1"
                        else:
                            line_num = int(
                                line_part.split(" ")[1]
                            )  # Extract from "Line 870"
                        problematic_lines.add(line_num)
                    except (ValueError, IndexError):
                        continue

            for warning in file_result["warnings"]:
                # Parse line number from warning message format "Line X: ..." or "Line X, Tool Y: ..."
                if warning.startswith("Line "):
                    try:
                        # Handle both "Line 655:" and "Line 655, Tool 0:" formats
                        line_part = warning.split(":")[
                            0
                        ]  # Get "Line 655" or "Line 655, Tool 0"
                        if ", Tool " in line_part:
                            line_num = int(
                                line_part.split(",")[0].split(" ")[1]
                            )  # Extract from "Line 655, Tool 0"
                        else:
                            line_num = int(
                                line_part.split(" ")[1]
                            )  # Extract from "Line 655"
                        problematic_lines.add(line_num)
                    except (ValueError, IndexError):
                        continue

            if problematic_lines:
                input_file_path = Path(input_path)

                lines_written = 0
                lines_removed = 0

                if fix_inplace:
                    # Create backup first
                    # backup_path = str(input_file_path) + '.backup'
                    # shutil.copy2(input_file_path, backup_path)
                    # print(f"📋 Created backup: {backup_path}")

                    # Use temporary file for writing
                    with tempfile.NamedTemporaryFile(
                        mode="w", delete=False, suffix=".jsonl", encoding="utf-8"
                    ) as temp_file:
                        temp_path = temp_file.name

                        # Read from original, write to temp
                        with open(input_file_path, "r", encoding="utf-8") as infile:
                            for line_num, line in enumerate(infile, 1):
                                if line_num not in problematic_lines:
                                    temp_file.write(line)
                                    lines_written += 1
                                else:
                                    lines_removed += 1

                    # Replace original file with cleaned temp file
                    shutil.move(temp_path, input_file_path)
                    output_file_path = input_file_path

                else:
                    # Create new file with _fixed suffix
                    output_file_path = (
                        input_file_path.parent
                        / f"{input_file_path.stem}_fixed{input_file_path.suffix}"
                    )

                    with open(input_file_path, "r", encoding="utf-8") as infile:
                        with open(output_file_path, "w", encoding="utf-8") as outfile:
                            for line_num, line in enumerate(infile, 1):
                                if line_num not in problematic_lines:
                                    outfile.write(line)
                                    lines_written += 1
                                else:
                                    lines_removed += 1

                print(f"🔧 Fixed file saved to: {output_file_path}")
                print(f"✅ Lines written: {lines_written}")
                print(f"🗑️ Lines removed: {lines_removed}")

                # Update results with fix information
                results["fix_applied"] = True
                results["fixed_file_path"] = str(output_file_path)
                results["lines_removed"] = lines_removed
                results["lines_written"] = lines_written

            else:
                print("ℹ️ No line-specific errors or warnings found to fix.")
        else:
            print("✨ No errors or warnings found - file is already clean!")

    elif fix and results.get("validation_type") == "directory":
        print(
            "⚠️ Fix functionality is only available for single files, not directories."
        )
##


def split_jsonl(
    input_file="data/final/combined_training_data.jsonl",
    output_dir="data/final",
    train=0.72,
    val=0.18,
    test=0.10,
):
    # Read
    examples = [json.loads(line) for line in open(input_file)]
    random.shuffle(examples)

    # Split
    n_train = int(len(examples) * train)
    n_val = int(len(examples) * val)

    splits = {
        "train": examples[:n_train],
        "val": examples[n_train : n_train + n_val],
        "test": examples[n_train + n_val :],
    }

    # Write
    for split_name, data in splits.items():
        path = Path(output_dir) / split_name
        path.mkdir(parents=True, exist_ok=True)
        with open(path / f"{split_name}.jsonl", "w") as f:
            for ex in data:
                f.write(json.dumps(ex) + "\n")
        print(f"{split_name}: {len(data)}")


# RFT format
"""
Transform SFT (Supervised Fine-Tuning) data to RFT (Rejection Fine-Tuning) format.

This script reads JSONL files in SFT format and converts them to RFT format by:
1. Adding sequential IDs
2. Flattening content arrays (extract text from [{"text": "..."}] format)
3. Moving assistant response to reference_answer field
4. Parsing assistant's JSON response as structured data
"""

import json
from pathlib import Path
from typing import Any, Dict


def flatten_content(content: Any) -> str:
    """
    Flatten content from array format to string.

    Args:
        content: Content in format [{"text": "..."}] or string

    Returns:
        Flattened string content
    """
    if isinstance(content, list):
        # Extract text from list of dicts
        texts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                texts.append(item["text"])
        return " ".join(texts)
    elif isinstance(content, str):
        return content
    else:
        return str(content)


def parse_assistant_response(response_text: str) -> Dict[str, Any]:
    """
    Parse the assistant's JSON response into structured format.

    Args:
        response_text: The assistant's response containing JSON

    Returns:
        Parsed reference answer dictionary
    """
    try:
        # The response is a JSON string, parse it
        parsed = json.loads(response_text)

        # Extract Query analysis
        if "Query analysis" in parsed:
            return parsed["Query analysis"]
        else:
            # Response might be the Query analysis directly
            return parsed

    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse assistant response as JSON: {e}")
        print(f"Response text: {response_text[:200]}...")
        return {"raw_response": response_text}


def transform_sft_to_rft(sft_record: Dict[str, Any], record_id: str) -> Dict[str, Any]:
    """
    Transform a single SFT record to RFT format.

    Args:
        sft_record: SFT format record
        record_id: Sequential ID for the record

    Returns:
        RFT format record
    """
    messages = sft_record.get("messages", [])

    # Extract and transform messages (system and user only)
    rft_messages = []
    assistant_message = None

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")

        if role == "assistant":
            # Save assistant message for reference_answer
            assistant_message = content
        else:
            # Transform system and user messages
            rft_messages.append({"role": role, "content": flatten_content(content)})

    # Parse assistant's response as reference answer
    reference_answer = {}
    if assistant_message:
        assistant_text = flatten_content(assistant_message)
        reference_answer = parse_assistant_response(assistant_text)

    # Build RFT record
    rft_record = {
        "id": record_id,
        "messages": rft_messages,
        "reference_answer": reference_answer,
    }

    return rft_record


def _process_single_file(input_path: Path, output_path: Path) -> None:
    """
    Process a single JSONL file from SFT to RFT format.

    Args:
        input_path: Path to input SFT JSONL file
        output_path: Path to output RFT JSONL file
    """
    print(f"\nReading from: {input_path}")
    print(f"Writing to: {output_path}")

    records_processed = 0
    records_failed = 0

    with open(input_path, "r", encoding="utf-8") as infile, open(
        output_path, "w", encoding="utf-8"
    ) as outfile:

        for line_num, line in enumerate(infile, 1):
            try:
                # Parse SFT record
                sft_record = json.loads(line.strip())

                # Generate sequential ID (5-digit zero-padded)
                record_id = f"{line_num:05d}"

                # Transform to RFT
                rft_record = transform_sft_to_rft(sft_record, record_id)

                # Write RFT record
                outfile.write(json.dumps(rft_record, ensure_ascii=False) + "\n")

                records_processed += 1

                if records_processed % 100 == 0:
                    print(f"Processed {records_processed} records...")

            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
                records_failed += 1
                continue

    print(f"Transformation complete for {input_path.name}!")
    print(f"  Records processed: {records_processed}")
    print(f"  Records failed: {records_failed}")
    print(f"  Output file: {output_path}")


def data_sft_rft(input_path: str, output_path: str = None) -> None:
    """
    Transform SFT format data to RFT format.

    Handles both file and directory paths:
    - If input is a file, transforms that single file
    - If input is a directory, transforms all .jsonl files in that directory

    Args:
        input_path: Path to input SFT file or directory (as string)
        output_path: Path to output RFT file or directory (as string).
                     If None, creates output path automatically:
                     - For files: adds '_rft' suffix before extension
                     - For directories: creates 'RFT' subdirectory in same location
    """
    input_p = Path(input_path)

    # Generate default output path if not provided
    if output_path is None:
        if input_p.is_dir():
            # For directories, create RFT subdirectory
            output_p = input_p.parent / "RFT"
        else:
            # For files, add _rft suffix before extension
            output_p = input_p.parent / f"{input_p.stem}_rft{input_p.suffix}"
    else:
        output_p = Path(output_path)

    # Handle directory input
    if input_p.is_dir():
        print(f"Processing directory: {input_p}")

        # Find all .jsonl files
        jsonl_files = list(input_p.glob("*.jsonl"))

        if not jsonl_files:
            print(f"No .jsonl files found in {input_p}")
            return

        print(f"Found {len(jsonl_files)} .jsonl file(s)")

        # Create output directory if needed
        output_p.mkdir(parents=True, exist_ok=True)

        # Process each file
        for jsonl_file in jsonl_files:
            output_file = output_p / jsonl_file.name
            _process_single_file(jsonl_file, output_file)

    # Handle single file input
    else:
        # Create output directory if it doesn't exist
        output_p.parent.mkdir(parents=True, exist_ok=True)
        _process_single_file(input_p, output_p)


# Prepare data format for eval
def nova_offline_eval(input_path: Union[str, Path], output_path: Union[str, Path] = None) -> None:
    """
    Convert JSONL files from messages format to flat format for Nova offline evaluation.
    
    Args:
        input_path: Path to input JSONL file or directory
        output_path: Path for output file (optional, defaults to input_path with _flat suffix)
    """
    def convert_single_file(input_file: Path, output_file: Path) -> None:
        """Convert a single JSONL file from messages format to flat format."""
        converted_count = 0
        error_count = 0
        
        print(f"Converting {input_file} -> {output_file}")
        
        with open(input_file, 'r', encoding='utf-8') as infile, \
            open(output_file, 'w', encoding='utf-8') as outfile:
            
            for line_num, line in enumerate(infile, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    # Parse the input format
                    data = json.loads(line)
                    
                    # Validate input format - check for system field at root level
                    if "system" not in data:
                        print(f"Warning: Line {line_num} - Missing 'system' field")
                        error_count += 1
                        continue
                    
                    if "messages" not in data or not isinstance(data["messages"], list):
                        print(f"Warning: Line {line_num} - Invalid messages format")
                        error_count += 1
                        continue
                    
                    # Extract system prompt from root level
                    system_content = data.get("system", [])
                    if not isinstance(system_content, list) or len(system_content) != 1:
                        print(f"Warning: Line {line_num} - Invalid system content format")
                        error_count += 1
                        continue
                    
                    system_text = system_content[0].get("text", "")
                    
                    # Now we expect only 2 messages: user and assistant
                    messages = data["messages"]
                    if len(messages) != 2:
                        print(f"Warning: Line {line_num} - Expected 2 messages (user, assistant), got {len(messages)}")
                        error_count += 1
                        continue
                    
                    # Extract user message
                    user_msg = messages[0]
                    if user_msg.get("role") != "user":
                        print(f"Warning: Line {line_num} - First message is not user role")
                        error_count += 1
                        continue
                    
                    user_content = user_msg.get("content", [])
                    if not isinstance(user_content, list) or len(user_content) != 1:
                        print(f"Warning: Line {line_num} - Invalid user content format")
                        error_count += 1
                        continue
                    
                    user_text = user_content[0].get("text", "")
                    
                    # Extract assistant message
                    assistant_msg = messages[1]
                    if assistant_msg.get("role") != "assistant":
                        print(f"Warning: Line {line_num} - Second message is not assistant role")
                        error_count += 1
                        continue
                    
                    assistant_content = assistant_msg.get("content", [])
                    if not isinstance(assistant_content, list) or len(assistant_content) != 1:
                        print(f"Warning: Line {line_num} - Invalid assistant content format")
                        error_count += 1
                        continue
                    
                    assistant_text = assistant_content[0].get("text", "")
                    
                    # Create new flat format
                    flat_data = {
                        "system": system_text,
                        "query": user_text,
                        "response": assistant_text
                    }
                    
                    # Write converted format
                    outfile.write(json.dumps(flat_data) + '\n')
                    converted_count += 1
                    
                except json.JSONDecodeError as e:
                    print(f"Error: Line {line_num} - Invalid JSON: {e}")
                    error_count += 1
                    continue
                except Exception as e:
                    print(f"Error: Line {line_num} - Unexpected error: {e}")
                    error_count += 1
                    continue
        
        print(f"Conversion complete: {converted_count} examples converted, {error_count} errors")    
    
    input_path = Path(input_path)
    
    if input_path.is_file():
        # Single file conversion
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_flat{input_path.suffix}"
        
        convert_single_file(input_path, output_path)
        
    elif input_path.is_dir():
        # Directory conversion
        jsonl_files = list(input_path.glob("*.jsonl"))
        
        for file_path in jsonl_files:
            if output_path is None:
                out_file = file_path.parent / f"{file_path.stem}_flat{file_path.suffix}"
            else:
                out_dir = Path(output_path)
                out_dir.mkdir(exist_ok=True)
                out_file = out_dir / f"{file_path.stem}_flat{file_path.suffix}"
            
            convert_single_file(file_path, out_file)
    
    else:
        raise ValueError(f"Path does not exist: {input_path}")
