from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from prompt import generate_plagiarism_prompt
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create FastAPI app with title and description
app = FastAPI(
    title="LLM-Only Plagiarism Detection",
    description="A simple API that uses GPT-3.5 to detect code plagiarism",
    version="1.0.0",
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class CodeRequest(BaseModel):
    code: str
    
    class Config:
        schema_extra = {
            "example": {
                "code": "def factorial(n):\n    if n == 0:\n        return 1\n    else:\n        return n * factorial(n-1)"
            }
        }

@app.post("/check", 
         response_class=PlainTextResponse,
         summary="Check Plagiarism",
         description="Submit code to check if it appears to be plagiarized")
async def check_plagiarism(request: CodeRequest):
    """
    Checks if the submitted code appears to be plagiarized using GPT-3.5
    
    - **code**: String containing the code snippet to analyze
    
    Returns a simple "Yes" or "No" response
    """
    try:
        prompt = generate_plagiarism_prompt(request.code)

        # Call the OpenAI API with the formatted prompt
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=1
        )

        result = response.choices[0].message.content.strip()
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Add a root endpoint for health check
@app.get("/", response_class=PlainTextResponse)
async def root():
    return "LLM Plagiarism Detector API is running"
