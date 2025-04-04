# 🤖 Combined Code Plagiarism Detection Microservice

This microservice implements a hybrid approach to detect code plagiarism using both **vector similarity search** and **LLM-based reasoning**. It connects to a vector-based code processing microservice and uses OpenAI to perform deep analysis over similar code chunks.

---

## 🔍 Key Features

- **Clone & process repositories** using a separate microservice
- **Generate embeddings** via CodeBERT
- **Retrieve similar code chunks** from a FAISS vector store
- **Analyze similarity** with OpenAI LLMs (e.g., GPT-3.5)
- **Dockerized for ease of deployment**

---

## 🔁 Workflow Overview

```
Client Input Code
        ↓
Get Embedding from Processing Microservice
        ↓
Search Similar Code Chunks
        ↓
Analyze Chunks with OpenAI LLM
        ↓
Return Analysis (plagiarism_detected, confidence, reasoning)
```

---

## 📦 API Endpoints

| Method | Endpoint              | Description                                 |
|--------|-----------------------|---------------------------------------------|
| GET    | `/`                   | Health check                                |
| POST   | `/clone-and-process`  | Trigger repository clone & embedding        |
| POST   | `/check-plagiarism`   | Send code and receive plagiarism analysis   |

---

## 🛠️ Usage with Docker

### 1. Set up `.env`

```env
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.0
PROCESSING_SERVICE_URL=http://host.docker.internal:8000
```

### 2. Docker Compose

If used with another container on port 8000 (processing service), expose this service on another port (e.g. 8001):

```yaml
services:
  combined-approach-service:
    build:
      context: .
    ports:
      - "8001:8000"
    volumes:
      - .:/app
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

- Accepts code as input (`/check-plagiarism`)
- Sends it to a processing microservice for embedding
- Searches for similar code in FAISS
- Sends query + results to an OpenAI LLM
- Returns a structured JSON analysis

---

## 📁 File Structure

```
.
├── app/
│   ├── main.py                  # FastAPI app
│   ├── llm_plagiarism_detector.py  # OpenAI-based analyzer
│   ├── utils.py                 # Code normalization
├── .env                         # API keys & config
├── Dockerfile                   # Container instructions
├── docker-compose.yml           # Multi-container setup
├── README.md                    # This documentation
```

---

## 📄 License

Licensed under the [MIT License](LICENSE)