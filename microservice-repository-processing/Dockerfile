FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libmagic1 \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/repositories /app/vector_store

# Create the app directory structure
RUN mkdir -p /app/app

# Copy the application code
COPY *.py /app/
COPY app/*.py /app/app/

# Set environment variables
ENV PYTHONPATH=/app

# Expose the port that FastAPI will run on
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]