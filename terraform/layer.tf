resource "null_resource" "build_layer" {
  triggers = {
    requirements = filemd5("${path.module}/../functions/requirements.txt")
  }

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-Command"]
    command = <<EOT
      $buildPath = "${path.module}/.build/layer"
      $pythonPath = "$buildPath/python"
      $zipPath = "${path.module}/.build/layer.zip"

      Write-Host "Building Lambda layer..."

      # Clean build folder
      if (Test-Path $buildPath) { Remove-Item -Recurse -Force $buildPath }
      New-Item -ItemType Directory -Force $pythonPath | Out-Null

      # Install dependencies
      pip install -r "${path.module}/../functions/requirements.txt" -t $pythonPath

      # Ensure install worked
      if (!(Test-Path "$pythonPath/pg8000")) {
        Write-Error "pg8000 not installed correctly"
        exit 1
      }

      # Remove old zip
      if (Test-Path $zipPath) { Remove-Item -Force $zipPath }

      # Zip correctly (IMPORTANT: include python folder itself)
      Compress-Archive -Path "$pythonPath" -DestinationPath $zipPath

      # Verify zip exists
      if (!(Test-Path $zipPath)) {
        Write-Error "Layer zip was not created"
        exit 1
      }

      Write-Host "Layer built successfully at $zipPath"
    EOT
  }
}



resource "aws_lambda_layer_version" "dependencies" {
  filename         = "${path.module}/.build/layer.zip"
  source_code_hash = null_resource.build_layer.triggers["requirements"]
  layer_name       = "nsw-property-deps"

  compatible_runtimes = ["python3.12"]

  depends_on = [null_resource.build_layer]
}