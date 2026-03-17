"""Shared utilities for W2 Form OCR Fine-tuning with Amazon Nova Lite.

Used across the notebook pipeline:
  01 - Base Model Evaluation
  02 - Data Preparation
  03 - Fine-tuning on Bedrock
  04 - Deployment on Bedrock
  05 - Custom Model Evaluation
"""

import boto3
import copy
import io
import json
import re
import time

import numpy as np
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REGION = "us-east-1"

# JSON Schema for W2 structured extraction (following JSON Schema spec as
# recommended by the Nova KIE documentation).
W2_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "employee": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Box e: Employee full name",
                },
                "address": {
                    "type": "string",
                    "description": "Box e: Street address, city state zip",
                },
                "socialSecurityNumber": {
                    "type": "string",
                    "description": "Box a: SSN in XXX-XX-XXXX format",
                },
            },
            "required": ["name", "address", "socialSecurityNumber"],
        },
        "employer": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Box c: Employer name",
                },
                "ein": {
                    "type": "string",
                    "description": "Box b: EIN in XX-XXXXXXX format",
                },
                "address": {
                    "type": "string",
                    "description": "Box c: Street address, city state zip",
                },
            },
            "required": ["name", "ein", "address"],
        },
        "earnings": {
            "type": "object",
            "properties": {
                "wages": {
                    "type": "number",
                    "description": "Box 1: Wages, tips, other compensation",
                },
                "socialSecurityWages": {
                    "type": "number",
                    "description": "Box 3: Social security wages",
                },
                "medicareWagesAndTips": {
                    "type": "number",
                    "description": "Box 5: Medicare wages and tips",
                },
                "federalIncomeTaxWithheld": {
                    "type": "number",
                    "description": "Box 2: Federal income tax withheld",
                },
                "stateIncomeTax": {
                    "type": "number",
                    "description": "Sum of Box 17 across all states",
                },
                "localWagesTips": {
                    "type": "number",
                    "description": "Box 18 for first state listed",
                },
                "localIncomeTax": {
                    "type": "number",
                    "description": "Box 19 for first state listed",
                },
            },
            "required": [
                "wages",
                "socialSecurityWages",
                "medicareWagesAndTips",
                "federalIncomeTaxWithheld",
                "stateIncomeTax",
                "localWagesTips",
                "localIncomeTax",
            ],
        },
        "benefits": {
            "type": "object",
            "properties": {
                "dependentCareBenefits": {
                    "type": "number",
                    "description": "Box 10: Dependent care benefits",
                },
                "nonqualifiedPlans": {
                    "type": "number",
                    "description": "Box 11: Nonqualified plans",
                },
            },
            "required": ["dependentCareBenefits", "nonqualifiedPlans"],
        },
        "multiStateEmployment": {
            "type": "object",
            "description": "Keyed by two-letter state abbreviation from Box 15",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "localWagesTips": {
                        "type": "number",
                        "description": "Box 18: Local wages/tips",
                    },
                    "localIncomeTax": {
                        "type": "number",
                        "description": "Box 19: Local income tax",
                    },
                    "localityName": {
                        "type": "string",
                        "description": "Box 20: Locality name",
                    },
                },
                "required": ["localWagesTips", "localIncomeTax", "localityName"],
            },
        },
    },
    "required": [
        "employee",
        "employer",
        "earnings",
        "benefits",
        "multiStateEmployment",
    ],
}

TEXT_PROMPT = (
    "Given the image representation of a document, extract information "
    "in JSON format according to the given schema. Follow these guidelines:\n"
    "- Ensure that every field is populated, provided the document includes "
    "the corresponding value. Only use null when the value is absent from "
    "the document.\n"
    "- Be precise with numerical values -- extract exact dollar amounts and "
    "tax figures as shown on the form.\n"
    "- For stateIncomeTax, provide the sum of state income tax across all "
    "states (Box 17).\n"
    "- For multiStateEmployment, list each state using its two-letter "
    "abbreviation as the key.\n\n"
    "JSON Schema:\n"
    + json.dumps(W2_JSON_SCHEMA, indent=2)
)


# ---------------------------------------------------------------------------
# AWS Setup
# ---------------------------------------------------------------------------


def get_aws_clients(region=REGION):
    """Initialize and return commonly used AWS clients."""
    session = boto3.session.Session(region_name=region)
    sts = session.client("sts")
    account_id = sts.get_caller_identity()["Account"]
    return {
        "session": session,
        "s3": session.client("s3"),
        "sts": sts,
        "bedrock": session.client("bedrock"),
        "bedrock_runtime": session.client("bedrock-runtime"),
        "account_id": account_id,
    }


def create_s3_bucket(s3_client, bucket_name, region=REGION):
    """Create an S3 bucket, handling region-specific creation."""
    try:
        if region == "us-east-1":
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        print(f"Bucket {bucket_name} created successfully")
    except s3_client.exceptions.BucketAlreadyExists:
        print(f"Bucket {bucket_name} already exists")
    except s3_client.exceptions.BucketAlreadyOwnedByYou:
        print(f"Bucket {bucket_name} already owned by you")
    except Exception as e:
        print(f"Error creating bucket: {e}")


# ---------------------------------------------------------------------------
# Data Processing
# ---------------------------------------------------------------------------


def transform_schema(original):
    """Transform raw W2 ground truth data into structured JSON format."""
    employee = {
        "name": original["box_e_employee_name"],
        "address": (
            f"{original['box_e_employee_street_address']}, "
            f"{original['box_e_employee_city_state_zip']}"
        ),
        "socialSecurityNumber": original["box_a_employee_ssn"],
    }
    employer = {
        "name": original["box_c_employer_name"],
        "ein": original["box_b_employer_identification_number"],
        "address": (
            f"{original['box_c_employer_street_address']}, "
            f"{original['box_c_employer_city_state_zip']}"
        ),
    }
    earnings = {
        "wages": original["box_1_wages"],
        "socialSecurityWages": original["box_3_social_security_wages"],
        "medicareWagesAndTips": original["box_5_medicare_wages"],
        "federalIncomeTaxWithheld": original["box_2_federal_tax_withheld"],
        "stateIncomeTax": (
            original["box_17_1_state_income_tax"]
            + original["box_17_2_state_income_tax"]
        ),
        "localWagesTips": original["box_18_1_local_wages"],
        "localIncomeTax": original["box_19_1_local_income_tax"],
    }
    benefits = {
        "dependentCareBenefits": original["box_10_dependent_care_benefits"],
        "nonqualifiedPlans": original["box_11_nonqualified_plans"],
    }
    multi_state = {
        original["box_15_1_state"]: {
            "localWagesTips": original["box_18_1_local_wages"],
            "localIncomeTax": original["box_19_1_local_income_tax"],
            "localityName": original["box_20_1_locality"],
        },
        original["box_15_2_state"]: {
            "localWagesTips": original["box_18_2_local_wages"],
            "localIncomeTax": original["box_19_2_local_income_tax"],
            "localityName": original["box_20_2_locality"],
        },
    }
    return {
        "employee": employee,
        "employer": employer,
        "earnings": earnings,
        "benefits": benefits,
        "multiStateEmployment": multi_state,
    }


def upload_images_to_s3(s3_client, dataset, bucket_name, subset):
    """Upload dataset images to S3 and return metadata with S3 paths."""
    print(f"Uploading {subset} images to S3...")
    s3_paths = []
    for i, item in enumerate(tqdm(dataset)):
        try:
            image = item["image"]
            fmt = image.format if hasattr(image, "format") else "jpeg"
            with io.BytesIO() as buf:
                image.save(buf, format=fmt)
                image_bytes = buf.getvalue()
            s3_key = f"ocr_images/{subset}/img_{i}.{fmt.lower()}"
            s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=image_bytes)
            s3_paths.append(
                {
                    "index": i,
                    "s3_uri": f"s3://{bucket_name}/{s3_key}",
                    "gt": item["ground_truth"],
                }
            )
        except Exception as e:
            print(f"Error uploading image {i}: {e}")
    return s3_paths


def create_jsonl_entry(item, s3_uri, account_id):
    """Create a single JSONL entry in Bedrock conversation schema format."""
    gt = transform_schema(item["gt_parse"])
    return {
        "schemaVersion": "bedrock-conversation-2024",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "image": {
                            "format": "png",
                            "source": {
                                "s3Location": {
                                    "uri": s3_uri,
                                    "bucketOwner": account_id,
                                }
                            },
                        }
                    },
                    {"text": TEXT_PROMPT},
                ],
            },
            {
                "role": "assistant",
                "content": [{"text": f"```json\n{json.dumps(gt)}\n```"}],
            },
        ],
    }


def prepare_dataset_jsonl(s3_paths, output_file, account_id):
    """Write JSONL file from S3 path metadata for Bedrock fine-tuning."""
    with open(output_file, "w") as f:
        for item in s3_paths:
            entry = create_jsonl_entry(
                json.loads(item["gt"]), item["s3_uri"], account_id
            )
            f.write(json.dumps(entry) + "\n")
    print(f"Created {output_file} with {len(s3_paths)} samples")


def build_test_data_in_memory(s3_paths, account_id):
    """Build test data entries in memory (same format as JSONL file entries)."""
    entries = []
    for item in s3_paths:
        entry = create_jsonl_entry(
            json.loads(item["gt"]), item["s3_uri"], account_id
        )
        entries.append(entry)
    return entries


# ---------------------------------------------------------------------------
# IAM
# ---------------------------------------------------------------------------


def create_iam_resources(session, account_id, bucket_name, region=REGION):
    """Create IAM role and policy for Bedrock fine-tuning.

    Returns (role_arn, role_name, policy_arn).
    """
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": account_id},
                    "ArnLike": {
                        "aws:SourceArn": (
                            f"arn:aws:bedrock:{region}:{account_id}"
                            ":model-customization-job/*"
                        )
                    },
                },
            }
        ],
    }
    access_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}",
                    f"arn:aws:s3:::{bucket_name}/*",
                ],
            }
        ],
    }

    iam = session.client("iam")
    ts = int(time.time())
    role_name = f"NovaVisionFineTuningRole-{ts}"
    policy_name = f"NovaVisionFineTuningPolicy-{ts}"

    try:
        resp = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role for fine-tuning Nova vision model with Amazon Bedrock",
        )
        role_arn = resp["Role"]["Arn"]
        print(f"Created role: {role_arn}")

        resp = iam.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(access_policy),
        )
        policy_arn = resp["Policy"]["Arn"]
        print(f"Created policy: {policy_arn}")

        iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        print("Attached policy to role")

        print("Waiting for IAM role to propagate...")
        time.sleep(10)
        return role_arn, role_name, policy_arn
    except Exception as e:
        print(f"Error creating IAM resources: {e}")
        return None, None, None


# ---------------------------------------------------------------------------
# Inference Helpers
# ---------------------------------------------------------------------------


def build_inference_messages(s3_uri, account_id, prefill_json=False):
    """Build the messages list for Bedrock converse API.

    If prefill_json=True, appends an assistant turn with '```json' so the
    model continues generating the JSON body directly
    (use with stopSequences=["```"]).
    """
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "image": {
                        "format": "png",
                        "source": {
                            "s3Location": {
                                "uri": s3_uri,
                                "bucketOwner": account_id,
                            }
                        },
                    }
                },
                {"text": TEXT_PROMPT},
            ],
        }
    ]
    if prefill_json:
        messages.append(
            {"role": "assistant", "content": [{"text": "```json"}]}
        )
    return messages


def parse_json_from_markdown(text):
    """Extract and parse JSON from markdown code fences."""
    match = re.search(r"```json\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if not match:
        return None
    return json.loads(match.group(1))


# ---------------------------------------------------------------------------
# Fine-tuning
# ---------------------------------------------------------------------------


def check_job_status(bedrock_client, job_arn):
    """Return the current status of a Bedrock model customization job."""
    resp = bedrock_client.get_model_customization_job(jobIdentifier=job_arn)
    return resp["status"]


def download_training_metrics(
    s3_client, bucket_name, job_arn, local_path="train_metrics.csv"
):
    """Download step-wise training metrics CSV from S3."""
    job_id = job_arn.split("/")[-1]
    s3_key = (
        f"output/model-customization-job-{job_id}"
        "/training_artifacts/step_wise_training_metrics.csv"
    )
    try:
        s3_client.download_file(bucket_name, s3_key, local_path)
        print("Metrics downloaded successfully")
        return local_path
    except Exception as e:
        print(f"Error downloading metrics: {e}")
        return None


def plot_training_metrics(metrics_file):
    """Plot training loss from the downloaded metrics CSV."""
    import matplotlib.pyplot as plt
    import pandas as pd

    data = pd.read_csv(metrics_file)
    by_step = data.groupby("step_number").mean()
    plt.figure(figsize=(10, 6))
    plt.plot(by_step.index, by_step.training_loss, label="Training")
    plt.title("Training Loss")
    plt.ylabel("Loss")
    plt.xlabel("Step")
    plt.legend()
    plt.grid(True)
    plt.show()


# ---------------------------------------------------------------------------
# Deployment
# ---------------------------------------------------------------------------


def create_model_deployment(bedrock_client, custom_model_arn):
    """Create an on-demand inferencing deployment for a custom model."""
    try:
        print(f"Creating on-demand deployment for model: {custom_model_arn}")
        name = f"nova-ocr-deployment-{time.strftime('%Y%m%d-%H%M%S')}"
        resp = bedrock_client.create_custom_model_deployment(
            modelArn=custom_model_arn,
            modelDeploymentName=name,
            description=f"On-demand deployment for {custom_model_arn}",
        )
        arn = resp.get("customModelDeploymentArn")
        print(f"Deployment ARN: {arn}")
        return arn
    except Exception as e:
        print(f"Error creating deployment: {e}")
        return None


def check_deployment_status(bedrock_client, deployment_arn):
    """Return the current status of a custom model deployment."""
    try:
        resp = bedrock_client.get_custom_model_deployment(
            customModelDeploymentIdentifier=deployment_arn
        )
        status = resp.get("status")
        print(f"Deployment status: {status}")
        return status
    except Exception as e:
        print(f"Error checking deployment status: {e}")
        return None


def wait_for_deployment(
    bedrock_client, deployment_arn, max_wait=3600, interval=60
):
    """Poll deployment status until Active, Failed, or timeout."""
    start = time.time()
    print(f"Waiting for deployment (max {max_wait / 60:.0f} min)...")
    while time.time() - start < max_wait:
        status = check_deployment_status(bedrock_client, deployment_arn)
        if status == "Active":
            elapsed = (time.time() - start) / 60
            print(f"\nDeployment active after {elapsed:.1f} minutes")
            return True
        if status == "Failed":
            print("\nDeployment failed")
            return False
        time.sleep(interval)
    print(f"\nTimed out after {max_wait / 60:.0f} minutes")
    return False


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def flatten_dict(d, parent_key="", sep="_"):
    """Flatten a nested dictionary into a single-level dict with compound keys."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def evaluate_prediction(gt, pred):
    """Compare a prediction against ground truth, returning accuracy and errors."""
    flat_gt = flatten_dict(gt)
    flat_pred = flatten_dict(pred)
    all_keys = set(flat_gt.keys()) | set(flat_pred.keys())
    correct = 0
    total = 0
    errors = {}

    for key in all_keys:
        total += 1
        if key in flat_gt and key in flat_pred:
            gt_val = flat_gt[key]
            pred_val = flat_pred[key]
            if isinstance(gt_val, (int, float)) and isinstance(
                pred_val, (int, float)
            ):
                if abs(gt_val) > 0:
                    pct_error = (
                        abs(gt_val - pred_val) / abs(gt_val) * 100
                    )
                    if pct_error < 0.1:
                        correct += 1
                    else:
                        errors[key] = (gt_val, pred_val, pct_error)
                else:
                    if abs(pred_val) < 0.1:
                        correct += 1
                    else:
                        errors[key] = (gt_val, pred_val, float("inf"))
            elif gt_val == pred_val:
                correct += 1
            else:
                errors[key] = (gt_val, pred_val, "mismatch")
        else:
            errors[key] = (
                flat_gt.get(key),
                flat_pred.get(key),
                "missing" if key in flat_gt else "extra",
            )

    return {
        "accuracy": correct / total if total > 0 else 0,
        "correct": correct,
        "total": total,
        "errors": errors,
    }


def get_field_category(field):
    """Map a flattened field name to its category."""
    if field.startswith("employee"):
        return "Employee Information"
    elif field.startswith("employer"):
        return "Employer Information"
    elif field.startswith("earnings"):
        return "Earnings"
    elif field.startswith("benefits"):
        return "Benefits"
    elif field.startswith("multiStateEmployment"):
        return "Multi-State Employment"
    return "Other"


def reorder_content(entry):
    """Reorder message content so images come before text."""
    new_entry = copy.deepcopy(entry)
    if "content" in new_entry and isinstance(new_entry["content"], list):
        images = [i for i in new_entry["content"] if "image" in i]
        texts = [i for i in new_entry["content"] if "text" in i]
        new_entry["content"] = images + texts
    return new_entry


def evaluate_model_on_test_data(bedrock_runtime, test_data, num_samples, model_id):
    """Run evaluation on test data and return accuracy metrics."""
    np.random.seed(42)
    num_samples = min(num_samples, len(test_data))
    sample_indices = np.random.choice(len(test_data), num_samples, replace=False)

    results = []
    field_categories = {
        "Employee Information": {"correct": 0, "total": 0},
        "Employer Information": {"correct": 0, "total": 0},
        "Earnings": {"correct": 0, "total": 0},
        "Benefits": {"correct": 0, "total": 0},
        "Multi-State Employment": {"correct": 0, "total": 0},
        "Other": {"correct": 0, "total": 0},
    }
    numerical_errors = []
    parse_failures = 0

    for i in tqdm(sample_indices, desc="Evaluating model"):
        test_sample = test_data[i]
        messages = [reorder_content(entry) for entry in test_sample["messages"][:1]]
        # messages.append({"role": "assistant", "content": [{"text": "```json"}]})

        # Parse ground truth
        match = re.search(
            r"```json\n(.*?)\n```",
            test_sample["messages"][1]["content"][0]["text"],
            re.DOTALL,
        )
        if not match:
            continue
        gt = json.loads(match.group(1))

        # Run inference
        response = bedrock_runtime.converse(
            modelId=model_id,
            messages=messages,
            inferenceConfig={
                "maxTokens": 5000,
                "temperature": 0.0,
            },
        )
        prediction_text = response["output"]["message"]["content"][0]["text"]

        # Attempt to parse model output as JSON
        try:
            prediction = parse_json_from_markdown(prediction_text)
        except (json.JSONDecodeError, ValueError, TypeError):
            prediction = None

        if prediction is None:
            # Record parse failure -- all GT fields count as wrong
            parse_failures += 1
            flat_gt = flatten_dict(gt)
            results.append(
                {
                    "index": int(i),
                    "accuracy": 0.0,
                    "correct": 0,
                    "total": len(flat_gt),
                    "errors": {
                        k: (v, None, "parse_failure")
                        for k, v in flat_gt.items()
                    },
                    "parse_success": False,
                }
            )
            for key in flat_gt:
                cat = get_field_category(key)
                field_categories[cat]["total"] += 1
            continue

        # Evaluate field-level accuracy
        eval_result = evaluate_prediction(gt, prediction)
        results.append(
            {
                "index": int(i),
                "accuracy": eval_result["accuracy"],
                "correct": eval_result["correct"],
                "total": eval_result["total"],
                "errors": eval_result["errors"],
                "parse_success": True,
            }
        )

        # Update category stats
        flat_gt = flatten_dict(gt)
        for key in flat_gt:
            cat = get_field_category(key)
            field_categories[cat]["total"] += 1
            if key not in eval_result["errors"]:
                field_categories[cat]["correct"] += 1

        # Collect numerical errors
        for key, (gt_val, pred_val, error) in eval_result["errors"].items():
            if isinstance(error, (int, float)) and error != float("inf"):
                numerical_errors.append(
                    {
                        "field": key,
                        "gt": gt_val,
                        "pred": pred_val,
                        "error_pct": error,
                        "category": get_field_category(key),
                    }
                )

    total_correct = sum(r["correct"] for r in results)
    total_fields = sum(r["total"] for r in results)
    overall_accuracy = total_correct / total_fields if total_fields > 0 else 0

    category_accuracies = {
        cat: stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        for cat, stats in field_categories.items()
    }

    num_evaluated = len(results)
    parse_successes = num_evaluated - parse_failures

    return {
        "results": results,
        "overall_accuracy": overall_accuracy,
        "category_accuracies": category_accuracies,
        "numerical_errors": numerical_errors,
        "structured_output": {
            "total": num_evaluated,
            "parse_successes": parse_successes,
            "parse_failures": parse_failures,
            "parse_success_rate": (
                parse_successes / num_evaluated if num_evaluated > 0 else 0
            ),
        },
    }


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def clean_up(
    session, bedrock_client, deployment_arn=None, role_name=None, policy_arn=None
):
    """Delete deployment and IAM resources."""
    print("Cleaning up resources...")

    if deployment_arn:
        try:
            print(f"Deleting deployment: {deployment_arn}...")
            bedrock_client.delete_custom_model_deployment(
                customModelDeploymentIdentifier=deployment_arn
            )
            print("Deployment deletion initiated")
        except Exception as e:
            print(f"Error deleting deployment: {e}")

    if role_name and policy_arn:
        iam = session.client("iam")
        try:
            print("Detaching policy from role...")
            iam.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
            print("Deleting policy...")
            iam.delete_policy(PolicyArn=policy_arn)
            print("Deleting role...")
            iam.delete_role(RoleName=role_name)
            print("IAM resources cleaned up")
        except Exception as e:
            print(f"Error cleaning up IAM resources: {e}")

    print("Cleanup completed")
