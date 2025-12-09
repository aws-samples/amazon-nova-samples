#!/usr/bin/env python3
import json
import argparse
import subprocess
import sys
from typing import Dict, List, Optional

def run_command(command: str) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, and stderr."""
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr

def describe_cluster(cluster_arn: str, region: str) -> Optional[Dict]:
    """Describe the cluster and return its configuration."""
    cmd = f"aws sagemaker describe-cluster --cluster-name {cluster_arn} --region {region}"
    exit_code, stdout, stderr = run_command(cmd)
    
    if exit_code != 0:
        print(f"Error describing cluster: {stderr}")
        return None
    
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        print("Error parsing cluster configuration")
        return None

def has_rig_setup(cluster_config: Dict) -> bool:
    """Check if cluster has RIG setup."""
    return bool(cluster_config.get("RestrictedInstanceGroups", []))

def get_existing_rig_names(cluster_config: Dict) -> List[str]:
    """Get names of existing RIGs."""
    rigs = cluster_config.get("RestrictedInstanceGroups", [])
    return [rig["InstanceGroupName"] for rig in rigs]

def prompt_yes_no(question: str) -> bool:
    """Prompt user for yes/no answer."""
    while True:
        response = input(f"{question} (y/n): ").lower()
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("Please answer yes or no.")

def prompt_with_default(prompt: str, default: str) -> str:
    """Prompt user for input with a default value."""
    response = input(f"{prompt} [{default}]: ")
    return response if response else default

def create_rig_config(cluster_config: Dict, use_existing: bool = False) -> Dict:
    """Create a new RIG configuration."""
    if use_existing and cluster_config.get("RestrictedInstanceGroups"):
        existing_rig = cluster_config["RestrictedInstanceGroups"][0]
        print("\nUsing values from existing RIG as defaults...")
    else:
        existing_rig = {}

    rig_name = input("\nEnter RIG name (e.g., restricted-instance-group-new): ")
    instance_count = int(input("Enter instance count: "))
    instance_type = prompt_with_default(
        "Enter instance type",
        existing_rig.get("InstanceType", "ml.p5.48xlarge")
    )
    
    # Use existing execution role if available
    execution_role = existing_rig.get("ExecutionRole")
    if not execution_role:
        execution_role = cluster_config["InstanceGroups"][0]["ExecutionRole"]
    
    # Storage configuration
    volume_size = int(prompt_with_default(
        "Enter EBS volume size in GB",
        str(existing_rig.get("InstanceStorageConfigs", [{}])[0].get("EbsVolumeConfig", {}).get("VolumeSizeInGB", 500))
    ))

    # VPC configuration
    if use_existing and existing_rig.get("OverrideVpcConfig"):
        vpc_config = existing_rig["OverrideVpcConfig"]
    else:
        security_group = input("Enter security group ID: ")
        subnet = input("Enter subnet ID: ")
        vpc_config = {
            "SecurityGroupIds": [security_group],
            "Subnets": [subnet]
        }

    # FSx configuration
    fsx_size = int(prompt_with_default(
        "Enter FSx Lustre size in GiB",
        str(existing_rig.get("TrustedEnvironment", {}).get("Config", {}).get("FSxLustreConfig", {}).get("SizeInGiB", 12000))
    ))
    fsx_throughput = int(prompt_with_default(
        "Enter FSx Lustre per unit storage throughput",
        str(existing_rig.get("TrustedEnvironment", {}).get("Config", {}).get("FSxLustreConfig", {}).get("PerUnitStorageThroughput", 125))
    ))

    return {
        "InstanceCount": instance_count,
        "InstanceGroupName": rig_name,
        "InstanceType": instance_type,
        "ExecutionRole": execution_role,
        "ThreadsPerCore": 1,
        "InstanceStorageConfigs": [
            {
                "EbsVolumeConfig": {
                    "VolumeSizeInGB": volume_size
                }
            }
        ],
        "OverrideVpcConfig": vpc_config,
        "TrustedEnvironment": {
            "Config": {
                "FSxLustreConfig": {
                    "SizeInGiB": fsx_size,
                    "PerUnitStorageThroughput": fsx_throughput
                }
            }
        }
    }

def update_cluster_config(cluster_config: Dict, operation: str) -> tuple[Optional[Dict], Optional[List[str]]]:
    """Update cluster configuration based on operation."""
    rigs_to_delete = None

    if operation == "add":
        use_existing = prompt_yes_no("\nDo you want to use values from existing RIG as defaults?")
        new_rig = create_rig_config(cluster_config, use_existing)
        cluster_config["RestrictedInstanceGroups"].append(new_rig)
    
    elif operation == "scale":
        rig_names = get_existing_rig_names(cluster_config)
        if not rig_names:
            print("No RIGs found to scale")
            return None, None
        
        print("\nAvailable RIGs:")
        for i, name in enumerate(rig_names, 1):
            print(f"{i}. {name}")
        
        while True:
            try:
                choice = int(input("\nSelect RIG to scale (enter number): ")) - 1
                if 0 <= choice < len(rig_names):
                    break
                print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a number.")
        
        new_count = int(input("Enter new instance count: "))
        cluster_config["RestrictedInstanceGroups"][choice]["InstanceCount"] = new_count

    elif operation == "delete":
        rig_names = get_existing_rig_names(cluster_config)
        if not rig_names:
            print("No RIGs found to delete")
            return None, None
        
        print("\nAvailable RIGs:")
        for i, name in enumerate(rig_names, 1):
            print(f"{i}. {name}")
        
        while True:
            try:
                choice = int(input("\nSelect RIG to delete (enter number): ")) - 1
                if 0 <= choice < len(rig_names):
                    break
                print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a number.")
        
        rig_to_delete = rig_names[choice]
        cluster_config["RestrictedInstanceGroups"] = [
            rig for rig in cluster_config["RestrictedInstanceGroups"]
            if rig["InstanceGroupName"] != rig_to_delete
        ]
        rigs_to_delete = [rig_to_delete]
    
    return cluster_config, rigs_to_delete

def update_cluster(cluster_arn: str, region: str, config: Dict, rigs_to_delete: List[str] = None):
    """Update the cluster with new configuration."""
    config_file = "updated_cluster_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\nUpdated configuration saved to {config_file}")
    if prompt_yes_no("Review the configuration before applying?"):
        print("\nConfiguration:")
        print(json.dumps(config, indent=2))
        if rigs_to_delete:
            print("\nRIGs to be deleted:", rigs_to_delete)
        if not prompt_yes_no("\nProceed with update?"):
            print("Update cancelled")
            return

    cmd = f"aws sagemaker update-cluster --cluster-name {cluster_arn} --cli-input-json file://{config_file}"
    if rigs_to_delete:
        rigs_json = json.dumps(rigs_to_delete)
        cmd += f" --instance-groups-to-delete '{rigs_json}'"
    
    exit_code, stdout, stderr = run_command(cmd)
    
    if exit_code != 0:
        print(f"Error updating cluster: {stderr}")
    else:
        print("Cluster update initiated successfully")

def main():
    parser = argparse.ArgumentParser(description="Manage HyperPod Restricted Instance Groups (RIG)")
    parser.add_argument("cluster_arn", help="ARN of the HyperPod cluster")
    parser.add_argument("--region", required=True, help="AWS region")
    args = parser.parse_args()

    # Get cluster configuration
    cluster_config = describe_cluster(args.cluster_arn, args.region)
    if not cluster_config:
        sys.exit(1)

    # Check RIG setup
    if not has_rig_setup(cluster_config):
        print("No RIG setup found. Please set up RIG using 00_setup/create_hp_cluster.sh first.")
        sys.exit(1)

    # Get operation choice
    print("\nAvailable operations:")
    print("1. Add new RIG")
    print("2. Scale existing RIG")
    print("3. Delete RIG")
    
    while True:
        try:
            choice = int(input("\nSelect operation (enter number): "))
            if choice in [1, 2, 3]:
                break
            print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a number.")

    operation = {1: "add", 2: "scale", 3: "delete"}[choice]
    
    # Update configuration
    updated_config, rigs_to_delete = update_cluster_config(cluster_config, operation)
    if updated_config:
        update_cluster(args.cluster_arn, args.region, updated_config, rigs_to_delete)

if __name__ == "__main__":
    main()
