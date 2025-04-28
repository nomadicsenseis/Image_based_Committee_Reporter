#!/bin/bash
set -e

echo "Starting Ollama service with GPU acceleration..."
CUDA_VISIBLE_DEVICES=0 ollama serve > /tmp/ollama.log 2>&1 &

echo "Waiting for Ollama to start..."
sleep 3

# Check if Ollama is running
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "✅ Ollama is running successfully with GPU support"
else
    echo "❌ Ollama failed to start. Check logs at /tmp/ollama.log"
    cat /tmp/ollama.log
fi

# Pull a small model for testing
echo "Pulling a small model (deepseek-r1:1.5b) for testing..."
ollama pull deepseek-r1:1.5b &

echo "Setup complete! You can access:"
echo "- Ollama API at: http://localhost:11434"
# echo "- PostgreSQL at: localhost:5432"