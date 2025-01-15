import os
import time
import boto3
import json
import logging
import cv2
from datetime import datetime
from moviepy import VideoFileClip, CompositeVideoClip

logger = logging.getLogger(__name__)

bedrock_runtime = boto3.client("bedrock-runtime")
s3_client = boto3.client("s3")


def save_invocation_info(
    invocation_result: dict, model_input: dict, output_folder: str = "output"
) -> str:
    """
    Save the invocation result and model input to the specified output folder.

    Args:
        invocation_result (dict): The result of the video generation invocation.
        model_input (dict): The input parameters used for the video generation.
        output_folder (str, optional): The folder where the invocation info will be saved. Defaults to "output".

    Returns:
        str: The absolute path of the output folder.
    """
    invocation_arn = invocation_result["invocationArn"]
    logger.info(f"Getting async invoke details for ARN: {invocation_arn}")
    invocation_job = bedrock_runtime.get_async_invoke(invocationArn=invocation_arn)
    folder_name = get_folder_name_for_job(invocation_job)

    output_folder_abs = os.path.abspath(f"{output_folder}/{folder_name}")
    os.makedirs(output_folder_abs, exist_ok=True)
    logger.info(f"Saving invocation info to folder: {output_folder_abs}")

    with open(
        os.path.join(output_folder_abs, "start_async_invoke_response.json"), "w"
    ) as f:
        json.dump(invocation_result, f, indent=2, default=str)
        logger.info("Saved start_async_invoke_response.json")

    with open(os.path.join(output_folder_abs, "model_input.json"), "w") as f:
        json.dump(model_input, f, indent=2, default=str)
        logger.info("Saved model_input.json")

    return output_folder_abs


def get_folder_name_for_job(invocation_job: dict) -> str:
    """
    Generate a folder name for the job based on the invocation ARN and submission time.

    Args:
        invocation_job (dict): The job details containing the invocation ARN and submission time.

    Returns:
        str: The generated folder name.
    """
    invocation_arn = invocation_job["invocationArn"]
    invocation_id = invocation_arn.split("/")[-1]
    submit_time = invocation_job["submitTime"]
    timestamp = submit_time.astimezone().strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"{timestamp}_{invocation_id}"
    logger.info(f"Generated folder name: {folder_name}")
    return folder_name


def is_video_downloaded_for_invocation_job(
    invocation_job: dict, output_folder: str = "output"
) -> bool:
    """
    Check if the video file for the given invocation job has been downloaded.

    Args:
        invocation_job (dict): The job details containing the invocation ARN.
        output_folder (str, optional): The folder where the video is expected to be downloaded. Defaults to "output".

    Returns:
        bool: True if the video file exists, False otherwise.
    """
    invocation_arn = invocation_job["invocationArn"]
    invocation_id = invocation_arn.split("/")[-1]
    folder_name = get_folder_name_for_job(invocation_job)
    output_folder_abs = os.path.abspath(f"{output_folder}/{folder_name}")
    file_name = f"{invocation_id}.mp4"
    video_path = os.path.join(output_folder_abs, file_name)
    if os.path.exists(video_path):
        logger.info(f"Video file already downloaded: {video_path}")
        return True
    logger.info(f"Video file not found: {video_path}")
    return False


def download_video_for_invocation_arn(
    invocation_arn: str, bucket_name: str, destination_folder: str
):
    """
    Download the video file for the given invocation ARN from the specified S3 bucket.

    Args:
        invocation_arn (str): The ARN of the invocation.
        bucket_name (str): The name of the S3 bucket.
        destination_folder (str): The local folder where the video will be downloaded.

    Returns:
        str: Local file path for the downloaded video.
    """
    invocation_id = invocation_arn.split("/")[-1]
    file_name = f"{invocation_id}.mp4"
    output_folder_abs = os.path.abspath(destination_folder)
    os.makedirs(output_folder_abs, exist_ok=True)
    local_file_path = os.path.join(output_folder_abs, file_name)
    logger.info(f"Downloading video file to: {local_file_path}")

    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=invocation_id)

    for obj in response.get("Contents", []):
        object_key = obj["Key"]
        if object_key.endswith(".mp4"):
            s3_client.download_file(bucket_name, object_key, local_file_path)
            logger.info(f"Downloaded video file: {local_file_path}")
            return local_file_path

    logger.error(
        f"Problem: No MP4 file was found in S3 at {bucket_name}/{invocation_id}"
    )


def elapsed_time_for_invocation_job(invocation_job: dict) -> int:
    """
    Calculate the elapsed time for the given invocation job.

    Args:
        invocation_job (dict): The job details containing the submission and end times.

    Returns:
        int: The elapsed time in seconds.
    """
    invocation_start_time = invocation_job["submitTime"].timestamp()
    if "endTime" in invocation_job:
        invocation_end_time = invocation_job["endTime"].timestamp()
        elapsed_time = int(invocation_end_time - invocation_start_time)
    else:
        elapsed_time = int(time.time() - invocation_start_time)

    return elapsed_time


def log_job_progress(job: dict):
    """
    Helper function to log job progress.

    Args:
        job (dict): The job details containing the invocation ARN.
    """
    job_id = get_job_id_from_arn(job["invocationArn"])
    elapsed_time = elapsed_time_for_invocation_job(job)
    minutes, seconds = divmod(elapsed_time, 60)
    logger.info(
        f"Job {job_id} is still in progress, elapsed time: {minutes} minutes {seconds} seconds"
    )


def monitor_and_download_video(invocation_arn: str, output_folder: str = "output"):
    """
    Monitor and download a single video based on the provided invocation ARN.

    Args:
        invocation_arn (str): The ARN of the invocation.
        output_folder (str, optional): The folder where the video will be downloaded. Defaults to "output".

    Returns:
        str: Local file path for the downloaded video.
    """
    logger.info(f"Monitoring and downloading video for ARN: {invocation_arn}")
    invocation_job = bedrock_runtime.get_async_invoke(invocationArn=invocation_arn)
    status = invocation_job["status"]

    if status == "Completed":
        local_file_path = save_completed_job(
            invocation_job, output_folder=output_folder
        )
    elif status == "Failed":
        save_failed_job(invocation_job, output_folder=output_folder)
    else:
        local_file_path = monitor_and_download_in_progress_video(
            invocation_arn, output_folder=output_folder
        )

    return local_file_path


def monitor_and_download_in_progress_video(
    invocation_arn: str, output_folder: str = "output"
):
    """
    Monitor and download a single video that is currently in progress.

    Args:
        invocation_arn (str): The ARN of the invocation.
        output_folder (str, optional): The folder where the video will be downloaded. Defaults to "output".

    Returns:
        str: Local file path for the downloaded video.
    """
    logger.info(
        f"Monitoring and downloading in-progress video for ARN: {invocation_arn}"
    )
    job_update = bedrock_runtime.get_async_invoke(invocationArn=invocation_arn)
    status = job_update["status"]

    while status == "InProgress":
        log_job_progress(job_update)
        time.sleep(10)
        job_update = bedrock_runtime.get_async_invoke(invocationArn=invocation_arn)
        status = job_update["status"]

    if status == "Completed":
        local_file_path = save_completed_job(job_update, output_folder=output_folder)
        return local_file_path
    elif status == "Failed":
        save_failed_job(job_update, output_folder=output_folder)
    else:
        logger.error(f"Unexpected status: {status} for job {invocation_arn}")


def monitor_and_download_videos(
    output_folder: str = "output", submit_time_after: datetime = None
):
    """
    Monitor and download videos for jobs that are in progress, completed, or failed.

    Args:
        output_folder (str, optional): The folder where the videos will be downloaded. Defaults to "output".
        submit_time_after (datetime, optional): Filter jobs submitted after this time.
    """
    logger.info("Monitoring and downloading videos")
    failed_jobs_args = {"statusEquals": "Failed"}
    if submit_time_after:
        failed_jobs_args["submitTimeAfter"] = submit_time_after

    failed_jobs = bedrock_runtime.list_async_invokes(**failed_jobs_args)
    for job in failed_jobs["asyncInvokeSummaries"]:
        save_failed_job(job, output_folder=output_folder)

    completed_jobs_args = {"statusEquals": "Completed"}
    if submit_time_after:
        completed_jobs_args["submitTimeAfter"] = submit_time_after

    completed_jobs = bedrock_runtime.list_async_invokes(**completed_jobs_args)
    for job in completed_jobs["asyncInvokeSummaries"]:
        save_completed_job(job, output_folder=output_folder)

    monitor_and_download_in_progress_videos(output_folder=output_folder)


def monitor_and_download_in_progress_videos(output_folder: str = "output"):
    """
    Monitor and download videos for jobs that are currently in progress.

    Args:
        output_folder (str, optional): The folder where the videos will be downloaded. Defaults to "output".
    """
    logger.info("Monitoring and downloading in-progress videos")
    invocation_list = bedrock_runtime.list_async_invokes(statusEquals="InProgress")
    in_progress_jobs = invocation_list["asyncInvokeSummaries"]
    pending_job_arns = [job["invocationArn"] for job in in_progress_jobs]

    while pending_job_arns:
        job_arns_to_remove = []
        for job_arn in pending_job_arns:
            job_update = bedrock_runtime.get_async_invoke(invocationArn=job_arn)
            status = job_update["status"]

            if status in ("Completed", "Failed"):
                if status == "Completed":
                    save_completed_job(job_update, output_folder=output_folder)
                else:
                    save_failed_job(job_update, output_folder=output_folder)
                job_arns_to_remove.append(job_arn)
            else:
                log_job_progress(job_update)

        for job_arn in job_arns_to_remove:
            pending_job_arns.remove(job_arn)

        time.sleep(10)

    logger.info("Monitoring and download complete!")


def get_job_id_from_arn(invocation_arn: str) -> str:
    """
    Extract the job ID from the invocation ARN.

    Args:
        invocation_arn (str): The invocation ARN.

    Returns:
        str: The job ID.
    """
    return invocation_arn.split("/")[-1]


def save_completed_job(job: dict, output_folder: str = "output"):
    """
    Save the details of a completed job and download the video if it hasn't been downloaded yet.

    Args:
        job (dict): The job details.
        output_folder (str, optional): The folder where the job details and video will be saved. Defaults to "output".

    Returns:
        str: Local file path for the downloaded video.
    """
    job_id = get_job_id_from_arn(job["invocationArn"])
    output_folder_abs = os.path.abspath(
        f"{output_folder}/{get_folder_name_for_job(job)}"
    )
    os.makedirs(output_folder_abs, exist_ok=True)
    logger.info(f"Saving completed job details for job {job_id}")

    status_file = os.path.join(output_folder_abs, "completed.json")

    if is_video_downloaded_for_invocation_job(job, output_folder=output_folder):
        logger.info(f"Skipping completed job {job_id}, video already downloaded.")
        return

    s3_bucket_name = (
        job["outputDataConfig"]["s3OutputDataConfig"]["s3Uri"]
        .split("//")[1]
        .split("/")[0]
    )
    local_file_path = download_video_for_invocation_arn(
        job["invocationArn"], s3_bucket_name, output_folder_abs
    )

    with open(status_file, "w") as f:
        json.dump(job, f, indent=2, default=str)
        logger.info(f"Saved completed job details to {status_file}")

    return local_file_path


def save_failed_job(job: dict, output_folder: str = "output"):
    """
    Save the details of a failed job.

    Args:
        job (dict): The job details.
        output_folder (str, optional): The folder where the job details will be saved. Defaults to "output".
    """
    output_folder_abs = os.path.abspath(
        f"{output_folder}/{get_folder_name_for_job(job)}"
    )
    output_file = os.path.join(output_folder_abs, "failed.json")

    job_id = get_job_id_from_arn(job["invocationArn"])

    if os.path.exists(output_file):
        logger.info(f"Skipping failed job {job_id}, output file already exists.")
        return

    os.makedirs(output_folder_abs, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(job, f, indent=2, default=str)
        logger.info(f"Saved failed job details to {output_file}")


def extract_last_frame(video_path: str, output_path: str):
    """
    Extracts the last frame of a video file.

    Args:
        video_path (str): The local path to the video to extract the last frame from.
        output_path (str): The local path to save the extracted frame to.
    """
    # Open the video file
    cap = cv2.VideoCapture(video_path)

    # Check if the video file is opened successfully
    if not cap.isOpened():
        logger.error("Error: Could not open video.")
        return

    # Get the total number of frames in the video
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Move to the last frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)

    # Read the last frame
    ret, frame = cap.read()

    # Check if the frame is read successfully
    if ret:
        # Save the last frame as an image
        cv2.imwrite(output_path, frame)
        logger.info(f"Last frame saved as {output_path}")
    else:
        logger.error("Error: Could not read the last frame.")

    # Release the video capture object
    cap.release()


def stitch_videos(video1_path: str, video2_path: str, output_path: str):
    """
    Stitches two videos together and saves the result to a new file.

    Args:
        video1_path (str): The file path to the first video.
        video2_path (str): The file path to the second video.
        output_path (str): The file path to save the stitched video.
    """
    # Load the video clips
    clip1 = VideoFileClip(video1_path)
    clip2 = VideoFileClip(video2_path)

    final_clip = [
        clip1,
        clip2.with_start(clip1.duration),
    ]

    # Concatenate the clips
    final_clip = CompositeVideoClip(final_clip)

    # Write the result
    final_clip.write_videofile(output_path)

    # Clean up
    clip1.close()
    clip2.close()
    final_clip.close()

    logger.info(f"Stitched video saved to {output_path}")
