#!/bin/bash

# ETF RAG Agent Setup Script

echo "==================================="
echo "ETF RAG Agent Setup"
echo "==================================="

# Check Python version
echo -e "\n[1/6] Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo -e "\n[2/6] Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo -e "\n[3/6] Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo -e "\n[4/6] Installing dependencies..."
pip install -r requirements.txt

# Copy environment file
echo -e "\n[5/6] Setting up environment variables..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please edit it with your API keys."
else
    echo ".env file already exists. Skipping..."
fi

# Create necessary directories
echo -e "\n[6/6] Creating directories..."
mkdir -p logs
mkdir -p data/raw
mkdir -p models

echo -e "\n==================================="
echo "Setup completed!"
echo "==================================="
echo -e "\nNext steps:"
echo "1. Edit .env file with your API keys"
echo "2. Start Weaviate: docker run -d -p 8080:8080 -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true semitechnologies/weaviate:latest"
echo "3. Generate gRPC files: python -m grpc_tools.protoc -I./protos --python_out=./protos/__generated__ --grpc_python_out=./protos/__generated__ ./protos/etf_query.proto"
echo "4. Run the server: python -m app.main"
echo -e "\n==================================="
