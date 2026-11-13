from typing import Optional

from app.core.exceptions import SmartCampusException
from app.services.catalogue_service import BaseCatalogueService, CatalogueRepository
from app.services.formation_service import FormationService
from app.services.specialite_service import SpecialiteService


class ProgrammePedagogiqueRepository(CatalogueRepository):
    table = "programmes_pedagogiques"
    columns = (
        "id",
        "programme_id",
        "specialite_id",
        "nom",
        "annee_academique",
        "niveau_etude",
        "description",
        "actif",
        "created_at",
        "updated_at",
    )
    search_columns = ("nom", "niveau_etude", "description")
    entity_label = "Programme pédagogique"
    integrity_message = (
        "Un enregistrement de programme pédagogique viole une contrainte "
        "d'intégrité."
    )
    database_message = (
        "Erreur base de données lors du traitement du programme pédagogique."
    )


class ProgrammePedagogiqueService(BaseCatalogueService):
    repository = ProgrammePedagogiqueRepository
    entity_label = "Programme pédagogique"

    @staticmethod
    def list_programmes_pedagogiques(
        programme_id: Optional[int] = None,
        specialite_id: Optional[int] = None,
        niveau_etude: Optional[str] = None,
        annee_academique: Optional[str] = None,
        q: Optional[str] = None,
        actif: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        return ProgrammePedagogiqueService.list(
            {
                "programme_id": programme_id,
                "specialite_id": specialite_id,
                "niveau_etude": niveau_etude,
                "annee_academique": annee_academique,
                "actif": actif,
            },
            q=q,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_programme_pedagogique_by_id(programme_pedagogique_id: int) -> Optional[dict]:
        return ProgrammePedagogiqueService.get(programme_pedagogique_id)

    @staticmethod
    def _valider_specialite(
        programme_id: int,
        specialite_id: Optional[int],
    ) -> None:
        if specialite_id is None:
            return

        specialite = SpecialiteService.get_specialite_by_id(specialite_id)
        if specialite is None:
            raise SmartCampusException(
                message=f"Spécialité ID {specialite_id} introuvable.",
                status_code=400,
            )
        if specialite["programme_id"] != programme_id:
            raise SmartCampusException(
                message=(
                    f"La spécialité ID {specialite_id} n'appartient pas au "
                    f"programme ID {programme_id}."
                ),
                status_code=400,
            )

    @staticmethod
    def create_programme_pedagogique(payload: dict) -> dict:
        programme_id = payload["programme_id"]
        if FormationService.get_formation_by_id(programme_id) is None:
            raise SmartCampusException(
                message=f"Programme ID {programme_id} introuvable.",
                status_code=400,
            )

        specialite_id = payload.get("specialite_id")
        ProgrammePedagogiqueService._valider_specialite(
            programme_id, specialite_id
        )

        ProgrammePedagogiqueService.ensure_unique(
            {
                "programme_id": programme_id,
                "specialite_id": specialite_id,
                "nom": payload["nom"],
                "annee_academique": payload["annee_academique"],
            },
            "Un programme pédagogique identique existe déjà.",
        )

        values = {
            "programme_id": programme_id,
            "specialite_id": specialite_id,
            "nom": payload["nom"],
            "annee_academique": payload["annee_academique"],
            "niveau_etude": payload["niveau_etude"],
            "description": payload.get("description"),
            "actif": payload.get("actif", True),
        }
        return ProgrammePedagogiqueRepository.insert_row(values)

    @staticmethod
    def update_programme_pedagogique(
        programme_pedagogique_id: int,
        **kwargs,
    ) -> dict:
        existing = ProgrammePedagogiqueService.get_or_404(
            programme_pedagogique_id
        )
        data = {
            key: value
            for key, value in kwargs.items()
            if key in ProgrammePedagogiqueRepository.columns and key != "id"
        }

        programme_id = data.get("programme_id", existing["programme_id"])
        specialite_id = data.get("specialite_id", existing["specialite_id"])
        nom = data.get("nom", existing["nom"])
        annee_academique = data.get(
            "annee_academique", existing["annee_academique"]
        )

        if "programme_id" in data:
            if FormationService.get_formation_by_id(programme_id) is None:
                raise SmartCampusException(
                    message=f"Programme ID {programme_id} introuvable.",
                    status_code=400,
                )

        ProgrammePedagogiqueService._valider_specialite(
            programme_id, specialite_id
        )

        ProgrammePedagogiqueService.ensure_unique(
            {
                "programme_id": programme_id,
                "specialite_id": specialite_id,
                "nom": nom,
                "annee_academique": annee_academique,
            },
            "Un programme pédagogique identique existe déjà.",
            exclude_id=programme_pedagogique_id,
        )

        if not data:
            return existing

        updated = ProgrammePedagogiqueRepository.update_row(
            programme_pedagogique_id, data
        )
        if updated is None:
            raise SmartCampusException(
                message=(
                    f"Programme pédagogique ID {programme_pedagogique_id} "
                    "introuvable."
                ),
                status_code=404,
            )
        return updated

    @staticmethod
    def delete_programme_pedagogique(programme_pedagogique_id: int) -> dict:
        return ProgrammePedagogiqueService.delete(programme_pedagogique_id)
