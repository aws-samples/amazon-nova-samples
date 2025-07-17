import sagemaker
from sagemaker.huggingface import HuggingFaceModel
from sagemaker.huggingface import get_huggingface_llm_image_uri
from sagemaker.utils import name_from_base
from sagemaker import get_execution_role
import boto3

# Deploy Qwen2.5-1.5B-Instruct Model to Sagemaker Endpoint

llm_image = get_huggingface_llm_image_uri(
  "huggingface",
  version="3.0.1"
)


role = get_execution_role()
print(role)

hub = {
    'HF_TASK': 'text-generation', 
    'HF_MODEL_ID': 'Qwen/Qwen2.5-1.5B-Instruct'
}

model_for_deployment = HuggingFaceModel(
    #model_data=s3_location,
    role=role,
    env=hub,
    image_uri=llm_image,
)

endpoint_name = name_from_base("qwen25")

instance_type = "ml.g5.12xlarge"
number_of_gpu = 1
health_check_timeout = 300

model_for_deployment.deploy(
    endpoint_name=endpoint_name,
    initial_instance_count=1,
    instance_type=instance_type,
    container_startup_health_check_timeout=health_check_timeout,
    routing_config = {
        "RoutingStrategy":  sagemaker.enums.RoutingStrategy.LEAST_OUTSTANDING_REQUESTS
    }
)
