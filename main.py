from fastapi import FastAPI, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import pandas as pd
import json
import zipfile
import io
import requests
import os

load_dotenv()

app = FastAPI()

static_folder = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_folder):
    raise RuntimeError(f"Directory '{static_folder}' does not exist.")

app.mount("/static", StaticFiles(directory=static_folder), name="static")

AI_PROXY_TOKEN = os.getenv("AI_PROXY_TOKEN")
AI_PROXY_URL = os.getenv("AI_PROXY_URL")

if not AI_PROXY_TOKEN or not AI_PROXY_URL:
    raise ValueError("❌ AI Proxy Token or Base URL not found.")

@app.get("/")
async def root():
    return {"message": "API is working!"}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    return FileResponse("static/favicon.ico")

@app.get("/favicon.png", include_in_schema=False)
async def favicon_png():
    return FileResponse("static/favicon.png")

def extract_file_content(filename, file_content):
    if filename.endswith('.csv'):
        return pd.read_csv(io.BytesIO(file_content)).to_dict(orient='records')
    elif filename.endswith('.txt'):
        return file_content.decode('utf-8')
    elif filename.endswith('.json'):
        return json.loads(file_content)
    elif filename.endswith(('.xlsx', '.xls')):
        return pd.read_excel(io.BytesIO(file_content)).to_dict(orient='records')
    else:
        raise ValueError("Unsupported file type.")

@app.post("/api/")
async def process_question(question: str = Form(...), file: UploadFile = File(None)):
    data_content = None

    if file:
        file_content = await file.read()
        filename = file.filename

        try:
            if filename.endswith('.zip'):
                with zipfile.ZipFile(io.BytesIO(file_content)) as z:
                    extracted_files = z.namelist()
                    if extracted_files:
                        first_file = extracted_files[0]
                        with z.open(first_file) as f:
                            inner_file_content = f.read()
                            data_content = extract_file_content(first_file, inner_file_content)
            else:
                data_content = extract_file_content(filename, file_content)

        except Exception:
            return {"answer": "Error reading file."}

    prompt = question

    if data_content:
        prompt += f"\n\nFile content:\n{json.dumps(data_content)}"

    try:
        response = requests.post(
            f"{AI_PROXY_URL}chat/completions",
            headers={
                "Authorization": f"Bearer {AI_PROXY_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "ONLY provide the final numeric or factual answer in plain text without explanations."},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=8
        )
        response.raise_for_status()
        response_json = response.json()
        if 'choices' in response_json and response_json['choices']:
            final_answer = response_json['choices'][0]['message']['content'].strip()
            return {"answer": final_answer}
        else:
            return {"answer": "No valid response."}

    except requests.Timeout:
        return {"answer": "Request timed out."}
    except Exception:
        return {"answer": "AI Proxy error."}
