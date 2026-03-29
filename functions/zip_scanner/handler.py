import boto3
import zipfile
import io
import json
import os

s3_client = boto3.client("s3")
sqs_client = boto3.client("sqs")

QUEUE_URL = os.environ["SQS_QUEUE_URL"]


def get_all_files(zip_data, current_path=""):
    all_files = []

    with zipfile.ZipFile(zip_data, "r") as z:
        for filename in z.namelist():

            # Build full path including parent zip(s)
            full_path = f"{current_path}/{filename}" if current_path else filename
            all_files.append(full_path)

            # If nested zip → recurse
            if filename.lower().endswith(".zip"):
                with z.open(filename) as nested_file:
                    nested_bytes = io.BytesIO(nested_file.read())
                    nested_files = get_all_files(nested_bytes, full_path)
                    all_files.extend(nested_files)

    return all_files


def lambda_handler(event, context):
    try:
        bucket_name = event["bucket"]
        zip_key = event["key"]

        print("Started Input File:", zip_key)

        response = s3_client.get_object(Bucket=bucket_name, Key=zip_key)
        zip_data = io.BytesIO(response["Body"].read())

        filelist = get_all_files(zip_data, zip_key)

        # FILTER: Keep only .dat files
        dat_files = [f for f in filelist if f.lower().endswith(".dat")]

        for file_path in dat_files:
            message = {
                "bucket": bucket_name,
                "key": file_path
            }
            sqs_client.send_message(
                QueueUrl=QUEUE_URL,
                MessageBody=json.dumps(message)
            )

        print(f"[INPUT: {zip_key}] | Queued: {len(dat_files)} .dat files | Skipped: {len(filelist) - len(dat_files)} non-dat files")

        return {
            "statusCode": 200,
            "body": f"Found {len(filelist)} files",
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": f"Error: {str(e)}"
        }