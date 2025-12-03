import time

def generate_2_0(
    client,
    model_id,
    messages,
    system_prompt=None,
    tools=None,
    temperature=0.3,
    max_tokens=4096,
    top_p=0.9,
    max_retries=1,
):
    """
    Generate response using the model with proper tokenization and retry mechanism

    Parameters:
        model_id (str): ID of the model to use
        messages (list): List of message dictionaries with 'role' and 'content'
        system_prompt (str, optional): System prompt to guide the model
        tools (dict, optional): Tool configuration for the model
        temperature (float): Controls randomness in generation (0.0-1.0)
        max_tokens (int): Maximum number of tokens to generate
        top_p (float): Nucleus sampling parameter (0.0-1.0)
        max_retries (int): Maximum number of retry attempts

    Returns:
        dict: Model response containing generated text and metadata
    """
    # Prepare base parameters for the API call
    kwargs = {
        "inferenceConfig": {
            "temperature": temperature,
            "maxTokens": max_tokens,
            "topP": top_p,
        },
    }

    # Add optional parameters if provided
    if tools:
        kwargs["toolConfig"] = tools
    if system_prompt:
        kwargs["system"] = [{"text": system_prompt}]

    # Retry logic
    for attempt in range(max_retries):
        try:
            return client.converse(modelId=model_id, messages=messages, **kwargs)
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                print("Max retries reached. Unable to get response.")
                print(str(e))
                return None