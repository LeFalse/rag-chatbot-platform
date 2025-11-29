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

# Embedding model
echo "Pulling nomic-embed-text..."
ollama pull nomic-embed-text

# LLM model
echo "Pulling llama3.2..."
ollama pull llama3.2

echo "All models ready!"

# Keep the script running (Ollama server is in background)
wait
