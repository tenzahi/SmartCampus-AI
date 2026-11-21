from typing import Optional

from app.core.exceptions import SmartCampusException
from app.services.catalogue_service import BaseCatalogueService, CatalogueRepository
from app.services.formation_service import FormationService
from app.services.programme_pedagogique_service import (
    ProgrammePedagogiqueService,
)


class ConditionAdmissionRepository(CatalogueRepository):
    table = "conditions_admission"
    columns = (
        "id",
        "programme_id",
        "programme_pedagogique_id",
        "type_condition",
        "description",
        "valeur",
        "obligatoire",
        "actif",
        "created_at",
        "updated_at",
    )
    search_columns = ("type_condition", "description", "valeur")
    entity_label = "Condition d'admission"
    integrity_message = (
        "Un enregistrement de condition d'admission viole une contrainte "
        "d'intégrité."
    )
    database_message = (
        "Erreur base de données lors du traitement de la condition d'admission."
    )


class ConditionAdmissionService(BaseCatalogueService):
    repository = ConditionAdmissionRepository
    entity_label = "Condition d'admission"

    @staticmethod
    def list_conditions_admission(
        programme_id: Optional[int] = None,
        programme_pedagogique_id: Optional[int] = None,
        type_condition: Optional[str] = None,
        obligatoire: Optional[bool] = None,
        q: Optional[str] = None,
        actif: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        return ConditionAdmissionService.list(
            {
                "programme_id": programme_id,
                "programme_pedagogique_id": programme_pedagogique_id,
                "type_condition": type_condition,
                "obligatoire": obligatoire,
                "actif": actif,
            },
            q=q,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_condition_admission_by_id(condition_id: int) -> Optional[dict]:
        return ConditionAdmissionService.get(condition_id)

    @staticmethod
    def _valider_parents(
        programme_id: Optional[int],
        programme_pedagogique_id: Optional[int],
    ) -> None:
        if (programme_id is None) == (programme_pedagogique_id is None):
            raise SmartCampusException(
                message=(
                    "Exactement un des deux parents doit être renseigné : "
                    "programme_id ou programme_pedagogique_id."
                ),
                status_code=400,
            )

        if programme_id is not None:
            if FormationService.get_formation_by_id(programme_id) is None:
                raise SmartCampusException(
                    message=f"Programme ID {programme_id} introuvable.",
                    status_code=400,
                )

        if programme_pedagogique_id is not None:
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
    def create_condition_admission(payload: dict) -> dict:
        programme_id = payload.get("programme_id")
        programme_pedagogique_id = payload.get("programme_pedagogique_id")
        ConditionAdmissionService._valider_parents(
            programme_id, programme_pedagogique_id
        )

        values = {
            "programme_id": programme_id,
            "programme_pedagogique_id": programme_pedagogique_id,
            "type_condition": payload["type_condition"],
            "description": payload["description"],
            "valeur": payload.get("valeur"),
            "obligatoire": payload.get("obligatoire", True),
            "actif": payload.get("actif", True),
        }
        return ConditionAdmissionRepository.insert_row(values)

    @staticmethod
    def update_condition_admission(condition_id: int, **kwargs) -> dict:
        existing = ConditionAdmissionService.get_or_404(condition_id)
        data = {
            key: value
            for key, value in kwargs.items()
            if key in ConditionAdmissionRepository.columns and key != "id"
        }

        # Le changement de parent est exclusif : fournir un parent non nul
        # remet automatiquement l'autre à NULL.
        if "programme_id" in data and "programme_pedagogique_id" not in data:
            if data["programme_id"] is not None:
                data["programme_pedagogique_id"] = None
            elif existing["programme_pedagogique_id"] is None:
                raise SmartCampusException(
                    message=(
                        "Exactement un des deux parents doit être renseigné : "
                        "programme_id ou programme_pedagogique_id."
                    ),
                    status_code=400,
                )

        if "programme_pedagogique_id" in data and "programme_id" not in data:
            if data["programme_pedagogique_id"] is not None:
                data["programme_id"] = None
            elif existing["programme_id"] is None:
                raise SmartCampusException(
                    message=(
                        "Exactement un des deux parents doit être renseigné : "
                        "programme_id ou programme_pedagogique_id."
                    ),
                    status_code=400,
                )

        programme_id = data.get("programme_id", existing["programme_id"])
        programme_pedagogique_id = data.get(
            "programme_pedagogique_id",
            existing["programme_pedagogique_id"],
        )
        ConditionAdmissionService._valider_parents(
            programme_id, programme_pedagogique_id
        )

        if not data:
            return existing

        updated = ConditionAdmissionRepository.update_row(condition_id, data)
        if updated is None:
            raise SmartCampusException(
                message=f"Condition d'admission ID {condition_id} introuvable.",
                status_code=404,
            )
        return updated

    @staticmethod
    def delete_condition_admission(condition_id: int) -> dict:
        return ConditionAdmissionService.delete(condition_id)
