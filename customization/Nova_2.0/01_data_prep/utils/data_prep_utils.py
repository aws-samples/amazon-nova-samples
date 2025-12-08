import json
import re


def clean_prefix(content):
    """Remove prefixes from content, according to Nova data_validator"""
    prefixes = [
        "SYSTEM:",
        "System:",
        "USER:",
        "User:",
        "ASSISTANT:",
        "Assistant:",
        "Bot:",
        "BOT:",
    ]

    # Handle array case (list of content items)
    if hasattr(content, "__iter__") and not isinstance(content, str):
        for i, item in enumerate(content):
            if isinstance(item, dict) and "text" in item:
                text = item["text"]
                if isinstance(text, str):
                    # Clean line by line for multi-line text
                    lines = text.split("\n")
                    cleaned_lines = []
                    for line in lines:
                        cleaned_line = line.strip()
                        for prefix in prefixes:
                            if cleaned_line.startswith(prefix):
                                cleaned_line = cleaned_line[len(prefix) :].strip()
                                break
                        cleaned_lines.append(cleaned_line)
                    item["text"] = "\n".join(cleaned_lines)
        return content

    # Handle string case
    if isinstance(content, str):
        lines = content.split("\n")
        cleaned_lines = []
        for line in lines:
            cleaned_line = line.strip()
            for prefix in prefixes:
                if cleaned_line.startswith(prefix):
                    cleaned_line = cleaned_line[len(prefix) :].strip()
                    break
            cleaned_lines.append(cleaned_line)
        return "\n".join(cleaned_lines)

    return content


def clean_message_list(message_list):
    """Clean message list from None values and convert to list of dicts if needed."""
    if isinstance(message_list, str):
        message_list = json.loads(message_list)

    tmp_cleaned = []
    for msg in message_list:
        new_msg = {}
        for key, value in msg.items():
            if key in ["content"]:
                if value is None or str(value).lower() == "None":
                    continue
            new_msg[key] = value
        tmp_cleaned.append(new_msg)

    cleaned = []
    for item in tmp_cleaned:
        content = item["content"]
        for content_item in content:
            if isinstance(content_item, dict) and "text" in content_item:
                text = clean_numbered_conversation(content_item["text"])
                content_item["text"] = clean_prefix(text)
        cleaned.append({"role": item["role"], "content": content})

    return cleaned


# Additional function to specifically handle the numbered conversation format
def clean_numbered_conversation(text):
    """Clean numbered conversation format like '1. User: ...'"""
    if not isinstance(text, str):
        return text

    # Pattern to match numbered items with User: or Assistant: prefixes
    pattern = r"(\d+\.\s*)(User:|Assistant:)\s*"

    # Replace the pattern, keeping the number but removing the role prefix
    cleaned_text = re.sub(pattern, r"\1", text)

    return cleaned_text

def transform_tool_format(tool):
    """Transform tool from old format to Nova format."""
    if "function" not in tool:
        return tool

    function = tool["function"]
    return {
        "toolSpec": {
            "name": function["name"],
            "description": function["description"],
            "inputSchema": {"json": function["parameters"]},
        }
    }


def prepare_dataset(sample):
    """Prepare dataset in the required format for Nova models"""
    messages = {"system": [], "messages": []}

    # Process tools upfront if they exist
    tools = json.loads(sample["tools"]) if sample.get("tools") else []
    transformed_tools = [transform_tool_format(tool) for tool in tools]

    formatted_text = (
        ""  # Initialize outside the loop to avoid undefined variable issues
    )

    for message in sample["messages"]:
        role = message["role"]

        if role == "system" and tools:
            # Build system message with tools
            system_text = (
                f"{message['content']}\n"
                "You may call one or more functions to assist with the user query.\n\n"
                "You are provided with function signatures within <tools></tools> XML tags:\n"
                "<tools>\n"
                f"{json.dumps({'tools': transformed_tools})}\n"
                "</tools>\n\n"
                "For each function call, return a json object with function name and parameters:\n"
                '{"name": function name, "parameters": dictionary of argument name and its value}'
            )
            messages["system"] = [{"text": system_text.lower()}]

        elif role == "user":
            messages["messages"].append(
                {"role": "user", "content": [{"text": message["content"].lower()}]}
            )

        elif role == "tool":
            formatted_text += message["content"]
            messages["messages"].append(
                {"role": "user", "content": [{"text": formatted_text.lower()}]}
            )

        elif role == "assistant":
            if message.get("tool_calls"):
                # Process tool calls
                tool_calls_text = []
                for tool_call in message["tool_calls"]:
                    function_data = tool_call["function"]
                    arguments = (
                        json.loads(function_data["arguments"])
                        if isinstance(function_data["arguments"], str)
                        else function_data["arguments"]
                    )
                    tool_call_json = {
                        "name": function_data["name"],
                        "parameters": arguments,
                    }
                    tool_calls_text.append(json.dumps(tool_call_json))

                messages["messages"].append(
                    {
                        "role": "assistant",
                        "content": [{"text": "".join(tool_calls_text).lower()}],
                    }
                )
            else:
                messages["messages"].append(
                    {"role": "assistant", "content": [{"text": message["content"].lower()}]}
                )

    # Remove the last message if it's not from assistant
    if messages["messages"] and messages["messages"][-1]["role"] != "assistant":
        messages["messages"].pop()

    return messages

def prepare_dataset_test(sample):
    """Parse sample and format it for validation dataset."""
    # Process tools
    tools = json.loads(sample["tools"]) if sample.get("tools") else []
    transformed_tools = [transform_tool_format(tool) for tool in tools]

    # Initialize result
    result = []
    conversation_history = []

    # Extract system message
    system_content = ""
    for message in sample["messages"]:
        if message["role"] == "system":
            system_content = message["content"]
            if tools:
                system_content += (
                    "\nYou may call one or more functions to assist with the user query.\n\n"
                    "You are provided with function signatures within <tools></tools> XML tags:\n"
                    "<tools>\n"
                    f"{json.dumps({'tools': transformed_tools})}\n"
                    "</tools>\n\n"
                    "For each function call, return a json object with function name and parameters:\n"
                    '{"name": function name, "parameters": dictionary of argument name and its value}'
                )
            break

    # Process conversation turns
    for i, message in enumerate(sample["messages"]):
        if message["role"] == "system":
            continue

        # Add message to conversation history
        if message["role"] == "user":
            conversation_history.append(f"## User: {message['content']}")
        elif message["role"] == "assistant":
            if message.get("tool_calls"):
                # Format tool calls
                target_parts = []
                for tool_call in message["tool_calls"]:
                    function_data = tool_call["function"]
                    arguments = (
                        json.loads(function_data["arguments"])
                        if isinstance(function_data["arguments"], str)
                        else function_data["arguments"]
                    )
                    target_parts.append(
                        json.dumps(
                            {"name": function_data["name"], "parameters": arguments}
                        )
                    )
                target = "".join(target_parts)

                conversation_history.append(f"## Assistant: {target}")
            else:
                conversation_history.append(f"## Assistant: {message['content']}")
        elif message["role"] == "tool":
            conversation_history.append(f"## Function: {message['content']}")

        # Create input-target pair when we have an assistant message
        if message["role"] == "assistant":
            # Input is system message + all previous conversation
            input_text = "\n".join(conversation_history[:-1])

            # Target is the assistant's response
            if message.get("tool_calls"):
                # Format tool calls
                target_parts = []
                for tool_call in message["tool_calls"]:
                    function_data = tool_call["function"]
                    arguments = (
                        json.loads(function_data["arguments"])
                        if isinstance(function_data["arguments"], str)
                        else function_data["arguments"]
                    )
                    target_parts.append(
                        json.dumps(
                            {"name": function_data["name"], "parameters": arguments}
                        )
                    )
                target = "".join(target_parts)
            else:
                target = message["content"]

            result.append({"system": system_content.lower(), "query": input_text.lower(), "response": target.lower()})

    return {"messages": result}

def make_eval_compatible(test_dataset):
    data_list = test_dataset.to_list()

    data = []

    for line in data_list:
            messages = line["messages"]

            for message in messages:
                data.append(message)

    return data
