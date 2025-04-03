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
code-plagiarism-detection/
├── llm-only/               # Direct LLM approach
├── vector-similarity/      # Vector database approach 
├── hybrid-retrieval/       # Vector + LLM approach
└── common/                 # Shared utilities and components
```


## 📊 Evaluation

Approaches are evaluated based on:
- Accuracy in detecting real plagiarism cases
- False positive rate
- Computational efficiency
- Scalability with increasing repository size

## 🔍 Use Cases

- Academic integrity verification
- Open source license compliance
- Internal code quality assurance
- Programming education

## 🤝 Contributing

Contributions are welcome! See the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines.

---

Each approach folder contains a detailed README with setup instructions and architectural explanations.