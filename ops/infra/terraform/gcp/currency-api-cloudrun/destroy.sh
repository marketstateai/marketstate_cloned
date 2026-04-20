#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

terraform destroy -auto-approve -var-file=terraform.tfvars -var-file=terraform.tfvars.runtime
