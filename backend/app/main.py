
from fastapi import FastAPI
from app.api.routes.health import router as health_router
from app.api.routes.test_errors import router as test_errors_router

from app.core.exceptions import (
    SmartCampusException,
    smartcampus_exception_handler
)

app = FastAPI(
    title="SmartCampus AI API",
    description="API backend de la plateforme SmartCampus AI",
    version="1.0.0"
)

app.add_exception_handler(
    SmartCampusException,
    smartcampus_exception_handler
)

@app.get("/")
def root():
    return {
        "message": "Bienvenue sur SmartCampus AI API",
        "status": "running"
}

app.include_router(health_router)
app.include_router(test_errors_router)
