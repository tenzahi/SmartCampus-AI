"""Socle commun aux services du catalogue académique.

Ce module centralise l'accès SQL et les règles communes (lecture paginée,
recherche, existence, création, mise à jour, suppression). Les services
métier de chaque entité ne conservent que leurs règles propres : validation
des parents, unicité et messages fonctionnels.
"""

import logging
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.database import engine
from app.core.exceptions import SmartCampusException


logger = logging.getLogger(__name__)


class CatalogueRepository:
    """Dépôt SQL générique pour une table du catalogue."""

    table: str = ""
    columns: tuple[str, ...] = ()
    search_columns: tuple[str, ...] = ()
    entity_label: str = "enregistrement"
    integrity_message: str = (
        "Un enregistrement viole une contrainte d'intégrité."
    )
    database_message: str = "Erreur base de données."

    @classmethod
    def _select_columns(cls) -> str:
        return ", ".join(cls.columns)

    @classmethod
    def _build_where(
        cls,
        conditions: dict[str, Any],
        exclude_id: Optional[int] = None,
    ) -> tuple[str, dict[str, Any]]:
        """Construire une clause WHERE à partir de conditions sûres.

        Les clés proviennent uniquement des services (jamais du client) et
        sont vérifiées contre les colonnes déclarées.
        """
        clauses: list[str] = []
        params: dict[str, Any] = {}

        for key, value in conditions.items():
            if key not in cls.columns:
                raise ValueError(f"Colonne inconnue : {key}")
            if value is None:
                clauses.append(f"{key} IS NULL")
            else:
                clauses.append(f"{key} = :{key}")
                params[key] = value

        if exclude_id is not None:
            clauses.append("id != :exclude_id")
            params["exclude_id"] = exclude_id

        if not clauses:
            return "1=1", params
        return " AND ".join(clauses), params

    @classmethod
    def list_rows(
        cls,
        filters: dict[str, Any],
        q: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """Lister les lignes avec filtres exacts et recherche textuelle."""
        if skip < 0:
            raise ValueError("skip doit être >= 0.")
        if limit < 1:
            raise ValueError("limit doit être >= 1.")

        where_parts: list[str] = []
        params: dict[str, Any] = {"skip": skip, "limit": limit}

        for key, value in filters.items():
            if value is None:
                continue
            if key not in cls.columns:
                raise ValueError(f"Colonne inconnue : {key}")
            where_parts.append(f"{key} = :{key}")
            params[key] = value

        if q is not None and q.strip():
            params["q"] = f"%{q.strip()}%"
            search_parts = [
                f"LOWER(COALESCE({column}, '')) LIKE LOWER(:q)"
                for column in cls.search_columns
            ]
            if search_parts:
                where_parts.append(f"({' OR '.join(search_parts)})")

        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        query = (
            f"SELECT {cls._select_columns()} FROM {cls.table} "
            f"WHERE {where_clause} "
            "ORDER BY id OFFSET :skip ROWS FETCH NEXT :limit ROWS ONLY"
        )

        try:
            with engine.connect() as conn:
                rows = conn.execute(text(query), params).mappings().all()
                return [dict(row) for row in rows]
        except SQLAlchemyError as exc:
            logger.error("Erreur de lecture sur %s : %s", cls.table, exc)
            raise SmartCampusException(
                message=cls.database_message,
                status_code=500,
            )

    @classmethod
    def get_row(cls, entity_id: int) -> Optional[dict]:
        query = (
            f"SELECT {cls._select_columns()} FROM {cls.table} "
            "WHERE id = :id"
        )
        try:
            with engine.connect() as conn:
                row = (
                    conn.execute(text(query), {"id": entity_id})
                    .mappings()
                    .first()
                )
                return dict(row) if row is not None else None
        except SQLAlchemyError as exc:
            logger.error("Erreur de lecture sur %s : %s", cls.table, exc)
            raise SmartCampusException(
                message=cls.database_message,
                status_code=500,
            )

    @classmethod
    def exists(
        cls,
        conditions: dict[str, Any],
        exclude_id: Optional[int] = None,
    ) -> bool:
        where_clause, params = cls._build_where(conditions, exclude_id)
        query = (
            f"SELECT 1 AS found FROM {cls.table} "
            f"WHERE {where_clause} LIMIT 1"
        )
        try:
            with engine.connect() as conn:
                return conn.execute(text(query), params).first() is not None
        except SQLAlchemyError as exc:
            logger.error("Erreur d'existence sur %s : %s", cls.table, exc)
            raise SmartCampusException(
                message=cls.database_message,
                status_code=500,
            )

    @classmethod
    def insert_row(cls, values: dict[str, Any]) -> dict:
        data = {
            key: value
            for key, value in values.items()
            if key in cls.columns and key != "id"
        }
        if not data:
            raise ValueError("Aucune colonne à insérer.")

        columns = ", ".join(data.keys())
        placeholders = ", ".join(f":{key}" for key in data)
        query = (
            f"INSERT INTO {cls.table} ({columns}) "
            f"VALUES ({placeholders}) "
            f"RETURNING {cls._select_columns()}"
        )

        try:
            with engine.connect() as conn:
                try:
                    row = (
                        conn.execute(text(query), data)
                        .mappings()
                        .first()
                    )
                    if row is None:
                        raise SmartCampusException(
                            message=f"Création impossible pour {cls.entity_label}.",
                            status_code=500,
                        )
                    conn.commit()
                    return dict(row)
                except Exception:
                    conn.rollback()
                    raise
        except IntegrityError as exc:
            logger.error("IntegrityError sur %s : %s", cls.table, exc)
            raise SmartCampusException(
                message=cls.integrity_message,
                status_code=409,
            )
        except SQLAlchemyError as exc:
            logger.error("SQLAlchemyError sur %s : %s", cls.table, exc)
            raise SmartCampusException(
                message=cls.database_message,
                status_code=500,
            )

    @classmethod
    def update_row(cls, entity_id: int, values: dict[str, Any]) -> Optional[dict]:
        data = {
            key: value
            for key, value in values.items()
            if key in cls.columns and key != "id"
        }
        if not data:
            return cls.get_row(entity_id)

        set_clause = ", ".join(f"{key} = :{key}" for key in data)
        params = dict(data)
        params["id"] = entity_id
        query = (
            f"UPDATE {cls.table} "
            f"SET {set_clause} "
            "WHERE id = :id "
            f"RETURNING {cls._select_columns()}"
        )

        try:
            with engine.connect() as conn:
                try:
                    row = (
                        conn.execute(text(query), params)
                        .mappings()
                        .first()
                    )
                    conn.commit()
                    return dict(row) if row is not None else None
                except Exception:
                    conn.rollback()
                    raise
        except IntegrityError as exc:
            logger.error("IntegrityError sur %s : %s", cls.table, exc)
            raise SmartCampusException(
                message=cls.integrity_message,
                status_code=409,
            )
        except SQLAlchemyError as exc:
            logger.error("SQLAlchemyError sur %s : %s", cls.table, exc)
            raise SmartCampusException(
                message=cls.database_message,
                status_code=500,
            )

    @classmethod
    def delete_row(cls, entity_id: int) -> int:
        query = f"DELETE FROM {cls.table} WHERE id = :id"
        try:
            with engine.connect() as conn:
                try:
                    result = conn.execute(text(query), {"id": entity_id})
                    conn.commit()
                    return result.rowcount
                except Exception:
                    conn.rollback()
                    raise
        except IntegrityError as exc:
            logger.error("IntegrityError sur %s : %s", cls.table, exc)
            raise SmartCampusException(
                message=(
                    f"Impossible de supprimer cet enregistrement de "
                    f"{cls.entity_label} : il est référencé par d'autres "
                    "enregistrements."
                ),
                status_code=409,
            )
        except SQLAlchemyError as exc:
            logger.error("SQLAlchemyError sur %s : %s", cls.table, exc)
            raise SmartCampusException(
                message=cls.database_message,
                status_code=500,
            )


class BaseCatalogueService:
    """Règles communes aux entités du catalogue."""

    repository: type[CatalogueRepository] = CatalogueRepository
    entity_label: str = "Enregistrement"

    @classmethod
    def list(
        cls,
        filters: dict[str, Any],
        q: Optional[str],
        skip: int,
        limit: int,
    ) -> list[dict]:
        return cls.repository.list_rows(filters, q=q, skip=skip, limit=limit)

    @classmethod
    def get(cls, entity_id: int) -> Optional[dict]:
        return cls.repository.get_row(entity_id)

    @classmethod
    def get_or_404(cls, entity_id: int) -> dict:
        row = cls.get(entity_id)
        if row is None:
            raise SmartCampusException(
                message=f"{cls.entity_label} ID {entity_id} introuvable.",
                status_code=404,
            )
        return row

    @classmethod
    def delete(cls, entity_id: int) -> dict:
        cls.get_or_404(entity_id)
        cls.repository.delete_row(entity_id)
        return {
            "detail": (
                f"{cls.entity_label} ID {entity_id} supprimé(e) avec succès."
            )
        }

    @classmethod
    def ensure_unique(
        cls,
        conditions: dict[str, Any],
        message: str,
        exclude_id: Optional[int] = None,
    ) -> None:
        if cls.repository.exists(conditions, exclude_id=exclude_id):
            raise SmartCampusException(message=message, status_code=409)
