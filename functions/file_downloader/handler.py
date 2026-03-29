import boto3
import urllib.request
import json
import os

S3_BUCKET = os.environ["S3_BUCKET_NAME"]
PARSER_FUNCTION = os.environ["ZIP_SCANNER_FUNCTION_NAME"]

s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")


def lambda_handler(event, context):
    url = event["url"]
    s3_key = event["s3_key"]

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=300) as response:
            s3.upload_fileobj(response, S3_BUCKET, s3_key)
            print(f"Uploaded: {s3_key}")

            # Invoke zip_scanner asynchronously
            invoke_response = lambda_client.invoke(
                FunctionName=PARSER_FUNCTION,
                InvocationType="Event",  # fire and forget
                Payload=json.dumps({
                    "bucket": S3_BUCKET,
                    "key": s3_key
                })
            )
            if invoke_response["StatusCode"] == 202:
                print(f"Successfully invoked: {PARSER_FUNCTION}")
            else:
                print(f"Invocation failed: {invoke_response}")

            return {"s3_key": s3_key, "status": "ok"}

    except urllib.request.HTTPError as e:
        if e.code == 404:
            print(f"Not found: {url}")
            return {"s3_key": s3_key, "status": "not_found"}
        raise