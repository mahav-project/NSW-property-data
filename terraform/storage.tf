resource "aws_s3_bucket" "property_data" {
  bucket = "nsw-property-data"

  lifecycle {
    prevent_destroy = true
  }
}
