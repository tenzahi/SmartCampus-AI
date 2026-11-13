from typing import Optional

from app.core.exceptions import SmartCampusException
from app.services.catalogue_service import BaseCatalogueService, CatalogueRepository
from app.services.programme_pedagogique_service import (
    ProgrammePedagogiqueService,
)


class MatiereRepository(CatalogueRepository):
    table = "matieres"
    columns = (
        "id",
        "programme_pedagogique_id",
        "nom",
        "code",
        "description",
        "semestre",
        "coefficient",
        "volume_horaire",
        "credits",
        "actif",
        "created_at",
        "updated_at",
    )
    search_columns = ("nom", "code", "description")
    entity_label = "Matière"
    integrity_message = "Un enregistrement de matière viole une contrainte d'intégrité."
    database_message = "Erreur base de données lors du traitement de la matière."


class MatiereService(BaseCatalogueService):
    repository = MatiereRepository
    entity_label = "Matière"

    @staticmethod
    def list_matieres(
        programme_pedagogique_id: Optional[int] = None,
        semestre: Optional[int] = None,
        q: Optional[str] = None,
        actif: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        return MatiereService.list(
            {
                "programme_pedagogique_id": programme_pedagogique_id,
                "semestre": semestre,
                "actif": actif,
            },
            q=q,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_matiere_by_id(matiere_id: int) -> Optional[dict]:
        return MatiereService.get(matiere_id)

    @staticmethod
    def _valider_parent(programme_pedagogique_id: int) -> None:
        if (
            ProgrammePedagogiqueService.get_programme_pedagogique_by_id(
                programme_pedagogique_id
            )
            is None
        ):
            raise SmartCampusException(
                message=(
                    f"Programme pédagogique ID {programme_pedagogique_id} "
                    "introuvable."
                ),
                status_code=400,
            )

    @staticmethod
    def create_matiere(payload: dict) -> dict:
        programme_pedagogique_id = payload["programme_pedagogique_id"]
        MatiereService._valider_parent(programme_pedagogique_id)

        MatiereService.ensure_unique(
            {
                "code": payload["code"],
                "programme_pedagogique_id": programme_pedagogique_id,
            },
            "Une matière avec ce code existe déjà dans ce programme pédagogique.",
        )

        values = {
            "programme_pedagogique_id": programme_pedagogique_id,
            "nom": payload["nom"],
            "code": payload["code"],
            "description": payload.get("description"),
            "semestre": payload["semestre"],
            "coefficient": payload["coefficient"],
            "volume_horaire": payload["volume_horaire"],
            "credits": payload["credits"],
            "actif": payload.get("actif", True),
        }
        return MatiereRepository.insert_row(values)

    @staticmethod
    def update_matiere(matiere_id: int, **kwargs) -> dict:
        existing = MatiereService.get_or_404(matiere_id)
        data = {
            key: value
            for key, value in kwargs.items()
            if key in MatiereRepository.columns and key != "id"
        }

        programme_pedagogique_id = data.get(
            "programme_pedagogique_id",
            existing["programme_pedagogique_id"],
        )
        code = data.get("code", existing["code"])

        if "programme_pedagogique_id" in data:
            MatiereService._valider_parent(programme_pedagogique_id)

        MatiereService.ensure_unique(
            {
                "code": code,
                "programme_pedagogique_id": programme_pedagogique_id,
            },
            "Une matière avec ce code existe déjà dans ce programme pédagogique.",
            exclude_id=matiere_id,
        )

        if not data:
            return existing

        updated = MatiereRepository.update_row(matiere_id, data)
        if updated is None:
            raise SmartCampusException(
                message=f"Matière ID {matiere_id} introuvable.",
                status_code=404,
            )
        return updated

    @staticmethod
    def delete_matiere(matiere_id: int) -> dict:
        return MatiereService.delete(matiere_id)
