import json
import boto3
import io 
from datetime import datetime
from botocore.exceptions import ClientError
import zipfile
import os
import pg8000

s3_client = boto3.client('s3')

DB_HOST     = os.environ['DB_HOST']
DB_USER     = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_NAME     = os.environ['DB_NAME']
DB_PORT     = os.environ.get('DB_PORT', '5432')


def get_db_connection():
    """Creates and returns a PostgreSQL database connection."""
    try:
        conn = pg8000.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=int(DB_PORT),
            timeout=10
        )
        return conn
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        print(f"  Host: {DB_HOST}")
        print(f"  Port: {DB_PORT}")
        print(f"  User: {DB_USER}")
        raise


def lambda_handler(event, context): 
    connection = get_db_connection()
    try:
        for record in event['Records']:
            try:
                message_body = json.loads(record['body'])

                bucket = message_body['bucket']
                full_key = message_body['key']

                print(f"Processing: s3://{bucket}/{full_key}")

                zip_parts = full_key.split('.zip/')
                files = []
                for i, p in enumerate(zip_parts):
                    if i < len(zip_parts) - 1:
                        files.append(p + ".zip")
                    else:
                        files.append(p)
                
                # Download and process file
                file_content = download_from_s3(bucket, files[0])
                print(len(file_content))
                data_file = open_zip(file_content, files)
                print(len(data_file))
                records = parse_dat_file(data_file, full_key , bucket)
                print(f'record to write {len(records)}')
                write_records_to_rds(records , connection)
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                print(f"AWS Error ({error_code}): {str(e)}")
                raise

            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                raise
    finally:
        # close the connection — runs even if something above threw an error
        connection.close()
    return {'statusCode': 200}


def open_zip(file_content, files):
    """Extract file from nested zip archives."""
    with zipfile.ZipFile(io.BytesIO(file_content)) as z:
        current_zip = z
        for f in files[1:]:
            if f.endswith(".zip"):
                inner_data = current_zip.read(f)
                current_zip = zipfile.ZipFile(io.BytesIO(inner_data))
            else:
                file_data = current_zip.read(f)
                return file_data.decode("utf-8", errors="replace")


def download_from_s3(bucket, file0):
    """Download file from S3."""
    response = s3_client.get_object(Bucket=bucket, Key=file0)
    return response['Body'].read()


def parse_dat_file(data, full_key, bucket):
    """Parse data file into records."""
    records = []

    for row_number, line in enumerate(data.splitlines(), start=1):
        if not line.strip() or not line.startswith("B"):
            continue

        record = {
            "row_number": row_number,
            "raw_line": line,
            "source_file": f's3://{bucket}/{full_key}',
            "ingested_at": datetime.utcnow().isoformat()
        }

        records.append(record)

    return records


def write_records_to_rds(records, connection, batch_size=1000):
    rows = [
        (r["row_number"], r["raw_line"], r["source_file"], r["ingested_at"])
        for r in records
    ]

    try:
        cursor = connection.cursor()
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            placeholders = ", ".join(
                [f"(%s, %s, %s, %s)"] * len(batch)
            )
            sql = f"""
                INSERT INTO nsw_property_sales_raw (row_number, raw_line, source_file, ingested_at)
                VALUES {placeholders}
            """
            # Flatten list of tuples into a single list of params
            params = [val for row in batch for val in row]
            cursor.execute(sql, params)
            connection.commit()
            print(f"Wrote batch {i // batch_size + 1} ({len(batch)} rows)")

        print(f"Successfully wrote {len(records)} total records")
    except Exception as e:
        connection.rollback()
        print(f"Database write failed at row ~{i}: {str(e)}")
        raise
