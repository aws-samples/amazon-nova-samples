import sys
import warnings
import logging
import sagemaker
from sagemaker.huggingface import HuggingFaceModel, get_huggingface_llm_image_uri
from sagemaker.utils import name_from_base
from sagemaker import get_execution_role

warnings.filterwarnings('ignore')
logging.getLogger('sagemaker').setLevel(logging.ERROR)

if len(sys.argv) < 2:
    print("Usage: python deploy_model_arg.py <model_name>")
    sys.exit(1)

model_name = sys.argv[1]

llm_image = get_huggingface_llm_image_uri("huggingface", version="3.0.1")
role = get_execution_role()

hub = {
    'HF_TASK': 'text-generation', 
    'HF_MODEL_ID': model_name
}

model_for_deployment = HuggingFaceModel(
    role=role,
    env=hub,
    image_uri=llm_image,
)

endpoint_name = name_from_base(model_name.split('/')[-1].lower().replace('.', ''))

model_for_deployment.deploy(
    endpoint_name=endpoint_name,
    initial_instance_count=1,
    instance_type="ml.g5.12xlarge",
    container_startup_health_check_timeout=300,
    routing_config={"RoutingStrategy": sagemaker.enums.RoutingStrategy.LEAST_OUTSTANDING_REQUESTS}
)

print(f"Model {model_name} deployed to endpoint: {endpoint_name}")
