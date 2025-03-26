import os
import logging
from typing import List, Dict, Any
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from dotenv import load_dotenv
from app.utils import get_all_code_files, chunk_code, num_tokens_from_string

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
MAX_TOKENS_PER_CHUNK = int(os.getenv("MAX_TOKENS_PER_CHUNK", "4000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_embedding(text: str) -> List[float]:
    """
    Retrieve an embedding for the given text using OpenAI.
    """
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key not found. Please set OPENAI_API_KEY in your environment.")
        return []

    try:
        response = client.embeddings.create(input=text, model=EMBEDDING_MODEL)
        return response.data[0].embedding
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
