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

from app.similarity_threshold import SimilarityAnalyzer

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

# Initialize similarity analyzer with default thresholds

similarity_analyzer = SimilarityAnalyzer(
    high_similarity_threshold=float(os.getenv("HIGH_SIMILARITY_THRESHOLD", "0.85")),
    medium_similarity_threshold=float(os.getenv("MEDIUM_SIMILARITY_THRESHOLD", "0.70")),
    low_similarity_threshold=float(os.getenv("LOW_SIMILARITY_THRESHOLD", "0.55"))
)

# Try to load existing vector store on startup
try:
    vector_store.load()
    logger.info("Loaded existing vector store")
except Exception as e:
    logger.warning(f"Could not load vector store: {str(e)}")

class RepositoryRequest(BaseModel):
    repo_urls: list[str] = []
    
class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    analyze_plagiarism: bool = False  # New field to control plagiarism analysis

class CodeSimilarityRequest(BaseModel):
    code: str
    top_k: int = 10
    analyze_plagiarism: bool = True  # Default to true for code similarity checks

class ThresholdConfig(BaseModel):
    high_threshold: float = 0.85
    medium_threshold: float = 0.70
    low_threshold: float = 0.55

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

async def run_embedding_in_thread():
    """
    Run the embedding process in a separate thread to avoid blocking the API.
    """
    thread = threading.Thread(target=run_embedding_thread)
    thread.daemon = True
    thread.start()
    logger.info("Started embedding process in background thread")
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
        
        # Update status to cloning
        update_progress(status="cloning", processed_files=0, total_files=0, current_file="Initializing")
        
        # Run the cloning in the background using a thread
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

@app.post("/search")
async def search_code(query_request: QueryRequest):
    """
    Search for code chunks similar to the query.
    
    Args:
        query_request: Query request containing query text and top_k
    """
    try:
        # Check if vector store is loaded
        if vector_store.index is None:
            # Try loading it
            try:
                loaded = vector_store.load()
                if not loaded:
                    return {"message": "Vector store is empty or not initialized", "results": []}
            except Exception as e:
                logger.error(f"Failed to load vector store: {str(e)}")
                return {"message": "Failed to load vector store", "results": []}
        
        # Get embedding for the query
        query_embedding = get_embedding(query_request.query)
        
        # Search for similar code chunks
        results = vector_store.search(query_embedding, query_request.top_k)
        
        # Apply plagiarism analysis if requested
        if query_request.analyze_plagiarism:
            plagiarism_analysis = similarity_analyzer.analyze_search_results(results)
            return {
                "message": f"Found {len(results)} similar code chunks",
                "query": query_request.query,
                "results": plagiarism_analysis["results"],
                "plagiarism_analysis": {
                    "summary": plagiarism_analysis["analysis"],
                    "plagiarism_detected": plagiarism_analysis["plagiarism_detected"],
                    "suspicious": plagiarism_analysis.get("suspicious", False),
                    "high_similarity_count": plagiarism_analysis["high_similarity_count"],
                    "medium_similarity_count": plagiarism_analysis["medium_similarity_count"],
                    "low_similarity_count": plagiarism_analysis["low_similarity_count"]
                }
            }
        else:
            return {
                "message": f"Found {len(results)} similar code chunks",
                "query": query_request.query,
                "results": results
            }
    except Exception as e:
        logger.error(f"Error searching code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/embed")
async def embed_repositories(background_tasks: BackgroundTasks):
    """
    Create embeddings for all code files in the repositories directory.
    This is useful when you've already cloned repositories but want to update embeddings.
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
        # Update status to embedding
        update_progress(status="embedding", processed_files=0, total_files=0, current_file="Initializing")
        
        # Run the embedding in the background using a thread
        background_tasks.add_task(run_embedding_in_thread)
        
        return {
            "message": "Repository embedding started",
            "status": "processing"
        }
    except Exception as e:
        update_progress(status="idle")
        logger.error(f"Error starting repository embedding: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start repository embedding: {str(e)}")

@app.post("/similar-code")
async def find_similar_code(request: CodeSimilarityRequest):
    """
    Find code chunks similar to the provided code snippet.
    
    Args:
        request: Code similarity request containing the code and top_k
    """
    # Ensure vector store is loaded
    if vector_store.index is None:
        loaded = False
        try:
            loaded = vector_store.load()
        except Exception as e:
            logger.error(f"Failed to load vector store: {str(e)}")
            return {"message": "Failed to load vector store", "results": []}
        
        if not loaded:
            return {"message": "Vector store is empty or not initialized", "results": []}

    try:
        # Get embedding for the code
        code_embedding = get_embedding(request.code)
        
        # Search for similar code chunks
        results = vector_store.search(code_embedding, request.top_k)
        
        # Apply plagiarism analysis if requested (default is True for this endpoint)
        if request.analyze_plagiarism:
            plagiarism_analysis = similarity_analyzer.analyze_search_results(results)
            summary = similarity_analyzer.get_plagiarism_summary("Submitted code", plagiarism_analysis)
            
            return {
                "message": f"Found {len(results)} similar code chunks",
                "query_code_length": len(request.code),
                "results": plagiarism_analysis["results"],
                "plagiarism_analysis": {
                    "summary": plagiarism_analysis["analysis"],
                    "human_readable_summary": summary,
                    "plagiarism_detected": plagiarism_analysis["plagiarism_detected"],
                    "suspicious": plagiarism_analysis.get("suspicious", False),
                    "high_similarity_count": plagiarism_analysis["high_similarity_count"],
                    "medium_similarity_count": plagiarism_analysis["medium_similarity_count"],
                    "low_similarity_count": plagiarism_analysis["low_similarity_count"]
                }
            }
        else:
            return {
                "message": f"Found {len(results)} similar code chunks",
                "query_code_length": len(request.code),
                "results": results
            }

    except Exception as e:
        logger.error(f"Error finding similar code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)