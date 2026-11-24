from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import engine

router = APIRouter()


@router.get("/tarifs")
def liste_tarifs():
    """
    Retourne uniquement les tarifs :
    - actifs
    - publiés
    - actuellement valides
    """

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
                    annee_academique,
                    modalite_paiement,
                    statut_publication,
                    date_debut_validite,
                    date_fin_validite
                FROM tarifs
                WHERE actif = TRUE
                  AND statut_publication = 'publie'
                  AND (
                      date_debut_validite IS NULL
                      OR date_debut_validite <= CURRENT_DATE
                  )
                  AND (
                      date_fin_validite IS NULL
                      OR date_fin_validite >= CURRENT_DATE
                  )
                ORDER BY id
            """)
        ).mappings().all()

    return [dict(row) for row in rows]