#!/bin/bash

# Create necessary directories
mkdir -p data results

# Check if test_cases.jsonl exists
if [ ! -f "data/test_cases.jsonl" ]; then
  echo "⚠️ Warning: data/test_cases.jsonl not found. Please add your test cases before running."
  echo "Expected format: {\"code\": \"your code here\", \"expected\": true}"
fi

# Build and run the Docker container
echo "🚀 Building and running the plagiarism evaluator..."
docker-compose up --build

# Check if results were generated
if [ -z "$(ls -A results)" ]; then
  echo "❌ No results generated. Check for errors above."
else
  echo "✅ Evaluation completed! Results saved to the 'results' directory."
  echo "📊 Files generated:"
  ls -l results/
fi