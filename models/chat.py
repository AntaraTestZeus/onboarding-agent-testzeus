# backend/models/chat.py
from pydantic import BaseModel
from typing import List, Dict, Any

class ChatRequest(BaseModel):
    message: str
    session_id: str = None

class ChatResponse(BaseModel):
    response: str
    next_prompt: str = None
    requires_followup: bool = True
    data: Dict[str, Any] = {}