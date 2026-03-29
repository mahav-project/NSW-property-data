resource "aws_sqs_queue" "ingestion_dlq" {
  name                      = "nsw-property-ingestion-dlq"
  message_retention_seconds = 1209600 # 14 days (AWS maximum)

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_sqs_queue" "ingestion_queue" {
  name                       = "nsw-property-ingestion-queue"
  visibility_timeout_seconds = 220
  message_retention_seconds  = 1209600 # 14 days (AWS maximum)

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ingestion_dlq.arn
    maxReceiveCount     = 1
  })

  lifecycle {
    prevent_destroy = true
  }
}
