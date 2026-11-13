from typing import Optional

from app.core.exceptions import SmartCampusException
from app.services.catalogue_service import BaseCatalogueService, CatalogueRepository
from app.services.formation_service import FormationService


class SpecialiteRepository(CatalogueRepository):
    table = "specialites"
    columns = (
        "id",
        "programme_id",
        "nom",
        "code",
        "description",
        "actif",
        "created_at",
        "updated_at",
    )
    search_columns = ("nom", "code", "description")
    entity_label = "Spécialité"
    integrity_message = (
        "Un enregistrement de spécialité viole une contrainte d'intégrité."
    )
    database_message = "Erreur base de données lors du traitement de la spécialité."


class SpecialiteService(BaseCatalogueService):
    repository = SpecialiteRepository
    entity_label = "Spécialité"

    @staticmethod
    def list_specialites(
        programme_id: Optional[int] = None,
        q: Optional[str] = None,
        actif: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        return SpecialiteService.list(
            {"programme_id": programme_id, "actif": actif},
            q=q,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_specialite_by_id(specialite_id: int) -> Optional[dict]:
        return SpecialiteService.get(specialite_id)

    @staticmethod
    def create_specialite(payload: dict) -> dict:
        programme_id = payload["programme_id"]
        if FormationService.get_formation_by_id(programme_id) is None:
            raise SmartCampusException(
                message=f"Programme ID {programme_id} introuvable.",
                status_code=400,
            )

        SpecialiteService.ensure_unique(
            {"programme_id": programme_id, "nom": payload["nom"]},
            "Une spécialité avec ce nom existe déjà pour ce programme.",
        )

        values = {
            "programme_id": programme_id,
            "nom": payload["nom"],
            "code": payload["code"],
            "description": payload.get("description"),
            "actif": payload.get("actif", True),
        }
        return SpecialiteRepository.insert_row(values)

    @staticmethod
    def update_specialite(specialite_id: int, **kwargs) -> dict:
        existing = SpecialiteService.get_or_404(specialite_id)
        data = {
            key: value
            for key, value in kwargs.items()
            if key in SpecialiteRepository.columns and key != "id"
        }

        programme_id = data.get("programme_id", existing["programme_id"])
        nom = data.get("nom", existing["nom"])

        if "programme_id" in data:
            if FormationService.get_formation_by_id(programme_id) is None:
                raise SmartCampusException(
                    message=f"Programme ID {programme_id} introuvable.",
                    status_code=400,
                )

        SpecialiteService.ensure_unique(
            {"programme_id": programme_id, "nom": nom},
            "Une spécialité avec ce nom existe déjà pour ce programme.",
            exclude_id=specialite_id,
        )

        if not data:
            return existing

        updated = SpecialiteRepository.update_row(specialite_id, data)
        if updated is None:
            raise SmartCampusException(
                message=f"Spécialité ID {specialite_id} introuvable.",
                status_code=404,
            )
        return updated

    @staticmethod
    def delete_specialite(specialite_id: int) -> dict:
        return SpecialiteService.delete(specialite_id)
