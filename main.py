# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
from routers import chatbot
import os


app = FastAPI(
    title="TestZeus Onboarding Agent",
    description="AI-powered onboarding with GPT-5 and free-form tool calling",
    version="1.0.0"
)

# CORS - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include chatbot router
app.include_router(chatbot.router)

@app.get("/health")
def health():
    return {"status": "ok", "model": os.getenv("OPENAI_MODEL", "gpt-5")}

# Optional: mount frontend (if using static files)
# from fastapi.staticfiles import StaticFiles
# app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")