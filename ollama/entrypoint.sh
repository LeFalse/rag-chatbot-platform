#!/bin/bash

# Start Ollama server in background
/bin/ollama serve &

# Wait for Ollama to be ready
echo "Waiting for Ollama to start..."
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 1
done
echo "Ollama is ready!"

# Pull required models
echo "Pulling required models..."

# Embedding model (always required)
echo "Pulling nomic-embed-text..."
ollama pull nomic-embed-text

# LLM model (configurable via environment variable)
# Default: qwen3:8b (best for tool calling)
# Alternative: llama3.2 (lighter, no tool calling)
LLM_MODEL="${LLM_MODEL:-qwen3:8b}"
echo "Pulling LLM model: $LLM_MODEL"
ollama pull "$LLM_MODEL"

echo "All models ready!"

# Keep the script running (Ollama server is in background)
wait
