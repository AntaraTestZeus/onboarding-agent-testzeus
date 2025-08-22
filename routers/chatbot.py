# backend/routers/chatbot.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/chat")
def chat():
    return {"response": "Chat endpoint placeholder"}