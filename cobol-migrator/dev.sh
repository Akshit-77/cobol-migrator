#!/usr/bin/env bash
# Start backend + frontend together. Press Ctrl+C to stop both.
set -e

# Load nvm if available (no-op if npm is already on PATH)
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"

cleanup() { kill 0; }
trap cleanup EXIT INT TERM

echo "Starting backend on http://localhost:8000 ..."
uv run uvicorn src.api:app --reload &

echo "Starting frontend on http://localhost:5173 ..."
cd frontend && npm run dev &

wait
