from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import engine

router = APIRouter()


@router.get("/conditions-admission")
def liste_conditions_admission():
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    id,
                    programme_id,
                    programme_pedagogique_id,
                    type_condition,
                    description,
                    valeur,
                    obligatoire
                FROM conditions_admission
                WHERE actif = TRUE
                ORDER BY id
            """)
        ).mappings().all()

    return [dict(row) for row in rows]