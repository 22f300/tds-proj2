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
api_key = os.getenv("AI_PROXY_TOKEN")
base_url = os.getenv("BASE_URL")

if not api_key or not base_url:
    raise ValueError("❌ AI Proxy Token or Base URL not found. Make sure they're set in your environment variables.")
else:
    print(f"✅ AI Proxy Token Loaded Successfully")
    print(f"✅ Base URL Loaded Successfully: {base_url}")

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
        try:
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
        except Exception as e:
            return {"answer": f"Error processing file: {str(e)}"}
    else:
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            json_data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant who answers academic questions."},
                    {"role": "user", "content": question}
                ],
                "max_tokens": 150,
                "temperature": 0.7
            }

            response = requests.post(
                f"{base_url}chat/completions",
                headers=headers,
                json=json_data
            )
            
            if response.status_code == 200:
                answer_text = response.json()['choices'][0]['message']['content'].strip()
                return {"answer": answer_text}
            else:
                return {"answer": f"Error: {response.status_code} - {response.text}"}
        except Exception as e:
            return {"answer": f"Error: {str(e)}"}
