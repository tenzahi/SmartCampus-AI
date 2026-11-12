from fastapi import FastAPI
from app.api.chat_sessions import router as chat_sessions_router
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SmartCampus AI",
    description="Backend de la plateforme SmartCampus AI — Epic 23",
    version="0.1.0",
)

# Configuration CORS pour autoriser le Frontend (Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# On inclut les routeurs
app.include_router(auth_router)
app.include_router(chat_sessions_router)
app.include_router(chat_router)

@app.get("/")
def root():
    return {"message": "SmartCampus AI backend is running", "epic": "epic23"}

@app.get("/health")
def health():
    return {"status": "ok"}