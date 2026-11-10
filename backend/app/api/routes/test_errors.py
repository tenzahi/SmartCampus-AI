
from fastapi import APIRouter
from app.core.exceptions import SmartCampusException
router = APIRouter()

@router.get("/test-error")
def test_error():
    raise SmartCampusException(
        message="Erreur personnalisée SmartCampus AI",
        status_code=400
    )
