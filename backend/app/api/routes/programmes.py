from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import engine, check_db

router = APIRouter()


@router.get("/health/db")
def health_db():
    check_db()
    return {"database": "ok"}


@router.get("/programmes")
def liste_programmes():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, etablissement, nom, niveau FROM programmes ORDER BY id")
        ).mappings().all()
    return [dict(r) for r in rows]