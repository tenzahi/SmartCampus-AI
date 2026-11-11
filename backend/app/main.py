from fastapi import FastAPI

app = FastAPI(
    title="SmartCampus AI",
    description="Backend de la plateforme SmartCampus AI — Epic 23",
    version="0.1.0",
)

@app.get("/")
def root():
    return {"message": "SmartCampus AI backend is running", "epic": "epic23"}

@app.get("/health")
def health():
    return {"status": "ok"}