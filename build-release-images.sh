#!/usr/bin/env bash

set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to build images" >&2
  exit 1
fi

repo_root=$(cd "$(dirname "$0")" && pwd)

registry=${REGISTRY:-docker2.crosslang.com}
namespace=${NAMESPACE:-ai4c}
tag=${TAG:-dev}
api_image_name=${API_IMAGE_NAME:-occam-gateway-jwt}
ui_image_name=${UI_IMAGE_NAME:-occam-ocr-ui-jwt}

api_image="${registry}/${namespace}/${api_image_name}:${tag}"
ui_image="${registry}/${namespace}/${ui_image_name}:${tag}"

echo "Building API image: ${api_image}"
docker build \
  -t "${api_image}" \
  "${repo_root}/occam-gateway/occam_gateway"

echo "Building UI image: ${ui_image}"
docker build \
  -t "${ui_image}" \
  "${repo_root}/occam-ocr-ui/frontend"

cat <<EOF

Build complete.

API image: ${api_image}
UI image:  ${ui_image}

Push them when ready with:
  docker push ${api_image}
  docker push ${ui_image}
EOF