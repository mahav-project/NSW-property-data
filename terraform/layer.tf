resource "null_resource" "build_layer" {
  triggers = {
    requirements = filemd5("${path.module}/../functions/requirements.txt")
  }

  provisioner "local-exec" {
    command = "pip install -r ${path.module}/../functions/requirements.txt -t ${path.module}/.build/python/"
  }
}

data "archive_file" "layer" {
  type        = "zip"
  source_dir  = "${path.module}/.build/python"
  output_path = "${path.module}/.build/layer.zip"

  depends_on = [null_resource.build_layer]
}

resource "aws_lambda_layer_version" "dependencies" {
  filename            = data.archive_file.layer.output_path
  source_code_hash    = data.archive_file.layer.output_base64sha256
  layer_name          = "nsw-property-deps"
  compatible_runtimes = ["python3.12"]

  depends_on = [null_resource.build_layer]
}
