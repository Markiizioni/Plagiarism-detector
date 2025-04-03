from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx
import logging
from dotenv import load_dotenv

from app.llm_plagiarism_detector import LLMPlagiarismDetector

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Combined Approach Plagiarism Detection Microservice")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM-based plagiarism detector
llm_detector = LLMPlagiarismDetector(
    model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
    temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.0"))
)

# Processing service configuration
PROCESSING_SERVICE_URL = os.getenv(
    "PROCESSING_SERVICE_URL", 
    "http://localhost:8000"
)

class RepositoryRequest(BaseModel):
    repo_urls: list[str] = []

class PlagiarismCheckRequest(BaseModel):
    """
    Request model for plagiarism check.
    
    Attributes:
        code: The source code to check for plagiarism. Can be multi-line.
        top_k: Number of similar code chunks to check.
    """
    code: str
    top_k: int = 5  # Number of similar code chunks to check
    
    class Config:
        schema_extra = {
            "example": {
                "code": """
import os
import sys

def calculate_factorial(n):
    if n == 0 or n == 1:
        return 1
    else:
        return n * calculate_factorial(n-1)
                """,
                "top_k": 5
            }
        }

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Combined Approach Plagiarism Detection Microservice",
        "status": "running"
    }

@app.post("/clone-and-process")
async def clone_repos(request: RepositoryRequest):
    """
    Trigger repository cloning in the processing microservice.
    
    Args:
        request: Repository request containing repo URLs
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PROCESSING_SERVICE_URL}/clone-and-process", 
                json={
                    "repo_urls": request.repo_urls,
                    "embed": True  # Always generate embeddings
                },
                timeout=300.0  # 5-minute timeout for cloning
            )
            
            # Raise an exception for bad responses
            response.raise_for_status()
            
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to processing service: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to connect to processing service: {e}"
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"Processing service returned an error: {e}")
        raise HTTPException(
            status_code=e.response.status_code, 
            detail=f"Processing service error: {e.response.text}"
        )

@app.post("/check-plagiarism")
async def check_plagiarism(request: PlagiarismCheckRequest):
    """
    Check if the provided code is plagiarized by finding similar code chunks
    and analyzing them with an LLM.
    
    Args:
        request: Request containing the code to check for plagiarism
        
    Returns:
        Plagiarism analysis result with LLM's determination
    """
    try:
        # First, get embeddings from processing service
        async with httpx.AsyncClient() as client:
            embedding_response = await client.post(
                f"{PROCESSING_SERVICE_URL}/get-embedding", 
                json={"code": request.code}
            )
            embedding_response.raise_for_status()
            code_embedding = embedding_response.json()['embedding']
            
            # Then, search for similar chunks
            similar_response = await client.post(
                f"{PROCESSING_SERVICE_URL}/search-similar", 
                json={
                    "embedding": code_embedding, 
                    "top_k": request.top_k
                }
            )
            similar_response.raise_for_status()
            results = similar_response.json()['similar_chunks']
        
        # Apply LLM-based plagiarism analysis
        plagiarism_analysis = llm_detector.analyze_similarity(request.code, results)
        
        # Return a detailed response
        return {
            "plagiarism_detected": plagiarism_analysis["plagiarism_detected"],
            "analysis": plagiarism_analysis["analysis"],
            "confidence": plagiarism_analysis.get("confidence", 0.0),
            "model_used": plagiarism_analysis.get("llm_model", "unknown"),
            "similar_chunks_count": len(results)
        }
    except httpx.RequestError as e:
        logger.error(f"Error connecting to processing service: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to connect to processing service: {e}"
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"Processing service returned an error: {e}")
        raise HTTPException(
            status_code=e.response.status_code, 
            detail=f"Processing service error: {e.response.text}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in plagiarism check: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Plagiarism check failed: {e}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)