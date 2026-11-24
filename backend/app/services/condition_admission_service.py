from datetime import date
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine
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
        "statut_publication",
        "date_debut_validite",
        "date_fin_validite",
        "created_at",
        "updated_at",
    )

    search_columns = (
        "type_condition",
        "description",
        "valeur",
    )

    entity_label = "Condition d'admission"

    integrity_message = (
        "Un enregistrement de condition d'admission viole une contrainte "
        "d'intégrité."
    )

    database_message = (
        "Erreur base de données lors du traitement de la condition d'admission."
    )

    @classmethod
    def list_valid_rows(
        cls,
        filters: dict,
        q: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """
        Retourne uniquement les conditions :
        - actives
        - publiées
        - actuellement valides
        """

        if skip < 0:
            raise ValueError("skip doit être >= 0.")

        if limit < 1:
            raise ValueError("limit doit être >= 1.")

        where_parts = [
            "actif = TRUE",
            "statut_publication = 'publie'",
            """
            (
                date_debut_validite IS NULL
                OR date_debut_validite <= CURRENT_DATE
            )
            """,
            """
            (
                date_fin_validite IS NULL
                OR date_fin_validite >= CURRENT_DATE
            )
            """,
        ]

        params = {
            "skip": skip,
            "limit": limit,
        }

        # Filtres classiques
        for key, value in filters.items():
            if value is None:
                continue

            if key not in cls.columns:
                raise ValueError(f"Colonne inconnue : {key}")

            where_parts.append(f"{key} = :{key}")
            params[key] = value

        # Recherche textuelle
        if q is not None and q.strip():
            params["q"] = f"%{q.strip()}%"

            search_parts = [
                f"LOWER(COALESCE({column}, '')) LIKE LOWER(:q)"
                for column in cls.search_columns
            ]

            if search_parts:
                where_parts.append(
                    f"({' OR '.join(search_parts)})"
                )

        where_clause = " AND ".join(where_parts)

        query = f"""
            SELECT
                {cls._select_columns()}
            FROM {cls.table}
            WHERE {where_clause}
            ORDER BY id
            OFFSET :skip ROWS
            FETCH NEXT :limit ROWS ONLY
        """

        try:
            with engine.connect() as conn:
                rows = (
                    conn.execute(
                        text(query),
                        params,
                    )
                    .mappings()
                    .all()
                )

                return [dict(row) for row in rows]

        except SQLAlchemyError as exc:
            raise SmartCampusException(
                message=cls.database_message,
                status_code=500,
            ) from exc

    @classmethod
    def get_valid_row(cls, entity_id: int) -> Optional[dict]:
        """
        Retourne une condition uniquement si elle est :
        - active
        - publiée
        - actuellement valide
        """

        query = f"""
            SELECT
                {cls._select_columns()}
            FROM {cls.table}
            WHERE id = :id
              AND actif = TRUE
              AND statut_publication = 'publie'
              AND (
                  date_debut_validite IS NULL
                  OR date_debut_validite <= CURRENT_DATE
              )
              AND (
                  date_fin_validite IS NULL
                  OR date_fin_validite >= CURRENT_DATE
              )
        """

        try:
            with engine.connect() as conn:
                row = (
                    conn.execute(
                        text(query),
                        {"id": entity_id},
                    )
                    .mappings()
                    .first()
                )

                return dict(row) if row is not None else None

        except SQLAlchemyError as exc:
            raise SmartCampusException(
                message=cls.database_message,
                status_code=500,
            ) from exc


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
        statut_publication: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """
        Consultation des conditions d'admission.

        Par défaut, seules les informations officielles et valides
        sont retournées.
        """

        filters = {
            "programme_id": programme_id,
            "programme_pedagogique_id": programme_pedagogique_id,
            "type_condition": type_condition,
            "obligatoire": obligatoire,
        }

        # Pour une consultation publique, on impose :
        # actif = TRUE
        # statut_publication = publie
        #
        # Le filtre de date est traité dans list_valid_rows().
        if actif is not None:
            filters["actif"] = actif
        else:
            filters["actif"] = True

        if statut_publication is not None:
            filters["statut_publication"] = statut_publication
        else:
            filters["statut_publication"] = "publie"

        return ConditionAdmissionRepository.list_valid_rows(
            filters,
            q=q,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_condition_admission_by_id(
        condition_id: int,
    ) -> Optional[dict]:
        """
        Récupère une condition uniquement si elle est actuellement
        officielle et valide.
        """

        return ConditionAdmissionRepository.get_valid_row(condition_id)

    @staticmethod
    def _valider_parents(
        programme_id: Optional[int],
        programme_pedagogique_id: Optional[int],
    ) -> None:
        """
        Une condition doit être liée à exactement un parent :
        - programme
        OU
        - programme pédagogique.
        """

        if (programme_id is None) == (
            programme_pedagogique_id is None
        ):
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
                        f"Programme pédagogique ID "
                        f"{programme_pedagogique_id} introuvable."
                    ),
                    status_code=400,
                )

    @staticmethod
    def _valider_publication(
        statut_publication: str,
        date_debut_validite: Optional[date],
        date_fin_validite: Optional[date],
    ) -> None:
        """
        Validation métier du statut et de la période de validité.
        """

        statuts_valides = {
            "brouillon",
            "publie",
            "archive",
        }

        if statut_publication not in statuts_valides:
            raise SmartCampusException(
                message=(
                    "statut_publication doit être l'une des valeurs suivantes : "
                    "brouillon, publie, archive."
                ),
                status_code=400,
            )

        if (
            date_debut_validite is not None
            and date_fin_validite is not None
            and date_fin_validite < date_debut_validite
        ):
            raise SmartCampusException(
                message=(
                    "La date de fin de validité doit être supérieure "
                    "ou égale à la date de début."
                ),
                status_code=400,
            )

    @staticmethod
    def create_condition_admission(payload: dict) -> dict:
        programme_id = payload.get("programme_id")
        programme_pedagogique_id = payload.get(
            "programme_pedagogique_id"
        )

        ConditionAdmissionService._valider_parents(
            programme_id,
            programme_pedagogique_id,
        )

        statut_publication = payload.get(
            "statut_publication",
            "publie",
        )

        date_debut_validite = payload.get(
            "date_debut_validite"
        )

        date_fin_validite = payload.get(
            "date_fin_validite"
        )

        ConditionAdmissionService._valider_publication(
            statut_publication,
            date_debut_validite,
            date_fin_validite,
        )

        values = {
            "programme_id": programme_id,
            "programme_pedagogique_id": programme_pedagogique_id,
            "type_condition": payload["type_condition"],
            "description": payload["description"],
            "valeur": payload.get("valeur"),
            "obligatoire": payload.get(
                "obligatoire",
                True,
            ),
            "actif": payload.get(
                "actif",
                True,
            ),
            "statut_publication": statut_publication,
            "date_debut_validite": date_debut_validite,
            "date_fin_validite": date_fin_validite,
        }

        return ConditionAdmissionRepository.insert_row(values)

    @staticmethod
    def update_condition_admission(
        condition_id: int,
        **kwargs,
    ) -> dict:

        existing = ConditionAdmissionService.get_or_404(
            condition_id
        )

        data = {
            key: value
            for key, value in kwargs.items()
            if key in ConditionAdmissionRepository.columns
            and key != "id"
        }

        # ---------------------------------------------------------
        # Gestion des parents
        # ---------------------------------------------------------

        if (
            "programme_id" in data
            and "programme_pedagogique_id" not in data
        ):
            if data["programme_id"] is not None:
                data["programme_pedagogique_id"] = None

            elif existing["programme_pedagogique_id"] is None:
                raise SmartCampusException(
                    message=(
                        "Exactement un des deux parents doit être "
                        "renseigné : programme_id ou "
                        "programme_pedagogique_id."
                    ),
                    status_code=400,
                )

        if (
            "programme_pedagogique_id" in data
            and "programme_id" not in data
        ):
            if data["programme_pedagogique_id"] is not None:
                data["programme_id"] = None

            elif existing["programme_id"] is None:
                raise SmartCampusException(
                    message=(
                        "Exactement un des deux parents doit être "
                        "renseigné : programme_id ou "
                        "programme_pedagogique_id."
                    ),
                    status_code=400,
                )

        programme_id = data.get(
            "programme_id",
            existing["programme_id"],
        )

        programme_pedagogique_id = data.get(
            "programme_pedagogique_id",
            existing["programme_pedagogique_id"],
        )

        ConditionAdmissionService._valider_parents(
            programme_id,
            programme_pedagogique_id,
        )

        # ---------------------------------------------------------
        # Validation publication / validité
        # ---------------------------------------------------------

        statut_publication = data.get(
            "statut_publication",
            existing["statut_publication"],
        )

        date_debut_validite = data.get(
            "date_debut_validite",
            existing["date_debut_validite"],
        )

        date_fin_validite = data.get(
            "date_fin_validite",
            existing["date_fin_validite"],
        )

        ConditionAdmissionService._valider_publication(
            statut_publication,
            date_debut_validite,
            date_fin_validite,
        )

        # ---------------------------------------------------------
        # Aucun changement
        # ---------------------------------------------------------

        if not data:
            return existing

        updated = ConditionAdmissionRepository.update_row(
            condition_id,
            data,
        )

        if updated is None:
            raise SmartCampusException(
                message=(
                    f"Condition d'admission ID "
                    f"{condition_id} introuvable."
                ),
                status_code=404,
            )

        return updated

    @staticmethod
    def delete_condition_admission(
        condition_id: int,
    ) -> dict:
        return ConditionAdmissionService.delete(
            condition_id
        )