from fastapi import FastAPI, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd
import zipfile
import io
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Mount the static directory for serving favicon
app.mount("/static", StaticFiles(directory="static"), name="static")

# Retrieve AI Proxy Token and Base URL from environment variables
ai_proxy_token = os.getenv("AI_PROXY_TOKEN")
ai_proxy_url = os.getenv("AI_PROXY_URL")

if not ai_proxy_token or not ai_proxy_url:
    raise ValueError("❌ AI Proxy Token or Base URL not found. Make sure they're set in your environment variables.")
else:
    print(f"✅ AI Proxy Token and Base URL Loaded Successfully")

@app.get("/")
async def root():
    return {"message": "API is working!"}

# Serve favicon.ico
@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    return FileResponse("static/favicon.ico")

# Serve favicon.png
@app.get("/favicon.png", include_in_schema=False)
async def favicon_png():
    return FileResponse("static/favicon.png")

@app.post("/api/")
async def process_question(question: str = Form(...)):
    try:
        headers = {
            "Authorization": f"Bearer {ai_proxy_token}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant who answers academic questions."},
                {"role": "user", "content": question}
            ]
        }
        
        response = requests.post(f"{ai_proxy_url}chat/completions", json=data, headers=headers)
        response_json = response.json()
        
        if "choices" in response_json:
            answer_text = response_json['choices'][0]['message']['content'].strip()
            return {"answer": answer_text}
        else:
            return {"answer": f"Error: {response_json}"}
    except Exception as e:
        return {"answer": f"Error: {str(e)}"}

