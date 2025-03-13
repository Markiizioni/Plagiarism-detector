from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from prompt import generate_plagiarism_prompt
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class CodeRequest(BaseModel):
    code: str

@app.post("/check", response_class=PlainTextResponse)
async def check_plagiarism(request: CodeRequest):
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
