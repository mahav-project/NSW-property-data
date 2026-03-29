resource "aws_cloudwatch_dashboard" "pipeline" {
  dashboard_name = "NSWPropertyDataPipeline"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 24
        height = 4
        properties = {
          title               = "Errors"
          view                = "singleValue"
          region              = "ap-southeast-2"
          stat                = "Sum"
          setPeriodToTimeRange = true
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", "nsw-property-file-selector"],
            [".", ".", ".", "nsw-property-file-downloader"],
            [".", ".", ".", "nsw-property-zip-scanner"],
            [".", ".", ".", "nsw-property-db-ingestor"]
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 4
        width  = 24
        height = 4
        properties = {
          title               = "Invocations"
          view                = "singleValue"
          region              = "ap-southeast-2"
          stat                = "Sum"
          setPeriodToTimeRange = true
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", "nsw-property-file-selector"],
            [".", ".", ".", "nsw-property-file-downloader"],
            [".", ".", ".", "nsw-property-zip-scanner"],
            [".", ".", ".", "nsw-property-db-ingestor"]
          ]
        }
      }
    ]
  })
}
