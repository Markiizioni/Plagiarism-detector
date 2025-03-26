from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import asyncio
import time
import threading
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import logging

from app.clone_and_process import get_repository_urls
from app.cleanup import cleanup_processed_files
from app.embedder import get_embedding
from app.vector_store import create_vector_store
from app.background_tasks import (
    init_progress, 
    load_progress, 
    update_progress, 
    format_time,
    run_clone_thread,
    run_embedding_thread
)
from app.llm_plagiarism_detector import LLMPlagiarismDetector

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize progress on startup
init_progress()

app = FastAPI(title="Repository Processing Microservice")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize vector store
vector_store = create_vector_store()

# Initialize LLM-based plagiarism detector
llm_detector = LLMPlagiarismDetector(
    model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
    temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.0"))
)

# Try to load existing vector store on startup
try:
    vector_store.load()
    logger.info("Loaded existing vector store")
except Exception as e:
    logger.warning(f"Could not load vector store: {str(e)}")

class RepositoryRequest(BaseModel):
    repo_urls: list[str] = []
    
class PlagiarismCheckRequest(BaseModel):
    code: str
    top_k: int = 5  # Number of similar code chunks to check

# Async thread wrapper functions
async def run_clone_pipeline_in_thread(embed=True):
    """
    Run the cloning pipeline in a separate thread to avoid blocking the API.
    """
    thread = threading.Thread(target=run_clone_thread, args=(None, embed))
    thread.daemon = True
    thread.start()
    logger.info("Started clone process in background thread")
    return

@app.get("/")
async def root():
    return {"message": "Repository Processing Microservice", "status": "running"}

@app.post("/clone")
async def clone_repos(
    background_tasks: BackgroundTasks, 
    request: RepositoryRequest = None,
    embed: bool = True
):
    """
    Clone repositories from GitHub URLs specified in the request or environment variables.
    Extract and categorize code files by file extension.
    
    Args:
        request: Repository request containing repo URLs
        embed: Whether to create embeddings for the code files
    """
    # Check if process is already running
    progress_data = load_progress()
    if progress_data["status"] != "idle":
        return {
            "message": "Another operation is already in progress",
            "current_status": progress_data["status"],
            "details": "Please wait for the current operation to complete"
        }
    
    try:
        if request and request.repo_urls:
            # Temporarily override environment variable
            os.environ["GITHUB_REPOSITORIES"] = ",".join(request.repo_urls)
            repo_source = "request"
        else:
            # Use environment variables
            repo_source = "environment"
        
        # ✅ Correct progress update
        update_progress(status="cloning", processed_files=0, total_files=0, current_file="Initializing")
        
        # ✅ Run cloning (and optional embedding) in background thread
        background_tasks.add_task(run_clone_pipeline_in_thread, embed)
        
        return {
            "message": "Repository cloning started",
            "repository_source": repo_source,
            "repositories": get_repository_urls(),
            "create_embeddings": embed
        }
    except Exception as e:
        update_progress(status="idle")
        logger.error(f"Error starting repository clone: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start repository clone: {str(e)}")

@app.post("/cleanup")
async def cleanup(clear_vector_store: bool = False):
    """
    Clean up processed files in the repositories directory.
    
    Args:
        clear_vector_store: Whether to clear the vector store as well
    """
    # Check if process is already running
    progress_data = load_progress()
    if progress_data["status"] != "idle":
        return {
            "message": "Another operation is already in progress",
            "current_status": progress_data["status"],
            "details": "Please wait for the current operation to complete"
        }
    
    try:
        update_progress(status="cleaning")
        
        # Clean up processed files
        cleanup_processed_files()
        
        # Clear vector store if requested
        if clear_vector_store:
            vector_store.clear()
            vector_store.save()
            logger.info("Cleared vector store")
        
        # Reset progress
        update_progress(status="idle", processed_files=0, total_files=0, current_file="")
            
        return {
            "message": "Cleaned up processed files successfully",
            "vector_store_cleared": clear_vector_store
        }
    except Exception as e:
        update_progress(status="idle")
        logger.error(f"Error during cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@app.get("/status")
async def get_status():
    """
    Get the status of processed repositories and vector store.
    """
    try:
        repositories_dir = os.path.join(os.getcwd(), "repositories")
        logger.info(f"Checking repositories directory at: {os.path.abspath(repositories_dir)}")
        
        # Check if repositories directory exists
        if not os.path.exists(repositories_dir):
            logger.warning(f"Repositories directory does not exist at: {os.path.abspath(repositories_dir)}")
            return {"status": "No repositories processed yet", "directory_checked": os.path.abspath(repositories_dir)}
        
        # List all items in the repository directory
        all_items = os.listdir(repositories_dir)
        logger.info(f"Items in repositories directory: {all_items}")
        
        # Get all extensions and file counts
        extensions = {}
        for item in all_items:
            item_path = os.path.join(repositories_dir, item)
            if os.path.isdir(item_path):
                try:
                    file_count = len(os.listdir(item_path))
                    extensions[item] = file_count
                except Exception as e:
                    logger.error(f"Error accessing directory {item_path}: {str(e)}")
        
        # Get vector store statistics
        vector_store_stats = vector_store.get_stats()
        
        # Get current progress
        progress_data = load_progress()
        
        return {
            "status": "Repositories processed",
            "directory_checked": os.path.abspath(repositories_dir),
            "items_in_directory": all_items,
            "file_extensions": extensions,
            "total_files": sum(extensions.values()) if extensions else 0,
            "vector_store_stats": vector_store_stats,
            "current_working_directory": os.getcwd(),
            "processing_status": progress_data["status"]
        }
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@app.get("/progress")
async def get_progress():
    """
    Get detailed progress information about ongoing operations.
    """
    try:
        progress_data = load_progress()
        
        # Add calculated fields
        result = dict(progress_data)
        
        # Calculate percentage
        if progress_data["total_files"] > 0:
            result["progress_percent"] = round(progress_data["processed_files"] / progress_data["total_files"] * 100, 2)
        else:
            result["progress_percent"] = 0
        
        # Calculate time metrics
        if progress_data["start_time"]:
            elapsed_seconds = time.time() - progress_data["start_time"]
            result["elapsed_time"] = {
                "seconds": round(elapsed_seconds, 1),
                "formatted": format_time(elapsed_seconds)
            }
            
            # Calculate estimated time remaining
            if progress_data["processed_files"] > 0 and progress_data["total_files"] > progress_data["processed_files"]:
                files_per_second = progress_data["processed_files"] / elapsed_seconds
                if files_per_second > 0:
                    remaining_files = progress_data["total_files"] - progress_data["processed_files"]
                    estimated_seconds = remaining_files / files_per_second
                    result["estimated_remaining"] = {
                        "seconds": round(estimated_seconds, 1),
                        "formatted": format_time(estimated_seconds)
                    }
        
        # Check if process might be stuck
        if (progress_data["status"] not in ["idle", "complete"] and 
            time.time() - progress_data["last_update"] > 300):  # 5 minutes
            result["warning"] = "Process may be stuck - no updates in the last 5 minutes"
        
        return result
    except Exception as e:
        logger.error(f"Error getting progress: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/check-plagiarism")
async def check_plagiarism(request: PlagiarismCheckRequest):
    """
    Check if the provided code is plagiarized by finding similar code chunks
    and analyzing them with an LLM.
    
    Args:
        request: Code to check for plagiarism and parameters
    """
    # Ensure vector store is loaded
    if vector_store.index is None:
        try:
            loaded = vector_store.load()
            if not loaded:
                return {"message": "Vector store is empty or not initialized", "results": []}
        except Exception as e:
            logger.error(f"Failed to load vector store: {str(e)}")
            return {"message": "Failed to load vector store", "results": []}

    try:
        # Get embedding for the code
        code_embedding = get_embedding(request.code)
        
        # Search for similar code chunks
        results = vector_store.search(code_embedding, request.top_k)
        
        # Apply LLM-based plagiarism analysis
        plagiarism_analysis = llm_detector.analyze_similarity(request.code, results)
        
        return {
            "message": f"Found {len(results)} similar code chunks",
            "code_length": len(request.code),
            "results": plagiarism_analysis["results"],
            "plagiarism_analysis": {
                "summary": plagiarism_analysis["analysis"],
                "plagiarism_detected": plagiarism_analysis["plagiarism_detected"],
                "confidence": plagiarism_analysis.get("confidence", 0.0),
                "model_used": plagiarism_analysis.get("llm_model", "unknown")
            }
        }
    except Exception as e:
        logger.error(f"Error checking plagiarism: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Plagiarism check failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)