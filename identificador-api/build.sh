#!/usr/bin/env bash
set -e

echo "==> Setting up Python environment"
export PYTHON_VERSION="3.11.10"

# Upgrade pip to latest
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

echo "==> Build complete"

