#!/usr/bin/env bash
set -euo pipefail

: "${KV_NAMESPACE_ID:?KV_NAMESPACE_ID is required}"
: "${KV_PREVIEW_NAMESPACE_ID:?KV_PREVIEW_NAMESPACE_ID is required}"

sed \
  -e "s|__KV_NAMESPACE_ID__|$KV_NAMESPACE_ID|g" \
  -e "s|__KV_PREVIEW_NAMESPACE_ID__|$KV_PREVIEW_NAMESPACE_ID|g" \
  wrangler.template.jsonc > wrangler.jsonc

uv run build
