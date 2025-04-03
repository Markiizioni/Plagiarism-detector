import os
import logging
from typing import List, Dict, Callable, Optional
import magic
import tiktoken
import json
import time
import re 

# Configure logging
logger = logging.getLogger(__name__)

# Constants
CODE_EXTENSIONS = {
    "py", "js", "ts", "jsx", "tsx", "java", "c", "cpp", "h", "hpp", 
    "cs", "go", "rb", "rs", "php", "html", "css", "scss", "sql", 
    "yaml", "yml", "json", "xml", "md", "sh", "bash", "kt", "swift"
}

IGNORED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "bmp", "svg", "ico", "tif", "tiff",
    "mp3", "mp4", "wav", "avi", "mov", "mkv", "flv", "wmv",
    "zip", "tar", "gz", "rar", "7z", "jar", "war", "ear",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "bin", "exe", "dll", "so", "class", "o", "pyc"
}

MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB


def normalize_code(code: str) -> str:
    """
    Normalize code by:
    - Removing comments
    - Converting to lowercase
    - Normalizing indentation and whitespace
    """
    if not isinstance(code, str):
        code = str(code)

    # Remove single-line comments
    code = re.sub(r'(//.*?$)|(#.*?$)', '', code, flags=re.MULTILINE)
    
    # Remove multi-line comments
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    
    # Remove docstrings
    code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
    code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
    
    # Normalize indentation (convert to spaces, standardize)
    lines = [line.strip() for line in code.split('\n') if line.strip()]
    
    # Convert to lowercase
    lines = [line.lower() for line in lines]
    
    # Normalize indentation
    return '\n'.join(lines)


def get_file_extension(file_path: str) -> str:
    """Returns the file extension (without dot), or filename if none."""
    _, ext = os.path.splitext(file_path)
    return ext[1:].lower() if ext else os.path.basename(file_path)


def is_binary_file(file_path: str) -> bool:
    """Detects if a file is binary using python-magic."""
    try:
        file_type = magic.from_file(file_path, mime=True)
        return not file_type.startswith(('text/', 'application/json', 'application/xml'))
    except Exception as e:
        logger.error(f"Error checking if file is binary: {str(e)}")
        return True  # Assume binary if detection fails


def is_valid_code_file(file_path: str) -> bool:
    """Checks if the given file should be treated as code."""
    ext = get_file_extension(file_path)

    if ext in IGNORED_EXTENSIONS:
        return False
    if ext not in CODE_EXTENSIONS:
        return False
    if is_binary_file(file_path):
        return False
    if os.path.getsize(file_path) > MAX_FILE_SIZE_BYTES:
        logger.warning(f"File {file_path} is too large (>1MB), skipping")
        return False

    return True


def get_all_code_files(directory: str) -> List[str]:
    """Recursively collects all valid code files from the given directory."""
    code_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)
            if is_valid_code_file(path):
                code_files.append(path)
    return code_files


def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a string using the specified encoding."""
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(string))


def count_tokens_with_huggingface(string: str, tokenizer) -> int:
    """
    Returns the number of tokens in a string using a HuggingFace tokenizer.
    This is a fallback for when we need to use the CodeBERT tokenizer.
    """
    if not string.strip():
        return 0
    return len(tokenizer.encode(string))


def chunk_code(
    code: str, 
    chunk_size: int = 510, 
    chunk_overlap: int = 100, 
    token_counter: Optional[Callable[[str], int]] = None
) -> List[str]:
    """
    Splits code into overlapping chunks of tokens, ideally aligned to newlines.
    
    Args:
        code: The code string to split.
        chunk_size: Max tokens per chunk.
        chunk_overlap: Tokens to overlap between chunks.
        token_counter: Function to count tokens (defaults to tiktoken)

    Returns:
        List of chunked code strings.
    """
    # Use the provided token counter or default to tiktoken
    counter = token_counter or num_tokens_from_string
    
    if counter(code) <= chunk_size:
        return [code]

    lines = code.split('\n')
    chunks = []
    current_chunk = []
    current_size = 0

    for line in lines:
        line_size = counter(line + '\n')

        if current_size + line_size > chunk_size and current_chunk:
            chunks.append('\n'.join(current_chunk))

            # Build overlap
            overlap_size = 0
            overlap_lines = []
            for prev_line in reversed(current_chunk):
                size = counter(prev_line + '\n')
                if overlap_size + size <= chunk_overlap:
                    overlap_lines.insert(0, prev_line)
                    overlap_size += size
                else:
                    break

            current_chunk = overlap_lines
            current_size = overlap_size

        current_chunk.append(line)
        current_size += line_size

    if current_chunk:
        chunks.append('\n'.join(current_chunk))

    return chunks