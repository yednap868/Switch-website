#! /bin/bash

# Kill existing server process
pkill -f "uvicorn main:app --port 8000"

# Pull latest code from GitHub
git pull origin prod

# Load env vars:
source env_vars.sh

# Start server with new code, saving logs inside project directory:
uv sync
nohup bash -c "source env_vars.sh && uv run uvicorn main:app --port 8000 --workers 1" > ./vance.out 2> ./vance.err < /dev/null & disown
