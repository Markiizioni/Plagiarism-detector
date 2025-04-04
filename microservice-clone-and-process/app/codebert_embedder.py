import os
import logging
from typing import List, Dict, Any
import torch
from transformers import AutoTokenizer, AutoModel
from tenacity import retry, stop_after_attempt, wait_exponential

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

# Initialize tokenizer and model
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME).to(DEVICE)
    model.eval()  # Set model to evaluation mode
    logger.info(f"Loaded CodeBERT model {MODEL_NAME} on {DEVICE}")
except Exception as e:
    logger.error(f"Failed to load CodeBERT model: {str(e)}")
    tokenizer = None
    model = None

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_embedding(text: str) -> List[float]:
    """
    Retrieve an embedding for the given code text using CodeBERT.
    """
    if tokenizer is None or model is None:
        logger.error("CodeBERT model not initialized correctly.")
        return []

    try:
        # Truncate text if too long (optional, as chunking should handle this)
        if len(text) > 10000:  # Arbitrary limit to prevent very long texts
            logger.warning(f"Text too long ({len(text)} chars), truncating")
            text = text[:10000]
        
        # Tokenize and get model inputs
        inputs = tokenizer(text, return_tensors="pt", truncation=True, 
                          max_length=MAX_TOKENS_PER_CHUNK, padding=True)
        inputs = {key: val.to(DEVICE) for key, val in inputs.items()}
        
        # Get embeddings with no gradient calculation needed
        with torch.no_grad():
            outputs = model(**inputs)
            
        # Use the [CLS] token embedding as the code representation
        embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()[0]
        
        # Convert to standard Python list and normalize (optional)
        embedding_list = embeddings.tolist()
        
        # Normalize the embedding 
        norm = torch.norm(torch.tensor(embedding_list), p=2).item()
        if norm > 0:
            embedding_list = [x / norm for x in embedding_list]
            
        return embedding_list
    except Exception as e:
        logger.error(f"Embedding request failed: {str(e)}")
        raise

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

        # Use CodeBERT tokenizer to count tokens (different from tiktoken)
        def count_tokens(text):
            return len(tokenizer.encode(text))

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
                    "token_count": count_tokens(chunk)
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