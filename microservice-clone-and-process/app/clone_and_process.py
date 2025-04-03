import os
import git
import tempfile
import logging
import shutil
from typing import List, Dict
from dotenv import load_dotenv

from app.utils import is_valid_code_file, get_file_extension, normalize_code

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

def get_repository_urls() -> List[str]:
    """
    Retrieve repository URLs from the GITHUB_REPOSITORIES environment variable.
    """
    repo_urls = os.getenv("GITHUB_REPOSITORIES", "").split(",")
    return [url.strip() for url in repo_urls if url.strip()]

def create_directory_structure() -> str:
    """
    Create the base directory for storing categorized code files.
    """
    base_dir = os.path.join(os.getcwd(), "repositories")
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    return base_dir

def clone_repository(repo_url: str) -> str:
    """
    Clone a single GitHub repository into a temporary directory.
    
    Args:
        repo_url: The GitHub URL to clone.
        
    Returns:
        Path to the cloned repository, or None if failed.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        logger.info(f"Cloning repository: {repo_url}")
        git.Repo.clone_from(repo_url, temp_dir)
        return temp_dir
    except Exception as e:
        logger.error(f"Failed to clone repository {repo_url}: {str(e)}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None



def extract_code_files(repo_path: str, base_dir: str) -> Dict[str, List[str]]:
    categorized_files = {}
    if not repo_path:
        return categorized_files

    repo_name = os.path.basename(repo_path)

    for root, _, files in os.walk(repo_path):
        # Skip hidden directories like .git
        if any(part.startswith('.') for part in root.split(os.sep)):
            continue

        for file in files:
            file_path = os.path.join(root, file)
            if not is_valid_code_file(file_path):
                continue

            ext = get_file_extension(file)
            ext_dir = os.path.join(base_dir, ext)
            os.makedirs(ext_dir, exist_ok=True)

            # Read and normalize the file content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    normalized_code = normalize_code(f.read())
                
                rel_path = os.path.relpath(file_path, repo_path)
                new_file_name = f"{repo_name}_{rel_path.replace(os.sep, '_')}"
                new_file_path = os.path.join(ext_dir, new_file_name)

                # Write normalized code
                with open(new_file_path, 'w', encoding='utf-8') as f:
                    f.write(normalized_code)

                categorized_files.setdefault(ext, []).append(new_file_path)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")

    return categorized_files

def clone_repositories() -> List[str]:
    """
    Clone all repositories defined in the environment and extract code files.
    
    Returns:
        A list of local paths to successfully cloned repositories.
    """
    repo_urls = get_repository_urls()
    if not repo_urls:
        logger.warning("No repository URLs found in environment variables")
        return []

    base_dir = create_directory_structure()
    cloned_paths = []

    for url in repo_urls:
        repo_path = clone_repository(url)
        if not repo_path:
            continue

        cloned_paths.append(repo_path)
        categorized = extract_code_files(repo_path, base_dir)
        for ext, files in categorized.items():
            logger.info(f"Extracted {len(files)} {ext} files from {url}")

    return cloned_paths

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    clone_repositories()