from ImageGenChat import ImageGenChat
import time
from datetime import datetime
import os
import json


def measure_malformed_json_rate(
    sample_size,
    model_id,
    turn_memory_count=4,
    region_name="us-east-1",
    max_requests_per_minute=20,
):
    """
    Measure the rate of malformed JSON responses from the ImageGenChat class.

    Args:
        sample_size (int): The number of samples to test.
        model_id (str): The model ID to use.
        turn_memory_count (int): The number of turns to remember.
        region_name (str): The AWS region name.
        max_requests_per_minute (int): The maximum number of requests per minute.

    Returns:
        float: The percentage of malformed JSON responses.
    """

    print(f"Measuring malformed JSON rate with model {model_id}...")

    # Create an instance of ImageGenChat which manages conversation history and
    # user input.
    image_chat = ImageGenChat(
        turn_memory_count=turn_memory_count,
        model_id=model_id,
        region_name=region_name,
    )

    # Generate a sample of malformed JSON responses.
    malformed_json_count = 0
    last_invocation_time = time.time()

    print("\nMeasuring malformed JSON rate...")

    for index in range(sample_size):
        print(f"Sample {index + 1} of {sample_size}")

        # Create a folder name based on the current time.
        folder_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = os.path.join(os.path.dirname(__file__), "output", folder_name)

        user_text = "Create a beach scene"
        try:
            image_chat.process_user_input(user_text=user_text, output_dir=output_dir)
        except json.JSONDecodeError:
            malformed_json_count += 1
        except Exception as e:
            print(f"Unexpected error: {e}")

        # Implement rate limiting
        current_time = time.time()
        elapsed_time = current_time - last_invocation_time
        if elapsed_time < 60 / max_requests_per_minute:
            time.sleep(60 / max_requests_per_minute - elapsed_time)

    # Calculate the percentage of malformed JSON responses.
    malformed_json_rate = (malformed_json_count / sample_size) * 100
    return malformed_json_rate


def main():
    malformed_json_rate = measure_malformed_json_rate(
        sample_size=100, model_id="us.amazon.nova-lite-v1:0", max_requests_per_minute=20
    )
    print(f"Malformed JSON rate: {malformed_json_rate}%")


if __name__ == "__main__":
    main()
