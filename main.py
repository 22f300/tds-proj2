from fastapi import FastAPI, File, UploadFile, Form
import pandas as pd
import zipfile
import io
import openai
import os

app = FastAPI()

# Load OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.get("/")
async def root():
    return {"message": "API is working!"}

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
        # Use OpenAI API with the new format
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Change to "gpt-3.5-turbo" if you're using GPT-3.5
                messages=[
                    {"role": "system", "content": "You are a helpful assistant who answers academic questions."},
                    {"role": "user", "content": question}
                ]
            )
            answer_text = response.choices[0].message["content"].strip()
            return {"answer": answer_text}
        except Exception as e:
            return {"answer": f"Error: {str(e)}"}
