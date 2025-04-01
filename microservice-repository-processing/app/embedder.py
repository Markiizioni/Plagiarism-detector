import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
import torch
from transformers import AutoModel, AutoTokenizer
import numpy as np
from dotenv import load_dotenv

from app.utils import get_all_code_files, chunk_code, num_tokens_from_string

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# CodeBERT configuration
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "microsoft/codebert-base")
MAX_TOKENS_PER_CHUNK = int(os.getenv("MAX_TOKENS_PER_CHUNK", "510"))  # CodeBERT has 512 token limit (including special tokens)
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Initialize CodeBERT model and tokenizer
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME).to(DEVICE)
    model.eval()
    logger.info(f"Loaded CodeBERT model: {MODEL_NAME} on {DEVICE}")
except Exception as e:
    logger.error(f"Failed to load CodeBERT model: {str(e)}")
    tokenizer = None
    model = None

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_embedding(text: str) -> List[float]:
    """
    Generate an embedding for the given text using CodeBERT.
    """
    if model is None or tokenizer is None:
        logger.error("CodeBERT model or tokenizer not initialized.")
        return []

    try:
        # Truncate to avoid exceeding token limit
        if len(text) > 10000:  # Roughly estimate character limit
            logger.warning(f"Text is too long ({len(text)} chars), truncating...")
            text = text[:10000]
        
        # Tokenize and generate embedding
        inputs = tokenizer(text, return_tensors="pt", truncation=True, 
                           max_length=MAX_TOKENS_PER_CHUNK, padding="max_length").to(DEVICE)
        
        with torch.no_grad():
            outputs = model(**inputs)
            
        # Use CLS token embedding (first token) as the representation
        embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy().flatten()
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}")
        raise

def mean_pooling(model_output, attention_mask):
    """
    Perform mean pooling on token embeddings.
    """
    token_embeddings = model_output.last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

def create_code_embeddings(file_path: str) -> List[Dict[str, Any]]:
    """
    Generate embeddings for the content of a given code file.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            code = f.read()

        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_name)[1][1:]  # Remove dot
        file_size = os.path.getsize(file_path)

        chunks = chunk_code(code, MAX_TOKENS_PER_CHUNK, CHUNK_OVERLAP)
        logger.info(f"Split {file_path} into {len(chunks)} chunks")

        return [
            {
                "chunk": chunk,
                "embedding": get_embedding(chunk),
                "metadata": {
                    "file_path": file_path,
                    "file_name": file_name,
                    "file_extension": file_extension,
                    "file_size": file_size,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "token_count": num_tokens_from_string(chunk)
                }
            }
            for i, chunk in enumerate(chunks)
        ]
    except Exception as e:
        logger.error(f"Failed to process {file_path}: {str(e)}")
        return []

def process_directory_for_embeddings(directory: str) -> List[Dict[str, Any]]:
    """
    Process all code files in a directory to generate embeddings.
    """
    try:
        code_files = get_all_code_files(directory)
        logger.info(f"Found {len(code_files)} code files in {directory}")

        all_embeddings = []
        for file_path in code_files:
            embeddings = create_code_embeddings(file_path)
            all_embeddings.extend(embeddings)
            logger.info(f"Created {len(embeddings)} embeddings for {file_path}")

        return all_embeddings
    except Exception as e:
        logger.error(f"Error processing directory {directory}: {str(e)}")
        return []

def process_repositories_for_embeddings() -> List[Dict[str, Any]]:
    """
    Process all code files in the /repositories directory.
    """
    repo_dir = os.path.join(os.getcwd(), "repositories")
    if not os.path.exists(repo_dir):
        logger.warning(f"Repositories directory does not exist: {repo_dir}")
        return []

    return process_directory_for_embeddings(repo_dir)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    embeddings = process_repositories_for_embeddings()
    logger.info(f"Created a total of {len(embeddings)} embeddings")