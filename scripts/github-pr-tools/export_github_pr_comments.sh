#!/usr/bin/env bash
set -euo pipefail
#
# Export all PR review comments from GitHub to a JSON file
# Mainly used to export CodeRabbit's comments for a given PR
# and feed them to the AI agent to improve the PR
#

# Load token from .env if present
if [ -f "$(dirname "$0")/.env" ]; then
  source "$(dirname "$0")/.env"
fi

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "Error: GITHUB_TOKEN not set. Put it in scripts/github-pr-tools/.env or export it."
  exit 1
fi

if [ $# -lt 1 ]; then
  echo "Usage: $0 <PR_NUMBER>"
  exit 1
fi

PR_NUMBER=$1
OUTPUT_DIR="$(dirname "$0")/output"
mkdir -p "$OUTPUT_DIR"
OUTPUT_FILE="$OUTPUT_DIR/pr_${PR_NUMBER}_comments.json"

curl -sSf \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/didac-crst/mockexchange/pulls/$PR_NUMBER/comments?per_page=100" \
  > "$OUTPUT_FILE"

echo "✅ Exported PR #$PR_NUMBER comments to $OUTPUT_FILE"
