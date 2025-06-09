#!/bin/bash
# Activation script for RTSP Camera Streaming Application virtual environment

echo "🎥 RTSP Camera Streaming - Activating Virtual Environment"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Run: python3 setup_env.py"
    exit 1
fi

# Check if we're already in a virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    echo "⚠️  Already in virtual environment: $VIRTUAL_ENV"
    echo "   Deactivate first with: deactivate"
else
    echo "✅ Activating virtual environment..."
    source venv/bin/activate
    echo "🚀 Virtual environment activated!"
    echo "   Python: $(which python)"
    echo "   To deactivate: deactivate"
fi