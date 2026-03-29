data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# shared env vars across all functions
locals {
  lambda_env = {
    S3_BUCKET_NAME                = aws_s3_bucket.property_data.bucket
    SQS_QUEUE_URL                 = aws_sqs_queue.ingestion_queue.url
    DB_NAME                       = var.db_name
    DB_HOST                       = aws_db_instance.property.address
    DB_USER                       = var.db_username
    DB_PASSWORD                   = var.db_password
    DB_PORT                       = "5432"
    FILE_DOWNLOADER_FUNCTION_NAME = "nsw-property-file-downloader"
    ZIP_SCANNER_FUNCTION_NAME     = "nsw-property-zip-scanner"
  }
}

# IAM role for all lambda functions
resource "aws_iam_role" "lambda_exec" {
  name = "nsw-property-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "nsw_property_access" {
  name = "NswPropertyAccess"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:HeadObject"]
        Resource = [
          aws_s3_bucket.property_data.arn,
          "${aws_s3_bucket.property_data.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Resource = [
          aws_sqs_queue.ingestion_queue.arn,
          aws_sqs_queue.ingestion_dlq.arn
        ]
      },
      {
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = [
          "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:nsw-property-file-downloader",
          "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:nsw-property-zip-scanner"
        ]
      }
    ]
  })
}

# zip each function for deployment
data "archive_file" "file_selector" {
  type        = "zip"
  source_dir  = "${path.module}/../functions/file_selector"
  output_path = "${path.module}/.build/file_selector.zip"
}

data "archive_file" "file_downloader" {
  type        = "zip"
  source_dir  = "${path.module}/../functions/file_downloader"
  output_path = "${path.module}/.build/file_downloader.zip"
}

data "archive_file" "zip_scanner" {
  type        = "zip"
  source_dir  = "${path.module}/../functions/zip_scanner"
  output_path = "${path.module}/.build/zip_scanner.zip"
}

data "archive_file" "db_ingestor" {
  type        = "zip"
  source_dir  = "${path.module}/../functions/db_ingestor"
  output_path = "${path.module}/.build/db_ingestor.zip"
}

# picks which files need downloading, runs monday 10am sydney time
resource "aws_lambda_function" "file_selector" {
  function_name    = "nsw-property-file-selector"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  timeout          = 200
  memory_size      = 500
  filename         = data.archive_file.file_selector.output_path
  source_code_hash = data.archive_file.file_selector.output_base64sha256
  layers           = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = local.lambda_env
  }

  depends_on = [null_resource.build_layer]
}

# monday 10am sydney time = midnight UTC
resource "aws_cloudwatch_event_rule" "file_selector_weekly" {
  name                = "nsw-property-file-selector-weekly"
  schedule_expression = "cron(0 0 ? * MON *)"
}

resource "aws_cloudwatch_event_target" "file_selector" {
  rule = aws_cloudwatch_event_rule.file_selector_weekly.name
  arn  = aws_lambda_function.file_selector.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_selector.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.file_selector_weekly.arn
}

resource "aws_lambda_function" "file_downloader" {
  function_name    = "nsw-property-file-downloader"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  timeout          = 200
  memory_size      = 500
  filename         = data.archive_file.file_downloader.output_path
  source_code_hash = data.archive_file.file_downloader.output_base64sha256
  layers           = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = local.lambda_env
  }

  depends_on = [null_resource.build_layer]
}

resource "aws_lambda_function_event_invoke_config" "file_downloader" {
  function_name          = aws_lambda_function.file_downloader.function_name
  maximum_retry_attempts = 0
}

resource "aws_lambda_function" "zip_scanner" {
  function_name    = "nsw-property-zip-scanner"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  timeout          = 200
  memory_size      = 500
  filename         = data.archive_file.zip_scanner.output_path
  source_code_hash = data.archive_file.zip_scanner.output_base64sha256
  layers           = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = local.lambda_env
  }

  depends_on = [null_resource.build_layer]
}

resource "aws_lambda_function_event_invoke_config" "zip_scanner" {
  function_name          = aws_lambda_function.zip_scanner.function_name
  maximum_retry_attempts = 0
}

resource "aws_lambda_function" "db_ingestor" {
  function_name                  = "nsw-property-db-ingestor"
  role                           = aws_iam_role.lambda_exec.arn
  handler                        = "handler.lambda_handler"
  runtime                        = "python3.12"
  timeout                        = 200
  memory_size                    = 500
  reserved_concurrent_executions = 10
  filename                       = data.archive_file.db_ingestor.output_path
  source_code_hash               = data.archive_file.db_ingestor.output_base64sha256
  layers                         = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = local.lambda_env
  }

  depends_on = [null_resource.build_layer]
}

# for inital load only uncomment this seciton when all files are ready to load in SQS
resource "aws_lambda_event_source_mapping" "db_ingestor_sqs" {
  event_source_arn = aws_sqs_queue.ingestion_queue.arn
  function_name    = aws_lambda_function.db_ingestor.arn
}
