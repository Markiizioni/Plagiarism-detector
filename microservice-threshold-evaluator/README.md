# 🔢 Threshold-Based Code Plagiarism Detection Microservice

This microservice implements a vector similarity-based approach to detect code plagiarism by comparing input code against a database of embeddings. It relies on similarity thresholds to determine plagiarism without using language models.

---

## 🔍 Key Features

- **Calculate code similarity** using vector embeddings
- **Apply configurable thresholds** to determine plagiarism
- **Retrieve similar code chunks** from a FAISS vector store
- **Provide detailed similarity scores** and matching code
- **Dockerized for ease of deployment**

---

## 🔁 Workflow Overview

```
Client Input Code
        ↓
Generate Code Embedding
        ↓
Search Similar Code Chunks in Vector Database
        ↓
Apply Similarity Thresholds 
        ↓
Return Results (similar chunks, similarity scores, plagiarism determination)
```

---

## 📦 API Endpoints

| Method | Endpoint              | Description                                 |
|--------|-----------------------|---------------------------------------------|
| GET    | `/health`             | Health check                                |
| POST   | `/search-similar`     | Search for similar code and analyze similarity |

---

## 🛠️ Usage with Docker

### 1. Set up `.env`

```env
VECTOR_DB_PATH=/app/data/vector_db
THRESHOLD_HIGH=0.95
THRESHOLD_MEDIUM=0.85
THRESHOLD_LOW=0.75
EMBEDDING_MODEL=microsoft/codebert-base
```

### 2. Docker Compose

```yaml
services:
  threshold-evaluator:
    build:
      context: .
    ports:
      - "8003:8000"
    volumes:
      - ./data:/app/data
    env_file:
      - .env
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Start it

```bash
docker-compose up --build
```

---

## 🧠 How It Works

- Accepts code as input (`/search-similar`)
- Normalizes the code to standardize formatting
- Generates vector embedding for the input code
- Searches for similar code chunks in the FAISS database
- Applies configurable thresholds to determine plagiarism
- Returns detailed similarity information and matched code chunks

---

## 📁 File Structure

```
.
├── app/
│   ├── __init__.py              # Package initialization
│   ├── __pycache__/             # Python cache
│   ├── main.py                  # FastAPI app
│   ├── similarity_threshold.py  # Threshold-based analyzer
│   ├── utils.py                 # Code normalization utilities
├── .env                         # Configuration variables
├── .gitignore                   # Git ignore patterns
├── Dockerfile                   # Container instructions
├── docker-compose.yml           # Multi-container setup
├── README.md                    # This documentation
├── requirements.txt             # Python dependencies
```

---

## 📝 Example Request

```bash
curl -X POST http://localhost:8003/search-similar \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def factorial(n):\n    if n == 0:\n        return 1\n    else:\n        return n * factorial(n-1)",
    "top_k": 10,
    "analyze_plagiarism": true
  }'
```

## 📝 Example Response

```json
{
  "message": "Found 10 similar code chunks",
  "query_code_length": 87,
  "results": [
    {
      "chunk": "def factorial(n):\n    if n == 0:\n        return 1\n    else:\n        return n * factorial(n-1)",
      "metadata": {
        "file_path": "/app/repositories/py/example_repo/math_utils.py",
        "file_name": "math_utils.py",
        "file_extension": "py",
        "file_size": 421,
        "chunk_index": 3,
        "total_chunks": 12,
        "token_count": 28
      },
      "distance": 0.03241,
      "similarity": 0.96759,
      "category": "high"
    },
    // Additional similar code chunks...
  ],
  "plagiarism_analysis": {
    "summary": "Potential plagiarism detected with high similarity",
    "plagiarism_detected": true,
    "high_similarity_count": 3,
    "medium_similarity_count": 5,
    "low_similarity_count": 2
  }
}
```

---

## 📄 License

Licensed under the [MIT License](LICENSE)