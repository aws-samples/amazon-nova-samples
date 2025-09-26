"""
This script can be used to estimate training times for CPT/PPO/SFT/DPO Nova Customization training
jobs on both Sagemaker HyperPod and SageMaker Training Jobs. To use the script, ensure that you have
your YAML recipe that you anticipate using to start your job.

Run the script by using a command similar to: python get_training_time_estimate.py

Simply walk through the prompts to receive your training time estimate. Please note that these estimates
are approximate projections and should not be interpreted as definitive training durations. Actual training
times may vary significantly based on multiple factors. For more accurate estimates, please check CloudWatch
logs while your training job is running.
"""

import os
import yaml

# Baselines adapted from performing regression on internal stress tests
BASELINES_BY_TYPE = {
    "cpt": {
        "nova-micro": {"T0": 4.0, "N0": 100000, "P5": 8, "GBS0": 256, "MaxLength": 8192},
        "nova-lite":  {"T0": 4.0, "N0": 100000, "P5": 16, "GBS0": 256, "MaxLength": 8192},
        "nova-pro":   {"T0": 10.0, "N0": 100000, "P5": 24, "GBS0": 256, "MaxLength": 8192},
    },
    "ppo": {
        "nova-micro": {"T0": 19.6, "N0": 15000, "P5": 7, "GBS0": 160, "MaxLength": 8192},
        "nova-lite":  {"T0": 18.6, "N0": 20000, "P5": 7, "GBS0": 160, "MaxLength": 8192},
        "nova-pro":   {"T0": 52.8, "N0": 20000, "P5": 8, "GBS0": 160, "MaxLength": 8192},
    },
    "sft": {
        "nova-micro": {
            "full-rank": {"T0": 0.45, "N0": 5000, "P5": 2, "GBS0": 64, "MaxLength": 48000},
            "lora":      {"T0": 0.45, "N0": 5000, "P5": 2, "GBS0": 64, "MaxLength": 64000}
        },
        "nova-lite": {
            "full-rank": {"T0": 0.5, "N0": 1500, "P5": 4, "GBS0": 64, "MaxLength": 48000},
            # No Lora data exists
        },
        "nova-pro": {
            "full-rank": {"T0": 0.707, "N0": 1500, "P5": 6, "GBS0": 32, "MaxLength": 48000},
            "lora":      {"T0": 0.75, "N0": 2000, "P5": 6, "GBS0": 32, "MaxLength": 64000}
        }
    },
    "dpo": {
        "nova-micro": {
            "full-rank": {"T0": 0.46, "N0": 10500, "P5": 2, "GBS0": 256, "MaxLength": 24000},
            "lora":      {"T0": 0.46, "N0": 10500, "P5": 2, "GBS0": 256, "MaxLength": 24000}
        },
        "nova-lite": {
            "full-rank": {"T0": 0.66, "N0": 20000, "P5": 4, "GBS0": 256, "MaxLength": 16000},
            "lora":      {"T0": 0.75, "N0": 20000, "P5": 4, "GBS0": 256, "MaxLength": 16000}
        },
        "nova-pro": {
            "full-rank": {"T0": 1.08, "N0": 20000, "P5": 4, "GBS0": 128, "MaxLength": 16000},
            "lora":      {"T0": 1.5,  "N0": 20000, "P5": 4, "GBS0": 128, "MaxLength": 16000}
        }
    }
}

# Estimate training time (in hours) based on linear scaling assumptions.
def estimate_training_time_hours(
        model_type: str,
        num_samples: int,
        p5_instances: int,
        gbs: int,
        max_length: int,
        training_type: str,
        sub_type: str = None
):
    # Fetch the baseline for the training type and model
    baseline = BASELINES_BY_TYPE[training_type][model_type]

    # If the baseline has subtypes (full-rank, lora, etc.), use the provided sub_type
    if training_type in ["sft", "dpo"]:
        baseline = baseline[sub_type]

    # Perform linear scaling calculation
    return (
            baseline["T0"]
            * (num_samples / baseline["N0"])        # > samples, > time
            * (baseline["P5"] / p5_instances)       # > P5's, < time
            * (baseline["GBS0"] / gbs)              # > gbs, < time
            * (max_length / baseline["MaxLength"])  # > max_length, > time
    )

def retrieve_recipe():
    """Prompt user for YAML file and return parsed content. Keep asking user until a valid yaml path is given"""
    while True:
        yaml_path = input("Enter path to YAML file: ").strip()
        if os.path.isfile(yaml_path):
            break
        print("Invalid file. Please enter a valid YAML file path.")

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    # Sanity check: ensure required keys exist
    if "run" not in data or "replicas" not in data["run"]:
        raise ValueError("YAML missing 'run.replicas' value.")
    if "training_config" not in data or "global_batch_size" not in data["training_config"] or "max_length" not in data["training_config"]:
        raise ValueError("YAML missing 'training_config.global_batch_size' or 'training_config.max_length' values.")

    return data

def select_from_list(prompt: str, options: list):
    """Display numbered list and get user selection."""
    print(prompt)
    for i, option in enumerate(options, start=1):
        print(f"{i}. {option}")
    while True:
        choice = input("Enter the number of your choice: ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        print(f"Invalid choice. Please enter a number between 1 and {len(options)}.")

def format_days_hours_minutes(hours: float):
    """Convert decimal hours to 'Xd Yh Zm'"""
    total_minutes = int(round(hours * 60))
    days = total_minutes // (24 * 60)
    hours_rem = (total_minutes % (24 * 60)) // 60
    minutes = total_minutes % 60

    def pluralize(value, unit):
        return f"{value} {unit}" + ("s" if value != 1 else "")

    parts = []
    if days > 0:
        parts.append(pluralize(days, "day"))
    if hours_rem > 0:
        parts.append(pluralize(hours_rem, "hour"))
    if minutes > 0:
        parts.append(pluralize(minutes, "minute"))

    return " ".join(parts) if parts else "Less than a minute"


def main():
    # Present only training types that have baselines
    training_types = [t for t, models in BASELINES_BY_TYPE.items() if models]

    training_type = select_from_list("Select training type:", training_types)

    # Present only models available for the selected training type
    available_models = list(BASELINES_BY_TYPE[training_type].keys())
    model_type = select_from_list("Select model type:", available_models)


    sub_type = None

    # For SFT & DPO, we must get sub_type
    if training_type in ["sft", "dpo"]:
        model_entry = BASELINES_BY_TYPE[training_type][model_type]
        sub_types = list(model_entry.keys())
        sub_type = select_from_list("Select sub-type:", sub_types)

    # Prompt User for Recipe Location
    recipe = retrieve_recipe()

    # Ask for dataset size, optional
    dataset_input = input("Enter dataset sample size (press Enter to use default 100,000): ").strip()
    if dataset_input == "":
        num_samples = 100000
        dataset_default = True
    else:
        try:
            num_samples = int(dataset_input)
            dataset_default = False
        except ValueError:
            print("Invalid input. Using default 100,000 samples.")
            num_samples = 100000
            dataset_default = True

    p5_instances = recipe["run"]["replicas"]
    gbs = recipe["training_config"]["global_batch_size"]
    max_length = recipe["training_config"]["max_length"]

    # Estimate training time
    estimated_hours = estimate_training_time_hours(
        model_type=model_type,
        num_samples=num_samples,
        p5_instances=p5_instances,
        gbs=gbs,
        max_length=max_length,
        training_type=training_type,
        sub_type=sub_type
    )

    # Format output
    formatted_time = format_days_hours_minutes(estimated_hours)

    # Build descriptive output string
    desc = f"{training_type}, {model_type}"

    if sub_type:
        desc += f", {sub_type}"

    desc += f", {p5_instances} P5s, {gbs} GBS, {max_length} max_length"

    if dataset_default:
        print(f"\nEstimated training time ({desc}, per 100000 samples): {formatted_time}.")
    else:
        print(f"\nEstimated training time ({desc}): {formatted_time}")

    print(
        "Please note that these estimates are approximate projections and should not be interpreted "
        "as definitive training durations. Please monitor CloudWatch logs for more accurate progress and estimates."
    )

if __name__ == "__main__":
    main()
