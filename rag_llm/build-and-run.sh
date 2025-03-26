#!/bin/bash

# Create required directories if they don't exist
mkdir -p repositories
mkdir -p vector_store
mkdir -p app

# Make sure the .env file exists
if [ ! -f .env ]; then
  echo "Creating .env file from template..."
  cp .env.template .env
  echo "Please edit the .env file with your API key before continuing"
  exit 1
fi

# Build the Docker image
echo "Building Docker image..."
docker build -t repo-processing-microservice .

# Run the container
echo "Running container..."
docker run -d --name repo-processor \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/repositories:/app/repositories \
  -v $(pwd)/vector_store:/app/vector_store \
  repo-processing-microservice

echo "Container started. API available at http://localhost:8000"
echo "To view logs, run: docker logs -f repo-processor"
echo "To stop the container, run: docker stop repo-processor"