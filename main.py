from fastapi import FastAPI, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import pandas as pd
import zipfile
import io
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
        file_content = await file.read()
        filename = file.filename
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_content))
            elif filename.endswith('.txt'):
                text_content = file_content.decode('utf-8')
                return {"answer": text_content}
            elif filename.endswith('.json'):
                import json
                json_content = json.loads(file_content)
                return {"answer": json_content}
            elif filename.endswith('.xlsx') or filename.endswith('.xls'):
                df = pd.read_excel(io.BytesIO(file_content))
            elif filename.endswith('.zip'):
                import zipfile
                with zipfile.ZipFile(io.BytesIO(file_content)) as z:
                    extracted_files = z.namelist()
                    # Automatically read the first file found in the ZIP archive
                    extracted_file = extracted_files[0] 
                    with z.open(extracted_file) as f:
                        if extracted_file.endswith('.csv'):
                            df = pd.read_csv(f)
                        elif extracted_file.endswith('.txt'):
                            text_content = f.read().decode('utf-8')
                            return {"answer": text_content}
                        elif extracted_file.endswith('.json'):
                            json_content = json.load(f)
                            return {"answer": json_content}
                        elif extracted_file.endswith('.xlsx') or extracted_file.endswith('.xls'):
                            df = pd.read_excel(f)
                        else:
                            return {"answer": f"Unsupported file type in ZIP: {extracted_file}"}
            else:
                return {"answer": "Unsupported file type. Please upload CSV, TXT, JSON, Excel, or ZIP files."}

            if isinstance(df, pd.DataFrame):
                if 'answer' in df.columns:
                    answer_value = df['answer'].iloc[0]
                    return {"answer": str(answer_value)}
                else:
                    return {"answer": "The 'answer' column was not found in the file."}
        except Exception as e:
            return {"answer": f"Error reading file: {str(e)}"}

    else:
        # Process the question with AI Proxy
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
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": question}
                    ]
                }
            )
            response.raise_for_status()
            response_json = response.json()
            if 'choices' in response_json and len(response_json['choices']) > 0:
                answer_text = response_json['choices'][0]['message']['content'].strip()
                return {"answer": answer_text}
            else:
                return {"answer": "Error: No valid response from the AI Proxy."}
        except Exception as e:
            return {"answer": f"Error: {str(e)}"}
