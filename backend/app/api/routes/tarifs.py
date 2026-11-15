from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import engine

router = APIRouter()


@router.get("/tarifs")
def liste_tarifs():
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    id,
                    programme_id,
                    programme_pedagogique_id,
                    montant,
                    devise,
                    type_frais,
                    description,
                    annee_academique
                FROM tarifs
                WHERE actif = TRUE
                ORDER BY id
            """)
        ).mappings().all()

    return [dict(row) for row in rows]