import boto3
import json
import os
from botocore.exceptions import ClientError
from datetime import datetime, timedelta

lambda_client = boto3.client("lambda")
s3_client = boto3.client("s3")

# Pulled from env vars set in template.yaml
WORKER_FUNCTION = os.environ["FILE_DOWNLOADER_FUNCTION_NAME"]
S3_BUCKET = os.environ["S3_BUCKET_NAME"]

BASE_URL = "https://www.valuergeneral.nsw.gov.au/__psi/"
today = datetime.today()


def ensure_s3_folder(folder_key):
    """Create an S3 folder if it doesn't already exist."""
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=folder_key)
    except ClientError:
        s3_client.put_object(Bucket=S3_BUCKET, Key=folder_key)
        print(f"Created folder: {folder_key}")


def get_yearly_tasks():
    tasks = []
    current_year = datetime.today().year
    for year in range(1990, current_year):
        task = {
            "url": f"{BASE_URL}yearly/{year}.zip",
            "s3_key": f"NSW/Download/yearly/{year}.zip",
        }
        tasks.append(task)
    return tasks


def get_weekly_tasks():
    tasks = []
    end_date = today - timedelta(days=today.weekday())
    y = datetime.today().year
    d = datetime(y, 1, 1)
    start_date = d + timedelta(days=(7 - d.weekday()) % 7)
    while start_date <= end_date:
        formatted_date = start_date.strftime("%Y%m%d")
        task = {
            "url": f"{BASE_URL}weekly/{formatted_date}.zip",
            "s3_key": f"NSW/Download/weekly/{formatted_date}.zip",
        }
        tasks.append(task)
        start_date += timedelta(days=7)
    return tasks


def lambda_handler(event, context):
    mode = event.get("mode", "last_week")

    # Ensure folders exist before dispatching any download tasks
    ensure_s3_folder("NSW/")
    ensure_s3_folder("NSW/Download/")

    if mode == "full":
        ensure_s3_folder("NSW/Download/yearly/")
        ensure_s3_folder("NSW/Download/weekly/")
        tasks = get_yearly_tasks() + get_weekly_tasks()

    elif mode == "last_week":
        ensure_s3_folder("NSW/Download/weekly/")
        last_monday = (today - timedelta(days=today.weekday())).strftime("%Y%m%d")
        tasks = [{
            "url": f"{BASE_URL}weekly/{last_monday}.zip",
            "s3_key": f"NSW/Download/weekly/{last_monday}.zip",
        }]

    for task in tasks:
        lambda_client.invoke(
            FunctionName=WORKER_FUNCTION,
            InvocationType="Event",  # fire and forget — all workers start at the same time
            Payload=json.dumps(task),
        )
        print(f"Dispatched: {task['s3_key']}")

    return {
        "mode": mode,
        "dispatched": len(tasks),
    }