from nova_custom_evaluation_sdk.processors.decorators import preprocess, postprocess
from nova_custom_evaluation_sdk.lambda_handler import build_lambda_handler

@preprocess
def preprocessor(event: dict, context) -> dict:
    print(f"Preprocessor Event: {event}")
    data = event.get('data', {})
    return {
        "statusCode": 200,
        "body": {
            "system": data.get("system"),
            "prompt": data.get("prompt", ""),
            "gold": data.get("gold", "")
        }
    }

@postprocess
def postprocessor(event: dict, context) -> dict:
    print(f"Postprocessor Event: {event}")
    # data is already validated and extracted from event
    data = event.get('data', [])
    inference_output = data.get('inference_output', '')
    gold = data.get('gold', '')
    
    metrics = []
    inverted_accuracy = 0 if inference_output.lower() == gold.lower() else 1.0
    metrics.append({
        "metric": "inverted_accuracy_custom",
        "value": inverted_accuracy
    })
    
    # Add more metrics here
    
    response = {
        "statusCode": 200,
        "body": metrics
    }

    print(f"response: {response}")

    return {
        "statusCode": 200,
        "body": metrics
    }

# Build Lambda handler
lambda_handler = build_lambda_handler(
    preprocessor=preprocessor,
    postprocessor=postprocessor
)
