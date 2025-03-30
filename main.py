from fastapi import FastAPI, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import pandas as pd
import zipfile
import io
import openai
import requests
import os

# ✅ Load environment variables from .env file
load_dotenv()

print("AI_PROXY_TOKEN:", os.getenv("AI_PROXY_TOKEN"))
print("AI_PROXY_URL:", os.getenv("AI_PROXY_URL"))

app = FastAPI()

# Absolute path to the static folder
static_folder = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_folder):
    raise RuntimeError(f"Directory '{static_folder}' does not exist. Make sure it's in the correct location.")

app.mount("/static", StaticFiles(directory=static_folder), name="static")
# Load AI Proxy Token and Base URL from environment variables
AI_PROXY_TOKEN = os.getenv("AI_PROXY_TOKEN")
AI_PROXY_URL = os.getenv("AI_PROXY_URL")

if not AI_PROXY_TOKEN or not AI_PROXY_URL:
    raise ValueError("❌ AI Proxy Token or Base URL not found. Make sure they're set in your environment variables.")

print(f"✅ AI Proxy Token Loaded Successfully")

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
async def process_question(question: str = Form(...), file: UploadFile = File(None)):
    if file:
        content = await file.read()
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            z.extractall("./extracted")

        csv_file = [f for f in z.namelist() if f.endswith('.csv')][0]
        df = pd.read_csv(f"./extracted/{csv_file}")

        if 'answer' in df.columns:
            answer_value = df['answer'].iloc[0]
            return {"answer": str(answer_value)}
        else:
            return {"answer": "The 'answer' column was not found in the CSV file."}
    else:
        # If no file is uploaded, process the question with AI Proxy
        try:
            headers = {
                "Authorization": f"Bearer {AI_PROXY_TOKEN}",
                "Content-Type": "application/json",
            }
            data = {
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": question}
                ]
            }

    try:
        response = requests.post(
            f"{AI_PROXY_URL}chat/completions",
            headers=headers,
            json=data
        )

        result = response.json()
        if "choices" in result:
            answer_text = result['choices'][0]['message']['content'].strip()
            return {"answer": answer_text}
        else:
            return {"error": result}

    except Exception as e:
        return {"error": str(e)}
