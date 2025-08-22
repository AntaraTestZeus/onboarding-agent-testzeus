# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chatbot, tenants, verify
from utils.config import settings

app = FastAPI(title="TestZeus Onboarding Agent", version="0.1.0")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chatbot.router, prefix="/api/v1", tags=["chat"])
app.include_router(tenants.router, prefix="/api/v1", tags=["tenants"])
app.include_router(verify.router, prefix="/api/v1", tags=["verify"])

@app.get("/")
def read_root():
    return {"message": "🚀 TestZeus Onboarding Agent is live!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "pocketbase": settings.pb_url}