from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging
from typing import List, Optional
from dotenv import load_dotenv

from app.clone_and_process import clone_repositories, get_repository_urls
from app.cleanup import cleanup_processed_files
from app.codebert_embedder import create_code_embeddings, get_embedding
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

class EmbeddingRequest(BaseModel):
    code: str

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
    """Clone repositories and optionally generate embeddings"""
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
            "message": "Repository cloning started",
            "repositories": request.repo_urls,
            "create_embeddings": embed
        }
    except Exception as e:
        logger.error(f"Error starting repository clone: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-embedding")
async def generate_embedding(request: EmbeddingRequest):
    """Generate an embedding for the given code"""
    try:
        # Generate the embedding using the get_embedding function
        embedding = get_embedding(request.code)
        return {"embedding": embedding}
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search-similar")
async def search_similar_chunks(request: SimilaritySearchRequest):
    """Search for similar code chunks based on embedding"""
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

@app.post("/cleanup")
async def cleanup(clear_vector_store: Optional[bool] = False):
    """Clean up processed files"""
    try:
        # Cleanup processed files
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

@app.get("/progress")
async def get_current_progress():
    """Get current processing progress"""
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
        logger.error(f"Error retrieving progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
