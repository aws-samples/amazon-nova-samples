import json
import logging
import os

import boto3

# Create logger.
logger = logging.getLogger(__name__)


class ImageGenChat:
    """
    This class handles image geneneration conversation flow and provides
    automatic image prompt enhancement. It maintains conversation history,
    processes user inputs, and formats model responses.

    Params:
        model_id (str): The AWS Bedrock model identifier to use for inference.
        turn_memory_count (int): Number of conversation turns to maintain in memory.
        region_name (str): AWS region for the Bedrock service.
    """

    def __init__(self, model_id, turn_memory_count=4, region_name="us-east-1"):
        self.model_id = model_id
        self.turn_memory_count = turn_memory_count
        self.region_name = region_name

        self.system_prompt = ""

        self.chat_history = []  # Array of user/assistant message objects
        self.bedrock_runtime = boto3.client(
            "bedrock-runtime", region_name=self.region_name
        )

    def process_user_input(self, user_text, output_dir=None):
        # Load the system prompt from a file.
        base_path = os.path.dirname(os.path.abspath(__file__))
        system_prompt_path = os.path.join(base_path, "system_prompt.md")
        with open(system_prompt_path, "r") as file:
            self.system_prompt = file.read()

        system = [{"text": self.system_prompt}]

        # Append the user message to the conversation history.
        self.chat_history.append({"role": "user", "content": [{"text": user_text}]})

        # Temporarily append a partial assistant message to the chat history.
        # This provides a way for us to put words on the model's mouth to help
        # enforce the response style we want.
        messages = [
            *self.chat_history,
            {
                "role": "assistant",
                "content": [{"text": "```json\n"}],
            },
        ]

        # Configure the inference parameters.
        inf_params = {
            "maxTokens": 3000,
            "temperature": 0.5,
            "topP": 0.99,
            "stopSequences": ["```"],
        }

        # Save request details.
        request_params = {
            "modelId": self.model_id,
            "messages": messages,
            "system": system,
            "inferenceConfig": inf_params,
        }

        # Save the request to a file for debugging.
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            request_file_path = os.path.join(
                output_dir, f"{self.model_id}-request.json"
            )
            with open(request_file_path, "w") as f:
                f.write(json.dumps(request_params, indent=2))

        # Invoke the model.
        model_response = self.bedrock_runtime.converse(**request_params)

        # Save the response to a file for debugging.
        if output_dir:
            response_file_path = os.path.join(
                output_dir, f"{self.model_id}-response.json"
            )
            with open(response_file_path, "w") as f:
                f.write(json.dumps(model_response, indent=2))

        response_text = model_response["output"]["message"]["content"][0]["text"]

        # Strip "```" from end of response_text if present.
        if response_text.endswith("```"):
            response_text = response_text[:-3].strip()

        try:
            response_json = json.loads(response_text)

            # Now that we've confirmed a valid JSON response was returned, we
            # can add the full assistant response to the chat history
            # permanently.
            full_assistant_text = f"```json\n{response_text}\n```"
            self.chat_history.append(
                {"role": "assistant", "content": [{"text": full_assistant_text}]}
            )

        except:
            logger.error(f"Error parsing JSON: {response_text}")
            raise

        # Trim from the start of the conversation history to bring it within the
        # desired context memory bounds.
        while len(self.chat_history) > self.turn_memory_count * 2:
            self.chat_history.pop(0)

        return response_json

    def get_chat_history_as_markdown(self):
        """Provides a simplified view of the chat history. Automatically pretty-prints JSON only responses."""

        # Loop through the chat history.
        chat_history_text = ""
        for message in self.chat_history:
            role = message["role"]
            content = message["content"][0]["text"]

            # If the content is JSON, pretty print it.
            try:
                # Strip Markdown JSON fences if present.
                if content.startswith("```json"):
                    content = content[7:-3].strip()

                    # Only treat it as JSON if it starts with a brace.
                    content_json = None
                    if content.startswith("{"):
                        content_json = json.loads(content)
                        # Pretty print the JSON.
                        content = json.dumps(content_json, indent=2)

                        # Re-add JSON fences.
                        content = f"```json\n{content}\n```"
            except:
                pass

            chat_history_text += f"**{role.capitalize()}:**\n{content}\n\n"

        return chat_history_text
