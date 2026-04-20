#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -f terraform.tfvars ]]; then
  echo "terraform.tfvars not found"
  exit 1
fi

IMAGE_URL="$(./build_and_push.sh | tail -n 1)"

cat > terraform.tfvars.runtime <<RUNTIME
image_url = "${IMAGE_URL}"
RUNTIME

terraform init -input=false
terraform fmt
terraform validate
terraform plan -var-file=terraform.tfvars -var-file=terraform.tfvars.runtime
terraform apply -auto-approve -var-file=terraform.tfvars -var-file=terraform.tfvars.runtime

terraform output service_url
