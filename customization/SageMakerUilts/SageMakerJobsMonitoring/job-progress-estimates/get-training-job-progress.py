import boto3
import argparse
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple

class SageMakerTrainingJobStatus:
    def __init__(self, job_name: str, region: str, num_dataset_samples: int):
        self.job_name = job_name
        self.region = region
        self.num_dataset_samples = num_dataset_samples
        self.sagemaker_client = boto3.client('sagemaker', region_name=region)
        self.logs_client = boto3.client('logs', region_name=region)

    def _calculate_iterations_per_epoch(self, batch_size: int) -> int:
        """Calculate the number of iterations per epoch based on dataset size and batch size."""
        return self.num_dataset_samples / batch_size

    def get_job_description(self) -> Dict[str, Any]:
        """Fetch training job information from SageMaker."""
        try:
            return self.sagemaker_client.describe_training_job(TrainingJobName=self.job_name)
        except Exception as e:
            raise Exception(f"Failed to retrieve training job details: {str(e)}")

    def get_latest_iteration_from_logs(self, log_stream_name_prefix: str) -> Tuple[Optional[int], Optional[datetime], Optional[int]]:
        """Query CloudWatch logs to get the latest training iteration information."""
        try:
            # Get logs from the last 1 hour
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(minutes=60)).timestamp() * 1000)

            response = self.logs_client.filter_log_events(
                logGroupName="/aws/sagemaker/TrainingJobs",
                logStreamNamePrefix=log_stream_name_prefix,
                startTime=start_time,
                endTime=end_time,
                filterPattern="Epoch",
                limit=10000
            )

            latest_iteration = None
            latest_timestamp = None
            latest_epoch = None

            for event in response.get('events', []):
                match = re.search(r'Epoch (\d+): : (\d+)it', event['message'])
                if match:
                    epoch = int(match.group(1))
                    iteration = int(match.group(2))
                    if latest_epoch is None or epoch > latest_epoch:
                        latest_epoch = epoch
                        latest_iteration = iteration
                        latest_timestamp = datetime.fromtimestamp(event['timestamp']/1000.0, tz=timezone.utc)
                    elif epoch == latest_epoch and (latest_iteration is None or iteration > latest_iteration):
                        latest_iteration = iteration
                        latest_timestamp = datetime.fromtimestamp(event['timestamp']/1000.0, tz=timezone.utc)

            return latest_iteration, latest_timestamp, latest_epoch

        except Exception as e:
            print(f"Warning: Could not parse epoch information from logs: {str(e)}")
            return None, None, None

    def calculate_progress(self, response: Dict[str, Any]) -> str:
        """Calculate and return the progress of the training job as a string."""
        start_time = response['TrainingStartTime']
        current_time = datetime.now(timezone.utc)

        # Get batch size and epoch count from hyperparameters
        try:
            batch_size = int(response['HyperParameters'].get('batchSize', 32))
            total_epochs = int(response['HyperParameters'].get('epochCount', 2))

            # Calculate iterations per epoch
            iterations_per_epoch = self._calculate_iterations_per_epoch(batch_size)
            total_iterations = iterations_per_epoch * total_epochs

        except (KeyError, ValueError) as e:
            return f"Error calculating progress: Could not parse HyperParameters: {str(e)}"

        current_iteration, log_timestamp, current_epoch = self.get_latest_iteration_from_logs(self.job_name)

        if current_iteration is None or current_epoch is None:
            return (f"Training for job {self.job_name} is in progress, but there is not enough data "
                    f"to estimate progress as of {current_time.strftime('%H:%M UTC %m/%d/%Y')}. Try again in a few minutes.")

        if log_timestamp:
            total_completed_iterations = (current_epoch * iterations_per_epoch) + current_iteration
            elapsed_time = (log_timestamp - start_time).total_seconds()
            progress_percentage = (total_completed_iterations / total_iterations) * 100

            if progress_percentage >= 100:
                return (f"Training iterations for job {self.job_name} are complete. "
                        f"Final validation, fine-tuning, and artifact upload steps are in progress as of "
                        f"{log_timestamp.strftime('%H:%M UTC %m/%d/%Y')}.")
            elif progress_percentage <= 0:
                return (f"Training for job {self.job_name} has just begun. Initial model setup and "
                        f"first training iterations are in progress as of "
                        f"{log_timestamp.strftime('%H:%M UTC %m/%d/%Y')}. Check back in a few minutes "
                        f"for a more detailed progress update.")

            time_per_iteration = elapsed_time / total_completed_iterations if total_completed_iterations > 0 else 0
            remaining_iterations = total_iterations - total_completed_iterations
            remaining_minutes = (remaining_iterations * time_per_iteration) / 60

            return (f"Training for job {self.job_name} is approximately {progress_percentage:.1f}% complete. "
                    f"Estimated training time remaining: {remaining_minutes:.1f} minutes "
                    f"[{remaining_minutes/60:.1f} hours]")

        return (f"Training for job {self.job_name} is in progress, but job progress could not be determined "
                f"as of {current_time.strftime('%H:%M UTC %m/%d/%Y')}. Try again in a few minutes.")

    def _handle_non_running_job(self, status: str, response: Dict[str, Any]) -> str:
        """Handle status reporting for non-running jobs."""
        end_time = response.get('TrainingEndTime', datetime.now(timezone.utc))
        if status == 'Failed':
            failure_reason = response.get('FailureReason', 'Unknown')
            return (f"Job {self.job_name} failed at {end_time.strftime('%H:%M UTC %m/%d/%Y')} "
                    f"due to \"{failure_reason}\"")
        elif status == 'Completed':
            duration = response.get('TrainingTimeInSeconds', None)
            base_message = f"Job {self.job_name} succeeded at {end_time.strftime('%H:%M UTC %m/%d/%Y')}"

            if duration is not None:
                hours = duration // 3600
                minutes = (duration % 3600) // 60

                if hours > 0:
                    duration_str = f". Training time was {hours} hour{'s' if hours != 1 else ''} and {minutes} minute{'s' if minutes != 1 else ''}."
                else:
                    duration_str = f". Training time was {minutes} minute{'s' if minutes != 1 else ''}."

                return base_message + duration_str

            return base_message
        return f"Job {self.job_name} is {status} as of {end_time.strftime('%H:%M UTC %m/%d/%Y')}."

    def _handle_in_progress_job(self, secondary_status: str, response: Dict[str, Any]) -> str:
        """Handle status reporting for in-progress jobs."""
        current_time = datetime.now(timezone.utc)
        if secondary_status == 'Training':
            print("Please note that these estimates are approximate projections and should not be interpreted as definitive training durations.\n")
            return self.calculate_progress(response)
        elif secondary_status == 'Pending':
            return (f"Job {self.job_name} is {secondary_status.lower()}. Instances are being prepared for training.")
        elif secondary_status == 'Downloading':
            return (f"Job {self.job_name} is {secondary_status.lower()}. Training image is being downloaded.")
        elif secondary_status == 'Uploading':
            return (f"Job {self.job_name} is {secondary_status.lower()}. Training is complete and model artifacts are being uploaded to S3!")
        elif secondary_status in ['Starting']:
            return (f"Job {self.job_name} is {secondary_status.lower()}. Training has not started yet. "
                    f"Rerun this script once training begins to get a training time estimate.")
        return (f"Job {self.job_name} status: InProgress, Secondary status: {secondary_status} "
                f"as of {current_time.strftime('%H:%M UTC %m/%d/%Y')}.")

    def get_status(self) -> str:
        """Get the formatted status of the training job."""
        try:
            response = self.get_job_description()
            status = response['TrainingJobStatus']
            secondary_status = response.get('SecondaryStatus', 'Unknown')

            if status != 'InProgress':
                return self._handle_non_running_job(status, response)

            return self._handle_in_progress_job(secondary_status, response)

        except Exception as e:
            return f"Unable to retrieve status for job {self.job_name}: {str(e)}"


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Check SageMaker training job progress information')
    parser.add_argument('--job-name',
                        required=True,
                        help='Name of the SageMaker training job to check')
    parser.add_argument('--region',
                        required=True,
                        help='AWS region (e.g., us-east-1) of the SageMaker training job')
    parser.add_argument('--num-dataset-samples',
                        required=True,
                        type=int,
                        help='Approximate number of samples in your S3 training dataset')
    args = parser.parse_args()

    return args


def main():
    args = parse_arguments()
    status_checker = SageMakerTrainingJobStatus(
        job_name=args.job_name,
        region=args.region,
        num_dataset_samples=args.num_dataset_samples,
    )
    print(status_checker.get_status())


if __name__ == "__main__":
    main()

