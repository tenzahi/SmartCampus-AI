
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.programmes import router as programmes_router
from app.api.routes.health import router as health_router
from app.api.routes.formations import router as formations_router
from app.api.routes.specialites import router as specialites_router
from app.api.routes.programmes_pedagogiques import router as programmes_pedagogiques_router
from app.api.routes.matieres import router as matieres_router
from app.api.routes.conditions_admission import router as conditions_admission_router
from app.api.routes.auth import router as auth_router

from app.core.environment import is_production
from app.core.exceptions import (
    SmartCampusException,
    smartcampus_exception_handler
)

app = FastAPI(
    title="SmartCampus AI API",
    description="API backend de la plateforme SmartCampus AI",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gestion des exceptions personnalisées
app.add_exception_handler(
    SmartCampusException,
    smartcampus_exception_handler
)

# Route principale
@app.get("/")
def root():
    return {
        "message": "Bienvenue sur SmartCampus AI API",
        "status": "running"
}

# Enregistrement des routes
app.include_router(health_router)
if not is_production():
    # Route de diagnostic uniquement disponible hors production.
    from app.api.routes.test_errors import router as test_errors_router

    app.include_router(test_errors_router)
app.include_router(programmes_router)
app.include_router(formations_router)
app.include_router(specialites_router)
app.include_router(programmes_pedagogiques_router)
app.include_router(matieres_router)
app.include_router(conditions_admission_router)
app.include_router(auth_router)