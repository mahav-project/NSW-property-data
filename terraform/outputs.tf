output "database_endpoint" {
  description = "DB HOST"
  value       = aws_db_instance.property.address
}

output "database_port" {
  value = aws_db_instance.property.port
}

output "s3_bucket_name" {
  value = aws_s3_bucket.property_data.bucket
}

output "sqs_queue_url" {
  value = aws_sqs_queue.ingestion_queue.url
}
