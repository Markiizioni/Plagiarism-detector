# 🔍 Vector Similarity-Based Code Plagiarism Detection

This module implements a more sophisticated approach to code plagiarism detection by comparing code against a repository of known code samples using embeddings and vector similarity.

A semantic code plagiarism detection system that uses embeddings (via CodeBERT) and FAISS similarity search to find and analyze code reuse across known repositories.

## 🧩 How It Works

1. The system clones repositories defined in environment variables or provided via API
2. Source code files are automatically extracted and categorized by programming language
3. By default, all extracted code is normalized, chunked, embedded, and stored in a FAISS vector database
4. The status API provides detailed information about how many files of each language were processed
5. When new code is submitted for checking, it's normalized, embedded, and compared against the vector database
6. Similarity scores are calculated and analyzed using configurable thresholds
7. A detailed plagiarism analysis report is generated based on the findings

## 🏗️ Architecture

The system consists of multiple components:

- **Repository Management**: Clones GitHub repositories and extracts code files
- **Code Normalization**: Standardizes code by removing comments, whitespace variations, and case sensitivity
- **Code Processing**: Chunks normalized code into smaller segments for more precise comparison
- **Embedding Generation**: Creates vector embeddings using CodeBERT
- **Vector Database**: Stores and indexes embeddings using FAISS for efficient similarity search
- **Similarity Analysis**: Evaluates search results against configurable thresholds
- **API Layer**: FastAPI endpoints for code submission and analysis

## 🛠️ Setup and Installation

### Prerequisites
- Python 3.8+
- CUDA-compatible GPU (optional, for faster embedding generation)

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env file with your configuration
```

### Environment Variables
```
# Repository Sources
GITHUB_REPOSITORIES=https://github.com/repo1/example,https://github.com/repo2/example

# Embedding Configuration
EMBEDDING_MODEL=microsoft/codebert-base
MAX_TOKENS_PER_CHUNK=510
CHUNK_OVERLAP=100

# Similarity Thresholds
HIGH_SIMILARITY_THRESHOLD=0.85
MEDIUM_SIMILARITY_THRESHOLD=0.70
LOW_SIMILARITY_THRESHOLD=0.55
```

## 🚀 Usage

### Starting the Service
```bash
uvicorn main:app --reload
```

### API Endpoints

#### 1. Code Similarity Check
```bash
curl -X POST http://localhost:8000/similar-code \
  -H "Content-Type: application/json" \
  -d '{
    "code": "YOUR_CODE_HERE",
    "top_k": 10,
    "analyze_plagiarism": true
  }'
```

#### 2. Managing Code Repository
```bash
# Clone and process repositories (extract, normalize, and embed - default behavior)
curl -X POST http://localhost:8000/clone-and-process

# Clone and process repositories without generating embeddings
curl -X POST http://localhost:8000/clone-and-process?embed=false

# Check status of repositories and vector store (shows file counts by language)
curl -X GET http://localhost:8000/status

# Manually generate embeddings (only needed if cloning was done with embed=false)
curl -X POST http://localhost:8000/embed
```

### Response Format

#### Status Response
```json
{
  "status": "Repositories processed",
  "directory_checked": "/path/to/repositories",
  "items_in_directory": ["py", "js", "java", "cpp"],
  "file_extensions": {
    "py": 120,
    "js": 85,
    "java": 230,
    "cpp": 45
  },
  "total_files": 480,
  "vector_store_stats": {
    "total_embeddings": 1450,
    "vector_dimension": 768,
    "file_extensions": ["py", "js", "java", "cpp"],
    "total_files": 480,
    "total_tokens": 325000
  },
  "processing_status": "idle"
}
```

#### Similarity Check Response
The API returns a JSON object with:
- Overall plagiarism detection result
- Human-readable summary
- Detailed matches categorized by similarity level
- Code chunks that match the query with similarity scores

## ⚙️ Implementation Details

### Code Normalization
- Removes comments (single-line, multi-line, and docstrings)
- Converts code to lowercase
- Normalizes whitespace and indentation
- Makes it harder to evade detection with superficial changes

### Code Embedding
- Uses Microsoft's CodeBERT model for code-specific embeddings
- Code is chunked into smaller segments with overlaps to capture context
- Each chunk is embedded into a 768-dimensional vector space

### Vector Store
- FAISS (Facebook AI Similarity Search) for efficient similarity search
- L2 distance normalized into similarity scores (1.0 = identical, 0.0 = completely different)
- Persists embeddings to disk for reuse across service restarts

### Similarity Analysis
- Three configurable thresholds:
  - **High similarity (default: ≥0.85)**: Likely plagiarism
  - **Medium similarity (default: ≥0.70)**: Suspicious
  - **Low similarity (default: ≥0.55)**: Potentially coincidental

## ⚖️ Advantages and Limitations

### Advantages
- Detects plagiarism against a known repository of code
- More precise than pure LLM-based approaches
- Provides evidence and similarity scores for each match
- Configurable thresholds for different sensitivity levels
- Scales efficiently with FAISS indexing
- Normalizes code to catch attempts at obfuscation

### Limitations
- Can only detect plagiarism from repositories it has indexed
- Requires periodic updates to keep repository data current
- Higher computational and storage requirements than LLM-only approach
- Chunks may cross logical boundaries in code, affecting similarity
- Language-specific nuances may not be fully captured
- Code normalization may occasionally miss sophisticated obfuscation techniques

## 📊 Performance

- Typical processing speed: ~200 code files per minute
- Typical search performance: <100ms per query
- Storage requirements: ~100MB per 10,000 code chunks
- Recommended minimum RAM: 4GB (16GB+ recommended for large repositories)

## 🔄 Next Steps

- Improve chunking strategy to better preserve code semantics
- Add support for language-specific tokenization
- Implement incremental updates to avoid full repository reprocessing
- Explore fine-tuning CodeBERT for plagiarism detection
- Integrate with the hybrid approach for more accurate results