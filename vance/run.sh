#!/bin/bash

# This shell script sets up the environment and runs the server
git pull origin main
source .venv/bin/activate
source env_vars.sh
# Pin to a single worker to match main.py and avoid race conditions
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
