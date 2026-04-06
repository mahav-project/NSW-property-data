resource "null_resource" "build_layer" {
  triggers = {
    requirements = filemd5("${path.module}/../functions/requirements.txt")
  }

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    command = <<EOT
set -e
BUILD_PATH="${path.module}/.build/layer"
PYTHON_PATH="$BUILD_PATH/python"
ZIP_PATH="${path.module}/.build/layer.zip"

echo "Building Lambda layer..."

rm -rf "$BUILD_PATH"
mkdir -p "$PYTHON_PATH"

pip install -r "${path.module}/../functions/requirements.txt" -t "$PYTHON_PATH"

if [ ! -d "$PYTHON_PATH/pg8000" ]; then
  echo "pg8000 not installed correctly" >&2
  exit 1
fi

rm -f "$ZIP_PATH"
ZIP_ABS="$(cd "$(dirname "$ZIP_PATH")" && pwd)/$(basename "$ZIP_PATH")"
cd "$BUILD_PATH" && zip -r "$ZIP_ABS" python/

if [ ! -f "$ZIP_ABS" ]; then
  echo "Layer zip was not created" >&2
  exit 1
fi

echo "Layer built successfully at $ZIP_ABS"
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