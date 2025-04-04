# 🧠 Code Plagiarism Detection System

This project explores different approaches for detecting plagiarism in source code, aiming to provide a scalable and intelligent solution for identifying reused or copied code across public repositories.

## 🎯 Goal

To build a modular system that can analyze a given code snippet and determine whether it is plagiarized, using a combination of traditional similarity-based techniques and modern language models.

## 🧪 Approaches Used

The system is implemented in three progressively more advanced variations:

1. **LLM-Only Detection**  
   Directly asks a large language model whether the provided code appears to be plagiarized, without external context.

2. **Vector Similarity Detection**  
   Compares the input code against a collection of embedded code snippets from real repositories using vector similarity and a plagiarism threshold.

3. **Hybrid Retrieval-Augmented LLM Detection**  
   Retrieves the most similar code snippets from a vector store and sends them along with the input to a language model, which makes a more informed plagiarism decision.

## 🏗️ Project Structure

```
plagiarism-detector/
├── .venv/                         # Virtual environment
├── evaluation/                    # Evaluation tools and results
├── microservice-clone-and-process/  # Preprocessing and indexing service
├── microservice-combined-approach/  # Hybrid retrieval-augmented LLM approach
├── microservice-llm-evaluator/    # LLM-only approach
├── microservice-threshold-evaluator/ # Vector similarity threshold approach
├── docker-compose.yml            # Main compose file for all services
└── requirements.txt              # Common dependencies
```

## 🚀 Getting Started


1. Start the services:
   ```bash
   docker-compose up -d
   ```

3. Access the services:
   - Combined approach: http://localhost:8001/check-plagiarism
   - LLM-only: http://localhost:8002/check
   - Threshold approach: http://localhost:8003/search-similar

## 🔬 Running Evaluations

The `evaluation` directory contains a Docker-based tool for comprehensive evaluation:

```bash
cd evaluation
chmod +x run.sh
./run.sh
```

For more detailed evaluation with more test cases:
```bash
LIMIT=50 ./run.sh  # Evaluates on 50 test cases
LIMIT=0 ./run.sh   # Evaluates on all test cases
```

## 🔍 Use Cases

- Academic integrity verification
- Open source license compliance
- Internal code quality assurance
- Programming education