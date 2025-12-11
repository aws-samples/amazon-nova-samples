# HyperPod Job Manager

A comprehensive command-line tool for managing HyperPod jobs including submission, monitoring, and administration tasks.

## Features

- **Interactive Job Submission**: Guided process for submitting new jobs
- **Job Monitoring**: Track job status and view logs
- **Job Management**: List and cancel running jobs
- **CloudWatch Integration**: View logs from CloudWatch
- **Container Management**: Support for multiple pre-configured containers
- **Flexible Configuration**: Customizable job parameters and resource settings

## Available Containers

1. **nova-sft**: Supervised Fine-Tuning container
2. **nova-dpo**: Direct Preference Optimization container
3. **nova-ppo**: PPO Training container
4. **nova-cpt**: CPT Training container
5. **nova-eval**: Evaluation container

## Usage

```bash
./hyperpod_job_manager.sh [flags]
```

### Flags

- `--job_name <name>`: Job name (required for monitor/cancel)
- `--namespace <ns>`: Kubernetes namespace (default: kubeflow)
- `--action <action>`: Action to perform (default: monitor)
- `--cluster-name <name>`: Cluster name for CloudWatch logs
- `--cluster-id <id>`: Cluster ID for CloudWatch logs
- `--rig-name <name>`: RIG name for CloudWatch logs

### Actions

1. **submit**: Launch a new job interactively

   ```bash
   ./hyperpod_job_manager.sh --action submit
   ```

2. **monitor**: Monitor job status and logs

   ```bash
   ./hyperpod_job_manager.sh --job_name my-job --action monitor --cluster-name my-cluster --cluster-id cluster123 --rig-name my-rig
   ```

3. **list**: Display all jobs

   ```bash
   ./hyperpod_job_manager.sh --action list
   ```

4. **cancel**: Terminate a running job immediately (no confirmation prompt)
   ```bash
   ./hyperpod_job_manager.sh --job_name my-job --action cancel
   ```

## Job Submission Process

When submitting a new job, you'll be prompted for:

1. **Basic Configuration**

   - Run name (used to generate job name)
   - Namespace (optional, defaults to 'kubeflow')
   - Recipe path

2. **Container Selection**

   - Choose from pre-configured containers
   - Option to specify custom container URI

3. **Resource Configuration**

   - Instance type (e.g., ml.p4d.24xlarge)

4. **S3 Configuration (Optional)**

   - Input data path
   - Output path
   - Tensorboard path

5. **Additional Parameters**
   - Custom JSON parameters for fine-tuning job configuration

### Special Handling for Evaluation Container

When selecting the evaluation container, additional prompts include:

- Model manifest path (required)
- Optional custom evaluation data path

## Job Monitoring

The monitoring functionality provides:

1. **Job Status**

   - List of all jobs in the namespace
   - Detailed pod status for specific job

2. **Pod Details**

   - Kubernetes pod descriptions
   - Resource utilization
   - Event logs

3. **CloudWatch Logs Integration**
   - Real-time log streaming
   - Historical log access
   - Automatic log stream discovery

### CloudWatch Logs Requirements

To view CloudWatch logs, you need to provide:

- Cluster name
- Cluster ID
- RIG name

## Configuration Storage

Job configurations are automatically saved in the `hyperpod_configs` directory with:

- Job name
- Timestamp
- All parameters used for submission
- Submission time

## Error Handling

The script includes comprehensive error handling for:

- Missing required parameters
- Invalid container selections
- Job submission failures
- Log access issues

## Color-Coded Output

The script uses color-coding for better visibility:

- 🟦 Blue: Headers and sections
- 🟩 Green: Success messages
- 🟥 Red: Error messages
- 🟨 Yellow: Warnings
- 🟦 Cyan: Information and prompts

## Best Practices

1. **Job Names**

   - Use descriptive run names
   - Keep track of job configurations in the configs directory

2. **Monitoring**

   - Use the monitor action to track job progress
   - Check CloudWatch logs for detailed execution information

3. **Resource Management**

   - Cancel unused jobs to free up resources
   - Monitor resource utilization through pod details

4. **Troubleshooting**
   - Check pod status for job issues
   - Review CloudWatch logs for detailed error messages
   - Use the saved configuration files for job recreation if needed
