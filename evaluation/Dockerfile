FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy evaluation script
COPY plagiarism_evaluator.py .
RUN chmod +x plagiarism_evaluator.py

# Create volumes for input and output
VOLUME ["/data", "/results"]

# Run evaluation script
ENTRYPOINT ["python", "plagiarism_evaluator.py"]