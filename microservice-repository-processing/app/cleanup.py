import os
import shutil
import logging
from typing import List

# Configure logging
logger = logging.getLogger(__name__)

def cleanup_repositories(repo_paths: List[str]):
    """
    Delete the cloned repositories after processing.
    
    Args:
        repo_paths: List of paths to cloned repositories
    """
    for repo_path in repo_paths:
        try:
            if os.path.exists(repo_path):
                logger.info(f"Cleaning up repository: {repo_path}")
                shutil.rmtree(repo_path)
        except Exception as e:
            logger.error(f"Error cleaning up repository {repo_path}: {str(e)}")

def cleanup_processed_files():
    """
    Clean up processed files in the repositories directory.
    This is useful for manual cleanup or when restarting the process.
    """
    repositories_dir = os.path.join(os.getcwd(), "repositories")
    
    try:
        if os.path.exists(repositories_dir):
            logger.info(f"Cleaning up processed files in: {repositories_dir}")
            
            # Option 1: Delete the entire directory
            shutil.rmtree(repositories_dir)
            
            # Recreate the directory
            os.makedirs(repositories_dir)
            
            logger.info("Cleaned up all processed files")
    except Exception as e:
        logger.error(f"Error cleaning up processed files: {str(e)}")

if __name__ == "__main__":
    # For testing
    logging.basicConfig(level=logging.INFO)
    cleanup_processed_files()