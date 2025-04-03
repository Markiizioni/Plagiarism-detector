# 🤖 LLM-Only Plagiarism Detection

This module implements a simple approach to code plagiarism detection by directly asking a Large Language Model (GPT-3.5 Turbo) to determine if a code snippet appears to be plagiarized, without providing additional context from a code repository.

## 🧩 How It Works

1. User submits a code snippet via a FastAPI endpoint
2. The system formats the code into a specialized prompt
3. This prompt is sent to OpenAI's GPT-3.5 Turbo model
4. The model responds with a simple "Yes" or "No" determination
5. The result is returned directly to the user

## 🛠️ Setup and Installation

### Prerequisites
- Python 3.8+
- OpenAI API key

### Installation
```bash
# Install dependencies
pip install -r requirements.txt
```

### Configuration
Create a `.env` file in the root directory:
```
OPENAI_API_KEY=your_openai_api_key_here
```

## 🚀 Usage

### Starting the API Server
```bash
uvicorn main:app --reload
```

### Making API Requests
```bash
curl -X POST http://localhost:8000/check \
  -H "Content-Type: application/json" \
  -d '{"code": "def hello_world():\n    print(\"Hello, World!\")"}'
```

### Response Format
The API returns a plain text response with either "Yes" (plagiarized) or "No" (not plagiarized).

## 📄 Project Structure

```
microservice-llm-evaluator/
├── __pycache__/
├── .dockerignore
├── .env                 # Environment variables
├── .gitignore
├── Dockerfile
├── main.py              # FastAPI application
├── prompt.py            # Prompt generation logic
├── README.md            # This documentation
└── requirements.txt     # Project dependencies
```

## ⚙️ Implementation Details

### Prompt Design
The system uses a simple prompt template that:
- Instructs the model to act as a plagiarism detection assistant
- Provides the user's code snippet
- Requests a binary "Yes" or "No" response

### API Endpoint
The FastAPI application exposes a single `/check` endpoint that accepts JSON requests with a `code` field containing the code snippet to check.

## ⚖️ Advantages and Limitations

### Advantages
- Simple implementation with minimal setup
- Fast response time
- No need for a reference database or vector storage
- Easy to deploy and scale

### Limitations
- Relies entirely on the LLM's pre-trained knowledge
- Cannot identify plagiarism from sources outside the LLM's training data
- No evidence trail for plagiarism claims

