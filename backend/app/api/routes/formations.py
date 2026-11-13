from fastapi import APIRouter, Depends, Query, status
from typing import Optional, List

from app.core.dependencies import catalogue_writer
from app.core.exceptions import SmartCampusException
from app.services.formation_service import FormationService
from app.schemas.formation import FormationCreate, FormationRead, FormationUpdate

router = APIRouter(prefix="/api/formations", tags=["formations"])


@router.get("", response_model=List[FormationRead], summary="Lister les formations")
def list_formations(
    etablissement: Optional[str] = None,
    niveau: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = Query(default=0, ge=0, description="Nombre d'enregistrements à sauter (>= 0)"),
    limit: int = Query(default=100, ge=1, description="Nombre maximum d'enregistrements à retourner (>= 1)"),
):
    """Lister toutes les formations avec filtres facultatifs.

    - **etablissement** : Filtrer par 'IIT' ou 'ISB'
    - **niveau** : Filtrer par niveau (insensible à la casse)
    - **q** : Recherche par texte dans le nom (insensible à la casse)
    - **skip** : Nombre d'enregistrements à sauter (pagination, >= 0)
    - **limit** : Nombre maximum d'enregistrements à retourner (>= 1)
    """
    formations = FormationService.list_formations(
        etablissement=etablissement,
        niveau=niveau,
        q=q,
        skip=skip,
        limit=limit,
    )
    return formations


@router.get("/{formation_id}", response_model=FormationRead, summary="Récupérer une formation par ID")
def get_formation(formation_id: int):
    """Récupérer une formation spécifique par son ID.

    Lève **404** si la formation n'existe pas.
    """
    formation = FormationService.get_formation_by_id(formation_id)
    if formation is None:
        raise SmartCampusException(
            message="Formation introuvable.",
            status_code=404,
        )
    return formation


@router.post("", response_model=FormationRead, status_code=status.HTTP_201_CREATED, summary="Créer une formation")
def create_formation(
    payload: FormationCreate,
    _user: object = Depends(catalogue_writer),
):
    """Créer une nouvelle formation.

    Lève **409** si un nom identique existe déjà dans le même établissement.
    """
    try:
        creation = FormationService.create_formation(payload.model_dump())
        return creation
    except SmartCampusException:
        raise
    except Exception:
        # Ne jamais exposer les messages d'erreur internes au client
        raise SmartCampusException(
            message="Erreur inattendue lors de la création d'une formation.",
            status_code=500,
        )


@router.put("/{formation_id}", response_model=FormationRead, summary="Mettre à jour une formation")
def update_formation(
    formation_id: int,
    payload: FormationUpdate,
    _user: object = Depends(catalogue_writer),
):
    """Mettre à jour une formation existante.

    Lève **404** si la formation n'existe pas.
    Lève **409** si le nouveau nom en doublon dans le même établissement.
    """
    # Utilisation de model_dump(exclude_unset=True) pour distinguer
    # les champs omis des champs explicitly définis à None
    dump_data = payload.model_dump(exclude_unset=True)

    try:
        formation = FormationService.update_formation(
            formation_id=formation_id,
            **dump_data,
        )
        return formation
    except SmartCampusException:
        raise
    except Exception:
        # Ne jamais exposer les messages d'erreur internes au client
        raise SmartCampusException(
            message="Erreur inattendue lors de la mise à jour de la formation.",
            status_code=500,
        )


@router.delete("/{formation_id}", summary="Supprimer une formation", status_code=status.HTTP_200_OK)
def delete_formation(
    formation_id: int,
    _user: object = Depends(catalogue_writer),
):
    """Supprimer une formation par son ID.

    Lève **404** si la formation n'existe pas.
    Lève **409** si la suppression est bloquée par une contrainte FK.
    """
    try:
        result = FormationService.delete_formation(formation_id)
        return result
    except SmartCampusException:
        raise
    except Exception:
        # Ne jamais exposer les messages d'erreur internes au client
        raise SmartCampusException(
            message="Erreur inattendue lors de la suppression de la formation.",
            status_code=500,
        )