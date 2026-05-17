#!/bin/bash

# Ensure script halts on failure
set -e

echo "========================================="
echo " Starting Meridian RAG Agent Application "
echo "========================================="

# 1. Load Environment Variables dynamically
if [ -f .env ]; then
  echo "Loading environment variables from .env"
  export $(grep -v '^#' .env | sed 's/ *= */=/g' | xargs)
else
  echo "[WARNING] .env file not found. Cloud environments like HuggingFace will use Native Secrets."
fi

if [ -z "$GEMINI_API_KEY" ]; then
  echo "Error: GEMINI_API_KEY is not set. Please set it in your .env file or HuggingFace Secrets."
  exit 1
fi

# 2. Boot FastAPI Backend using uv inside the python virtual environment
echo "Initializing Python Backend & Vector Store..."
cd backend

# Always run the idempotent document ingest sequence first
./.venv/bin/python ingest.py

# Boot the FastAPI uvicorn server in background
./.venv/bin/uvicorn app:app --port 8000 --host 0.0.0.0 &
BACKEND_PID=$!
cd ..

# 3. Boot SvelteKit Frontend
echo "Initializing Node Frontend..."
cd frontend
# Ensure node packages exist
if [ ! -d "node_modules" ]; then
    npm install --ignore-engines
fi

# Boot Vite server natively on port 7860 (HuggingFace compatible) 
npm run dev -- --host 0.0.0.0 --port 7860 &
FRONTEND_PID=$!

echo "========================================="
echo "All processes started!"
echo "Backend: internal (port 8000)"
echo "Frontend: http://0.0.0.0:7860"
echo "Logs/Admin: http://0.0.0.0:7860/admin"
echo "Press CTRL+C anytime to cleanly stop all services."
echo "========================================="

# Helper trap to kill background processes on Ctrl+c
trap "echo 'Shutting down services...'; kill $BACKEND_PID $FRONTEND_PID; exit 0" SIGINT SIGTERM

wait $BACKEND_PID $FRONTEND_PID
