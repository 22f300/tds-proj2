from fastapi import FastAPI, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd
import zipfile
import io
import openai
import os
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Mount the static directory for serving favicon
app.mount("/static", StaticFiles(directory="static"), name="static")

# Retrieve AI Proxy Token and Base URL from environment variables
api_token = os.getenv("AI_PROXY_TOKEN")
base_url = os.getenv("AI_PROXY_URL")

if not api_token or not base_url:
    raise ValueError("❌ AI Proxy Token or Base URL not found. Make sure they're set in your environment variables.")
else:
    print(f"✅ AI Proxy Token and Base URL Loaded Successfully")

@app.get("/")
async def root():
    return {"message": "API is working!"}

@app.post("/api/")
async def process_question(question: str = Form(...)):
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": question}]
    }

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=data
        )

        response_json = response.json()

        if response.status_code == 200:
            answer_text = response_json['choices'][0]['message']['content'].strip()
            return {"answer": answer_text}
        else:
            return {"answer": f"Error: {response_json}"}

    except Exception as e:
        return {"answer": f"Error: {str(e)}"}
