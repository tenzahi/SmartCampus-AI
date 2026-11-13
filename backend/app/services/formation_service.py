import logging
from typing import Optional
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.database import engine
from app.schemas.formation import FormationCreate, FormationRead, FormationUpdate
from app.core.exceptions import SmartCampusException


logger = logging.getLogger(__name__)


class FormationService:
    """Service layer for formation business logic."""

    @staticmethod
    def list_formations(
        etablissement: Optional[str] = None,
        niveau: Optional[str] = None,
        q: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """Récupérer la liste des formations avec filtres facultatifs.

        Valide : skip >= 0, limit >= 1.
        Utilise ILIKE pour la recherche insensible à la casse.
        """
        # Validation des paramètres
        if skip < 0:
            raise ValueError("skip doit être >= 0.")
        if limit < 1:
            raise ValueError("limit doit être >= 1.")

        query = (
            "SELECT id, etablissement, nom, niveau, description "
            "FROM programmes WHERE 1=1"
        )
        params = {}

        if etablissement is not None:
            # L'établissement est déjà validé comme étant IIT ou ISB dans les schemas
            query += " AND etablissement = :etablissement"
            params["etablissement"] = etablissement.strip().upper()

        if niveau is not None:
            # Filtre insensible à la casse : utiliser ILIKE ou comparaison upper niveau
            # On stocke le niveau tel quel dans la DB, mais le filtre est insensible
            query += " AND UPPER(niveau) = :niveau"
            params["niveau"] = niveau.strip().upper()

        if q is not None:
            search = f"%{q}%"
            query += " AND LOWER(nom) LIKE LOWER(:q)"
            params["q"] = search

        query += " ORDER BY id OFFSET :skip ROWS FETCH NEXT :limit ROWS ONLY"
        params["skip"] = skip
        params["limit"] = limit

        with engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()
            return [dict(r) for r in rows]

    @staticmethod
    def get_formation_by_id(formation_id: int) -> Optional[dict]:
        """Récupérer une formation par son ID. Retourne None si introuvable."""
        query = (
            "SELECT id, etablissement, nom, niveau, description "
            "FROM programmes WHERE id = :id"
        )

        with engine.connect() as conn:
            row = conn.execute(text(query), {"id": formation_id}).mappings().first()
            if row is None:
                return None
            return dict(row)

    @staticmethod
    def create_formation(payload: dict) -> dict:
        """Créer une nouvelle formation à partir d'un dictionnaire.

        Lève SmartCampusException en cas de doublon.
        La clé 'description' peut être None pour la définir à NULL.
        """
        nom = payload.get("nom")
        etablissement = payload.get("etablissement")
        niveau = payload.get("niveau")
        description = payload.get("description")

        # Vérifier d'abord si un nom existe déjà dans le même établissement
        existing = FormationService._check_duplicate(nom, etablissement)
        if existing:
            raise SmartCampusException(
                message="Un nom de formation identique existe déjà dans cet établissement.",
                status_code=409,
            )

        query = (
            "INSERT INTO programmes (etablissement, nom, niveau, description) "
            "VALUES (:etablissement, :nom, :niveau, :description) "
            "RETURNING id, etablissement, nom, niveau, description"
        )

        params = {
            "etablissement": etablissement.strip().upper() if etablissement else etablissement,
            "nom": nom,
            "niveau": niveau,  # Pas de .upper() : on preserve la valeur existante
            "description": description,
        }

        try:
            with engine.connect() as conn:
                try:
                    result = conn.execute(text(query), params)
                    row = result.mappings().first()  # Fetch once
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
            if row is None:
                raise SmartCampusException(
                    message="Création de la formation impossible.",
                    status_code=500,
                )
            return dict(row)  # Return the stored row
        except SmartCampusException:
            raise
        except IntegrityError as e:
            logger.error(f"IntegrityError during creation: {e}")
            raise SmartCampusException(
                message="Erreur de contrainte lors de la création de la formation.",
                status_code=409,
            )
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemyError during creation: {e}")
            raise SmartCampusException(
                message="Erreur base de données lors de la création.",
                status_code=500,
            )
        except Exception as e:
            logger.error(f"Unexpected error during creation: {e}")
            raise SmartCampusException(
                message="Erreur inattendue lors de la création de la formation.",
                status_code=500,
            )

    @staticmethod
    def update_formation(formation_id: int, **kwargs) -> dict:
        """Mettre à jour une formation.

        Accepte des clés facultatives via **kwargs (venues de model_dump(exclude_unset=True)).
        Distingue les champs omis (absents de kwargs) des champs explicitement définis à None.

        Règles :
        - Champ absent de kwargs → garder la valeur existante
        - Champ présent avec valeur None → réinitialiser (pour description) ou invalide pour les autres
        - Champ présent avec une valeur → utiliser cette valeur
        """
        # Vérifier d'abord que la formation existe
        existing = FormationService.get_formation_by_id(formation_id)
        if existing is None:
            raise SmartCampusException(
                message=f"Formation ID {formation_id} introuvable.",
                status_code=404,
            )

        # Extraire les valeurs effectives depuis kwargs, avec fallback sur les valeurs existantes
        # Pour chaque champ, on vérifie s'il est présent dans kwargs
        effective_nom = kwargs.get("nom", existing["nom"])
        effective_etab = kwargs.get("etablissement", existing["etablissement"])
        effective_niveau = kwargs.get("niveau", existing["niveau"])
        # Pour description : None signifie réinitialisation explicite, absent signifie garder existant
        if "description" in kwargs:
            effective_description = kwargs["description"]  # Peut être None pour reset ou une chaîne
        else:
            effective_description = existing.get("description", None)  # Garder la valeur existante

        # Vérifier le doublon si le nom change (exclure l'ID courant) - on vérifie le PAIR (nom, etablissement)
        if effective_nom != existing["nom"] or effective_etab != existing["etablissement"]:
            dup = FormationService._check_duplicate_pair(
                effective_nom, effective_etab, formation_id
            )
            if dup:
                raise SmartCampusException(
                    message="Un nom de formation identique existe déjà dans cet établissement.",
                    status_code=409,
                )

        # Construire les parties UPDATE dynamiquement
        update_parts = []
        params = {"id": formation_id}

        if effective_nom is not None and effective_nom != existing["nom"]:
            update_parts.append("nom = :nom")
            params["nom"] = effective_nom

        if effective_etab is not None and effective_etab != existing["etablissement"]:
            update_parts.append("etablissement = :etablissement")
            params["etablissement"] = effective_etab.upper().strip()

        if effective_niveau is not None and effective_niveau != existing["niveau"]:
            # Pas de .upper() : on conserve la casse telle quelle
            update_parts.append("niveau = :niveau")
            params["niveau"] = effective_niveau

        # Gestion de la description : distinguer "présent avec None" (→ NULL en BDD)
        # de "absent" (→ conserver la valeur existante)
        if "description" in kwargs:
            # Explicitement passé (même à None) : on met à jour la colonne
            update_parts.append("description = :description")
            params["description"] = kwargs["description"]  # Peut être None → SET NULL
        # else : description absente du dictionnaire → on ne touche pas à la colonne existante

        if not update_parts:
            return existing

        query = f"""
            UPDATE programmes
            SET {", ".join(update_parts)}
            WHERE id = :id
            RETURNING id, etablissement, nom, niveau, description
        """

        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            row = result.mappings().first()
            if row is None:
                raise SmartCampusException(
                    message=f"Formation ID {formation_id} introuvable après mise à jour.",
                    status_code=404,
                )
            conn.commit()
            return dict(row)

    @staticmethod
    def delete_formation(formation_id: int) -> dict:
        """Supprimer une formation. Lève 404 si introuvable, 409 en cas de conflit FK.

        Règle : attraper IntegrityError directement depuis la DELETE,
        et non se reposer uniquement sur le compte de candidats.
        """
        # Vérifier d'abord que la formation existe
        existing = FormationService.get_formation_by_id(formation_id)
        if existing is None:
            raise SmartCampusException(
                message=f"Formation ID {formation_id} introuvable.",
                status_code=404,
            )

        # Essayer de supprimer directement ; capturer l'IntegrityError
        # qui survient si des FK externes (autres que candidats) bloquent la suppression.
        delete_query = "DELETE FROM programmes WHERE id = :id"

        try:
            with engine.connect() as conn:
                try:
                    result = conn.execute(text(delete_query), {"id": formation_id})
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
            # Si result.rowcount = 0, la formation n'existait pas (déjà traitée ci-dessus)
            if result.rowcount == 0:
                raise SmartCampusException(
                    message=f"Formation ID {formation_id} introuvable après suppression.",
                    status_code=404,
                )
            return {"detail": f"Formation ID {formation_id} supprimée avec succès."}
        except SmartCampusException:
            raise
        except IntegrityError as e:
            logger.error(f"IntegrityError during deletion of formation {formation_id}: {e}")
            raise SmartCampusException(
                message="Impossible de supprimer cette formation : elle est référencée par d'autres enregistrements.",
                status_code=409,
            )
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemyError during deletion of formation {formation_id}: {e}")
            raise SmartCampusException(
                message="Erreur base de données lors de la suppression.",
                status_code=500,
            )
        except Exception as e:
            logger.error(f"Unexpected error during deletion of formation {formation_id}: {e}")
            raise SmartCampusException(
                message="Erreur inattendue lors de la suppression de la formation.",
                status_code=500,
            )

    @staticmethod
    def _check_duplicate(nom: str, etablissement: str) -> bool:
        """Vérifier si un nom de formation existe déjà dans le même établissement."""
        query = (
            "SELECT COUNT(*) AS cnt FROM programmes "
            "WHERE nom = :nom AND etablissement = :etablissement"
        )
        with engine.connect() as conn:
            result = conn.execute(text(query), {
                "nom": nom,
                "etablissement": etablissement.upper().strip(),
            })
            row = result.mappings().first()
            return row["cnt"] > 0 if row else False

    @staticmethod
    def _check_duplicate_pair(nom: str, etablissement: str, exclusion_id: int) -> bool:
        """Vérifier le doublon en utilisant le pair (nom, établissement), en excluant l'ID courant.

        Cette méthode est appelée à chaque fois que soit le nom OU l'établissement change.
        Elle garantit que la combinaison nom+établissement est unique.
        """
        query = (
            "SELECT COUNT(*) AS cnt FROM programmes "
            "WHERE nom = :nom AND etablissement = :etablissement AND id != :exclusion_id"
        )
        with engine.connect() as conn:
            result = conn.execute(text(query), {
                "nom": nom,
                "etablissement": etablissement.upper().strip(),
                "exclusion_id": exclusion_id,
            })
            row = result.mappings().first()
            return row["cnt"] > 0 if row else False