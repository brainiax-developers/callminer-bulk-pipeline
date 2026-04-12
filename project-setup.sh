#!/bin/sh
# Usage: sh project-setup.sh {build account profile name}
# Example: sh project-setup.sh data-build

set -eu

uv python install
unset AWS_VAULT
CODEARTIFACT_TOKEN="$(
  aws-vault exec build-non-prod -- \
    aws codeartifact get-authorization-token \
      --domain data-theverygroup \
      --domain-owner 669610644781 \
      --query authorizationToken \
      --output text
)"
export CODEARTIFACT_TOKEN
export UV_INDEX_CODEARTIFACT_USERNAME=aws
export UV_INDEX_CODEARTIFACT_PASSWORD="$CODEARTIFACT_TOKEN"
# Install all deps locally including dev and test requirements. Keeping core deps down for lambda build
uv sync --all-groups

# Bootstraps pre-commit in the repo
# --- Ensure Homebrew exists ---
if ! command -v brew >/dev/null 2>&1; then
  echo "❌ Homebrew not found. Please install from https://brew.sh/"
  exit 1
fi

# --- Ensure pre-commit installed ---
if ! command -v pre-commit >/dev/null 2>&1; then
  echo "⬇️ Installing pre-commit via Homebrew…"
  brew install pre-commit
else
  echo "ℹ️ pre-commit already installed."
fi

# --- Run pre-commit install in repo root ---
if [ ! -f .pre-commit-config.yaml ]; then
  echo "❌ No .pre-commit-config.yaml found in this repo."
  exit 1
fi

echo "⚙️ Initializing git hooks with pre-commit"
pre-commit install

