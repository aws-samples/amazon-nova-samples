"""
Preprocessing Utilities for AI Assistant Conversation Data

This module provides utilities for preprocessing conversation data between users and AI assistants.
It focuses on converting data from GlaiveAI format to Standard format, handling tool calls,
and ensuring proper message structure.

The module includes functions for:
- Converting GlaiveAI formatted data to Standard format
- Parsing chat strings into structured message lists
- Handling tool calls and responses
- Filtering invalid or malformed conversation entries

https://github.com/anyscale/templates/blob/main/templates/fine-tune-llm_v2/end-to-end-examples/fine-tune-function-calling/fc_utils/preprocessing.py
"""

from typing import Any, Dict, List, Optional, Tuple
from datasets import Dataset
import re
import json
import logging
import uuid

from utils.dataset_format import (
    GLAIVEAI_SYSTEM_NO_TOOLS,
    GLAIVEAI_SYSTEM_WITH_TOOLS,
    GLAIVEAI_TOOL_CALL_INDICATORS,
    GLAIVEAI_TOOL_CALL_PREFIX,
    GLAIVEAI_EOS,
    DEFAULT_SYSTEM_PROMPT,
    IndicatorTags,
    GlaiveAIRoleTags,
    MessageType,
    ToolCallType,
    DatasetFormat,
    check_tool_calls_format,
)


class FunctionCallFormatError(Exception):
    """Raised when a function call is expected but not found/ in a wrong format in the assistant response."""

    pass


class FunctionResponseFormatError(Exception):
    """Raised when a function response is not found/ in a wrong format in the given content."""

    pass


class PatternNotFoundError(Exception):
    """Raised when no content is not found based on the given string and tags."""

    pass


class FunctionFormatError(Exception):
    """Raised when function definition is in the wrong format in the given string."""

    pass


class InvalidSystemPromptError(Exception):
    """Raised when an invalid system prompt is found."""

    pass


class InvalidRoleError(Exception):
    """Raised when an invalid role is found in a message."""

    pass


class TagsNotFoundError(Exception):
    """Raised when none of the expected tags are found in the chat string."""

    pass


def _extract_functions_from_system_msg_glaive(system_str: str) -> List[Dict[str, Any]]:
    """
    Extract function definitions from a GlaiveAI system message.

    Args:
        system_str: The system message string containing function definitions

    Returns:
        List of function definitions in Standard tools format

    Raises:
        FunctionFormatError: If the function definitions are not in valid JSON format
    """
    # Extracting the functions using regex
    functions_match = re.findall(r"\{.*?\}(?=\s*\{|\s*$)", system_str, re.DOTALL)
    functions = []

    for fn in functions_match:
        try:
            # Convert string representation of dictionary to actual dictionary
            fn_dict = json.loads(fn)
            functions.append(fn_dict)
        except json.JSONDecodeError:
            # In case the string is not a valid JSON, raise an error
            raise FunctionFormatError(
                f"Tool list not in the correct format in : {system_str}"
            )

    # Some functions may not have parameters. Fix them
    for fn in functions:
        if not fn["parameters"]:
            fn["parameters"] = {
                "type": "object",
                "properties": {},
                "required": [],
            }
    # Bring it into the Standard tools format
    functions = [{"type": "function", "function": fn} for fn in functions]
    return functions


def _glaive_to_standard_format(example: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a single example from GlaiveAI format to Standard format.

    Args:
        example: Dictionary containing 'system' and 'chat' keys in GlaiveAI format

    Returns:
        Dictionary with 'messages' and 'tools' keys in Standard format

    Raises:
        InvalidSystemPromptError: If the system prompt doesn't match expected formats
    """
    messages = []
    tools = None
    if GLAIVEAI_SYSTEM_WITH_TOOLS in example["system"]:
        try:
            tools = extract_functions_from_system_msg(
                example["system"], format=DatasetFormat.GLAIVE
            )
        except FunctionFormatError as e:
            logging.info(f"Error processing example {example['system']} : {e}")
            return {"messages": None, "tools": None}
        # Convert to string for compatiblity with PyArrow
        tools = json.dumps(tools)
    elif GLAIVEAI_SYSTEM_NO_TOOLS not in example["system"]:
        # If an unexpected system prompt is found, raise an error to investigate
        raise InvalidSystemPromptError(
            f"System prompt {example['system']} does not match expected prefixes"
        )

    messages.append({"role": "system", "content": DEFAULT_SYSTEM_PROMPT})
    try:
        chat_messages = chat_str_to_messages(example["chat"])
    except (FunctionCallFormatError, TagsNotFoundError, json.JSONDecodeError) as e:
        # For chat data format errors, propagate None types for filtering later
        return {"messages": None, "tools": None}

    messages.extend(chat_messages)
    processed_example = {"messages": messages, "tools": tools}
    return processed_example


def _parse_function_calls_glaive(string: str) -> List[Dict[str, Any]]:
    """
    Parse function calls from a GlaiveAI format string.

    Args:
        string: JSON string containing function calls

    Returns:
        List of parsed function call dictionaries

    Raises:
        json.JSONDecodeError: If the string is not valid JSON
    """
    # Remove single quotes used for the arguments field.
    string = string.replace("'", "")
    # Parse the string into a list of JSONs
    json_list = json.loads(string)
    if isinstance(json_list, dict):
        json_list = [json_list]
    return json_list


def _parse_function_calls_standard(string: str) -> List[Dict[str, Any]]:
    """
    Parse function calls from an Standard format string.

    Args:
        string: JSON string containing function calls

    Returns:
        List of parsed function call dictionaries with arguments parsed as JSON

    Raises:
        json.JSONDecodeError: If the string is not valid JSON
        FunctionCallFormatError: If the function call format is invalid
    """
    # Parse the string into a list of JSONs
    json_list = json.loads(string)
    if isinstance(json_list, dict):
        json_list = [json_list]
    for json_obj in json_list:
        if "function" not in json_obj or "arguments" not in json_obj["function"]:
            raise FunctionCallFormatError(
                f"Function call not in the correct format in : {string}"
            )
        json_obj["function"]["arguments"] = json.loads(
            json_obj["function"]["arguments"]
        )
    return json_list


def combine_multiple_entries(assistant_content: str) -> str:
    """
    Combine multiple assistant entries that may have been split by tool call prefixes.

    Args:
        assistant_content: The assistant's response content

    Returns:
        Combined assistant content with proper tool call formatting
    """
    if (
        assistant_content.startswith(GLAIVEAI_TOOL_CALL_PREFIX)
        or GLAIVEAI_TOOL_CALL_PREFIX not in assistant_content
    ):
        return assistant_content
    else:
        assistant_tag = GlaiveAIRoleTags.ASSISTANT.value
        fn_call_pattern = r"([\s\S]*?){}\s+{}([\s\S]*)".format(
            re.escape(assistant_tag), re.escape(GLAIVEAI_TOOL_CALL_PREFIX)
        )
        function_call_match = re.search(fn_call_pattern, assistant_content, re.DOTALL)
        if function_call_match:
            content1 = function_call_match.group(1).strip()
            content2 = function_call_match.group(2).strip()
            assistant_content = content1 + GLAIVEAI_TOOL_CALL_PREFIX + content2
    return assistant_content


def chat_str_to_messages(chat: str) -> List[MessageType]:
    """
    Convert a chat string with GlaiveAI format tags to a list of structured messages.

    Args:
        chat: String containing the chat conversation with GlaiveAI role tags

    Returns:
        List of message dictionaries in Standard format

    Raises:
        TagsNotFoundError: If no user/assistant/tool messages are found
        FunctionCallFormatError: If function calls are not properly formatted
    """
    user_tag = GlaiveAIRoleTags.USER.value
    assistant_tag = GlaiveAIRoleTags.ASSISTANT.value
    tool_tag = GlaiveAIRoleTags.TOOL.value
    # Regex pattern to extract user, assistant and tool messages.
    tag_pattern = re.compile(
        rf"(?:{user_tag}\s*(?P<user>.*?)\s*(?={assistant_tag}|$)|{assistant_tag}\s*(?P<assistant>.*?)\s*(?={tool_tag}|{user_tag}|$)|{tool_tag}\s*(?P<function_response>.*?)\s*(?={tool_tag}|{assistant_tag}|$))",
        re.DOTALL,
    )

    matches = tag_pattern.finditer(chat)
    # If no matches found, raise an error
    if not matches:
        raise TagsNotFoundError(f"No user/assistant/tool message found in {chat}")
    messages = []
    # Keep track of the tool call ids and function names in the previous assistant response
    previous_tool_calls_info = []
    # Loop through all matches and extract the respective roles and content
    for match in matches:
        if match.group("user"):
            user_content = match.group("user").strip()
            msg = {"role": "user", "content": user_content}
        elif match.group("assistant"):
            assistant_content = match.group("assistant").strip()
            assistant_content = combine_multiple_entries(assistant_content)

            # Glaive dataset is full of single function calls.
            # We extract the function call and place it in the tool_calls field
            standard_fmt_tool_calls = []
            if GLAIVEAI_TOOL_CALL_PREFIX in assistant_content:
                # Get the function calls from the response.
                # We convert to JSON and then back to string to ensure the format is correct
                assistant_content, tool_calls = get_tool_calls_from_response(
                    assistant_content,
                    GLAIVEAI_TOOL_CALL_INDICATORS,
                    format=DatasetFormat.GLAIVE,
                )
                if assistant_content is None:
                    assistant_content = ""
                for i, tool_call in enumerate(tool_calls):
                    # Generate a short UUID for the tool call id
                    tool_id = str(uuid.uuid4())[:9]
                    standard_fmt_tool_call = {
                        "type": "function",
                        "function": {
                            "name": tool_call["name"],
                            # arguments field is stringified with single quotes
                            "arguments": json.dumps(tool_call["arguments"]),
                            "id": tool_id,
                        },
                    }
                    standard_fmt_tool_calls.append(standard_fmt_tool_call)
            # Remove the eos token if present
            assistant_content = assistant_content.replace(GLAIVEAI_EOS, "")
            msg = {
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": standard_fmt_tool_calls,
            }
            previous_tool_calls_info = []
            for i, tool_call in enumerate(standard_fmt_tool_calls):
                tool_call_id = tool_call["function"].get("id")
                if tool_call_id is None or tool_call_id == "":
                    tool_call_id = str(uuid.uuid4())[:9]
                previous_tool_calls_info.append(
                    (tool_call_id, tool_call["function"]["name"])
                )
        elif match.group("function_response"):
            function_response = match.group("function_response").strip()
            role = "tool"
            # Skip this element if no tool call id is found
            if not len(previous_tool_calls_info):
                continue
            tool_call_id, tool_call_name = previous_tool_calls_info.pop(0)
            msg = {
                "role": role,
                "content": function_response,
                "name": tool_call_name,
                "tool_call_id": tool_call_id,
            }
        else:
            # Sometimes, the input can be malformed with no content in the captured group.
            # Example: 'USER: \n'. Skip these entries
            continue
        messages.append(msg)
    return messages


def extract_segment_between_tags(
    string: str, indicator_tags: IndicatorTags
) -> Tuple[Optional[str], str]:
    """
    Extract content between specified tags in a string.

    Args:
        string: The input string to search in
        indicator_tags: IndicatorTags object containing start and end tags

    Returns:
        Tuple containing:
            - Optional prefix before the start tag (None if string starts with start tag)
            - Content between the start and end tags

    Raises:
        PatternNotFoundError: If the tags are not found in the string
    """
    string = string.strip()
    escaped_tags = [re.escape(tag) for tag in indicator_tags]

    if string.startswith(indicator_tags.start):
        pattern = r"{}([\s\S]*?){}".format(*escaped_tags)
        extract_prefix = False
    else:
        pattern = r"([\s\S]*?){}([\s\S]*?){}".format(*escaped_tags)
        extract_prefix = True

    pattern_match = re.search(pattern, string)
    if not pattern_match:
        raise PatternNotFoundError(
            f"No content found in the string {string} with the given tags {indicator_tags}"
        )
    prefix, special_content = None, None
    if extract_prefix:
        prefix = pattern_match.group(1).strip()
        special_content = pattern_match.group(2).strip()
    else:
        prefix = None
        special_content = pattern_match.group(1).strip()
    return prefix, special_content


def extract_functions_from_system_msg(
    system_str: str,
    format: DatasetFormat,
) -> List[Dict[str, Any]]:
    """
    Extract function definitions from a system message based on the dataset format.

    Args:
        system_str: The system message string containing function definitions
        format: The dataset format (GLAIVE)

    Returns:
        List of function definitions in the appropriate format

    Raises:
        NotImplementedError: If the specified format is not supported
    """
    if format == DatasetFormat.GLAIVE:
        return _extract_functions_from_system_msg_glaive(system_str)
    else:
        raise NotImplementedError(
            f"Function extraction for format {format} not implemented"
        )


def get_tool_calls_from_response(
    raw_response: str, tool_call_tags: IndicatorTags, format: DatasetFormat
) -> Tuple[str, List[ToolCallType]]:
    """
    Extract tool calls from an assistant response.

    Args:
        raw_response: The assistant's response text
        tool_call_tags: IndicatorTags object containing start and end tags for tool calls
        format: The dataset format to use for parsing

    Returns:
        Tuple containing:
            - Response text before the tool calls
            - List of parsed tool call objects

    Raises:
        FunctionCallFormatError: If tool calls cannot be found or are in an invalid format
    """
    try:
        response_text, tool_calls_str = extract_segment_between_tags(
            raw_response, tool_call_tags
        )
        tool_calls = parse_function_calls(tool_calls_str, format)
    except (PatternNotFoundError, json.JSONDecodeError) as e:
        # Propagate a custom exception for use later
        raise FunctionCallFormatError(f"Tool calls could not be found : {e}")

    if not check_tool_calls_format(tool_calls, format):
        raise FunctionCallFormatError("Tool call is not in the correct format")
    return response_text, tool_calls


def filter_func(example: Dict[str, Any]) -> bool:
    """
    Filter function to remove invalid conversation examples.

    Args:
        example: Dictionary containing 'messages' key with conversation messages

    Returns:
        bool: True if the example is valid, False otherwise
    """
    messages = example["messages"]
    is_good_entry = True
    j = 0
    while j + 1 < len(messages):
        # Sometimes,a single message has the same assistant response repeated. We remove these entries along with the ones where we have consecutive assistant responses
        if (
            messages[j]["role"] == messages[j + 1]["role"]
            or GlaiveAIRoleTags.ASSISTANT.value in messages[j]["content"]
        ):
            is_good_entry = False
            break

        j += 1
    return is_good_entry


def glaive_to_standard_format(ds: Dataset) -> Dataset:
    """
    Convert a dataset from GlaiveAI format to Standard format.

    Args:
        ds: Dataset in GlaiveAI format

    Returns:
        Dataset in Standard format with invalid entries filtered out
    """
    ds = ds.map(_glaive_to_standard_format)
    ds = ds.filter(lambda x: x["messages"] is not None)
    ds = ds.filter(filter_func)
    return ds


def parse_function_calls(string: str, format: DatasetFormat) -> List[Dict[str, Any]]:
    """
    Parse function calls from a string based on the dataset format.

    Args:
        string: JSON string containing function calls
        format: The dataset format (GLAIVE or other formats use Standard parsing)

    Returns:
        List of parsed function call dictionaries
    """
    if format == DatasetFormat.GLAIVE:
        return _parse_function_calls_glaive(string)
    else:
        return _parse_function_calls_standard(string)


def parse_tool_result(string: str, tool_result_tags: Tuple[str, str]) -> Dict[str, Any]:
    """
    Parse tool result from a string.

    Args:
        string: The string containing tool result
        tool_result_tags: Tuple containing start and end tags for tool result

    Returns:
        Dictionary containing the parsed tool result

    Raises:
        FunctionResponseFormatError: If tool result cannot be found or is not valid JSON
    """
    try:
        _, tool_result_str = extract_segment_between_tags(string, tool_result_tags)
        result = json.loads(tool_result_str)
    except (PatternNotFoundError, json.JSONDecodeError) as e:
        # Propagate a custom exception for use later
        raise FunctionResponseFormatError(f"Tool result could not be found : {e}")
    return result
