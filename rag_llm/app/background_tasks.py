import os
import json
import time
import logging
from typing import Dict, Optional, List
import threading

# Configure logging
logger = logging.getLogger(__name__)

# Progress file path
PROGRESS_FILE = os.path.join(os.getcwd(), "progress.json")

# Initialize progress data
def init_progress():
    progress_data = {
        "status": "idle",
        "processed_files": 0,
        "total_files": 0,
        "current_file": "",
        "start_time": None,
        "last_update": time.time()
    }
    save_progress(progress_data)
    return progress_data

# Load progress from file
def load_progress() -> Dict:
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        else:
            return init_progress()
    except Exception as e:
        logger.error(f"Error loading progress: {str(e)}")
        return init_progress()

# Save progress to file
def save_progress(progress_data: Dict):
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress_data, f)
    except Exception as e:
        logger.error(f"Error saving progress: {str(e)}")

# Update progress
def update_progress(status=None, processed_files=None, total_files=None, current_file=None):
    progress_data = load_progress()
    
    if status is not None:
        progress_data["status"] = status
    if processed_files is not None:
        progress_data["processed_files"] = processed_files
    if total_files is not None:
        progress_data["total_files"] = total_files
    if current_file is not None:
        progress_data["current_file"] = current_file
    
    # Update timestamp
    progress_data["last_update"] = time.time()
    
    # Set start time if this is the beginning of a process
    if status in ["cloning", "embedding"] and progress_data.get("start_time") is None:
        progress_data["start_time"] = time.time()
    
    # Reset start time if process is complete
    if status == "idle":
        progress_data["start_time"] = None
    
    save_progress(progress_data)
    return progress_data

# Format time (seconds)
def format_time(seconds):
    """Format seconds into a human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        return f"{seconds / 60:.1f} minutes"
    else:
        return f"{seconds / 3600:.1f} hours"
    
# Thread functions
def run_clone_thread(repo_urls: Optional[List[str]] = None, embed: bool = True):
    """
    Thread function to handle repository cloning and embedding.
    """
    try:
        logger.info("Starting repository cloning in thread")
        update_progress(status="cloning", current_file="Initializing")
        
        # Import here to avoid circular imports
        from app.clone_and_process import clone_repositories
        from app.cleanup import cleanup_repositories
        from app.utils import get_all_code_files
        # Import from codebert_embedder instead of embedder
        from app.codebert_embedder import create_code_embeddings
        
        # Set repository URLs if provided
        if repo_urls:
            os.environ["GITHUB_REPOSITORIES"] = ",".join(repo_urls)
        
        # Clone repositories
        repo_paths = clone_repositories()
        logger.info(f"Cloned {len(repo_paths)} repositories")
        
        if embed:
            # Count files for progress tracking
            repos_dir = os.path.join(os.getcwd(), "repositories")
            files = get_all_code_files(repos_dir)
            total_files = len(files)
            update_progress(total_files=total_files, current_file="Found code files")
            
            # Process embeddings
            update_progress(status="embedding")
            processed_files = 0
            all_embeddings = []
            
            # Import vector_store here to avoid circular imports
            from app.main import vector_store
            
            for file in files:
                current = os.path.basename(file)
                update_progress(current_file=current, processed_files=processed_files)
                logger.info(f"Processing {current} ({processed_files}/{total_files})")
                
                # Create embeddings using CodeBERT
                file_embeddings = create_code_embeddings(file)
                all_embeddings.extend(file_embeddings)
                processed_files += 1
                update_progress(processed_files=processed_files)
            
            # Add to vector store
            if all_embeddings:
                update_progress(current_file="Saving to vector store")
                vector_store.add_embeddings(all_embeddings)
                vector_store.save()
                logger.info(f"Added {len(all_embeddings)} embeddings to vector store")
        
        # Clean up
        update_progress(current_file="Cleaning up")
        cleanup_repositories(repo_paths)
        
        # Mark as complete
        update_progress(status="idle", current_file="Complete")
        logger.info("Clone process completed")
    except Exception as e:
        logger.error(f"Error in clone process: {str(e)}")
        update_progress(status="error", current_file=f"Error: {str(e)}")
        # Reset after a few seconds
        time.sleep(5)
        update_progress(status="idle")

def run_embedding_thread():
    """
    Thread function to handle embedding process.
    """
    try:
        logger.info("Starting embedding process in thread")
        
        # Import here to avoid circular imports
        from app.utils import get_all_code_files
        # Import from codebert_embedder instead of embedder
        from app.codebert_embedder import create_code_embeddings
        from app.main import vector_store
        
        # Count and collect code files for processing
        repositories_dir = os.path.join(os.getcwd(), "repositories")
        all_code_files = get_all_code_files(repositories_dir)
        total_files = len(all_code_files)
        update_progress(total_files=total_files, current_file="Found code files")
        
        if total_files > 0:
            # Process files individually to track progress
            all_embeddings = []
            for index, file_path in enumerate(all_code_files):
                filename = os.path.basename(file_path)
                logger.info(f"Processing file: {filename} ({index+1}/{total_files})")
                update_progress(processed_files=index+1, current_file=filename)
                
                # Create embeddings for this file using CodeBERT
                file_embeddings = create_code_embeddings(file_path)
                all_embeddings.extend(file_embeddings)
                
                # Log progress at certain intervals
                if (index + 1) % 10 == 0 or (index + 1) == total_files:
                    percentage = (index + 1) / total_files * 100
                    logger.info(f"Progress: {index+1}/{total_files} files ({percentage:.1f}%)")
            
            # Save embeddings to vector store
            if all_embeddings:
                update_progress(current_file="Adding embeddings to vector store")
                vector_store.add_embeddings(all_embeddings)
                
                update_progress(current_file="Saving vector store")
                vector_store.save()
                logger.info(f"Created embeddings for {len(all_embeddings)} code chunks")
            else:
                logger.warning("No embeddings were created")
        else:
            logger.warning("No code files found to process")
        
        # Mark process as complete
        update_progress(status="idle", processed_files=total_files, current_file="Complete")
        logger.info("Embedding process completed successfully")
    except Exception as e:
        logger.error(f"Error in embedding process: {str(e)}")
        update_progress(status="error", current_file=f"Error: {str(e)}")
        # Wait a bit then reset status
        time.sleep(5)
        update_progress(status="idle")