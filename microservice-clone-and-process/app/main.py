from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging
from typing import List, Optional
from dotenv import load_dotenv

from app.clone_and_process import clone_repositories, get_repository_urls
from app.cleanup import cleanup_processed_files
from app.codebert_embedder import create_code_embeddings
from app.vector_store import create_vector_store
from app.background_tasks import (
    init_progress,
    load_progress,
    update_progress,
    format_time,
    run_clone_thread,
    run_embedding_thread
)

# Load environment variables 
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Repository Processing Microservice")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize vector store
vector_store = create_vector_store()

# Initialize progress on startup
init_progress()

# Try to load existing vector store
try:
    vector_store.load()
    logger.info("Loaded existing vector store")
except Exception as e:
    logger.warning(f"Could not load vector store: {str(e)}")

# Pydantic models
class RepositoryRequest(BaseModel):
    repo_urls: List[str] = []

class SimilaritySearchRequest(BaseModel):
    embedding: List[float]
    top_k: int = 5

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Repository Processing Microservice", "status": "running"}
    
@app.post("/clone-and-process")
async def clone_and_process_repos(
    background_tasks: BackgroundTasks,
    request: RepositoryRequest,
    embed: bool = True
):
    """
    Clone repositories and optionally generate embeddings
    
    Args:
        request: Repository URLs to clone
        embed: Whether to generate embeddings after cloning
    """
    try:
        # Check if a process is already running 
        progress_data = load_progress()
        if progress_data["status"] != "idle":
            return {
                "message": "Another operation is already in progress",
                "current_status": progress_data["status"]
            }
        
        # Set repository URLs
        if request.repo_urls:
            os.environ["GITHUB_REPOSITORIES"] = ",".join(request.repo_urls)
        
        # Start clone process in background    
        background_tasks.add_task(run_clone_thread, repo_urls=request.repo_urls, embed=embed)
        
        return {
            "message": "Repository cloning and processing started",
            "repositories": request.repo_urls,
            "create_embeddings": embed
        }
    except Exception as e:
        logger.error(f"Error starting repository clone and process: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.get("/embedding-progress")
async def get_embedding_progress():
    """
    Get current embedding progress
    """
    try:
        progress_data = load_progress()
        
        # Add calculated fields
        result = dict(progress_data)
        
        # Calculate percentage
        if progress_data["total_files"] > 0:
            result["progress_percent"] = round(
                progress_data["processed_files"] / progress_data["total_files"] * 100,
                2
            ) 
        else:
            result["progress_percent"] = 0
            
        return result
    except Exception as e:
        logger.error(f"Error retrieving embedding progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
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
            logger.warning(
                f"Repositories directory does not exist at: {os.path.abspath(repositories_dir)}"
            )
            return {"status": "No repositories processed yet"} 
        
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
            "processed_repositories": all_items,
            "file_extensions": extensions,
            "total_files": sum(extensions.values()) if extensions else 0,
            "vector_store_stats": vector_store_stats, 
            "processing_status": progress_data["status"]
        }
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
        
@app.post("/cleanup")
async def cleanup(clear_vector_store: bool = False):
    """
    Clean up processed files and optionally clear vector store
    
    Args:
        clear_vector_store: Whether to clear the vector store
    """
    try:
        # Clean up processed files 
        cleanup_processed_files()
        
        # Clear vector store if requested
        if clear_vector_store:
            vector_store.clear()
            vector_store.save()
        
        return {
            "message": "Cleanup completed",
            "vector_store_cleared": clear_vector_store  
        }
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")  
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/search-similar")
async def search_similar_chunks(request: SimilaritySearchRequest):
    """
    Search for similar code chunks based on embedding.
    
    Args:
        request: Embedding to search for
        
    Returns:
        Similar code chunks from the vector store
    """
    try:
        # Ensure vector store is loaded
        if vector_store.index is None:
            vector_store.load()
        
        # Perform similarity search
        results = vector_store.search(request.embedding, request.top_k)
        return {"similar_chunks": results}
    except Exception as e:
        logger.error(f"Error searching similar chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)