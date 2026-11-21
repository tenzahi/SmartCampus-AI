from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.routes._service_call import call_service
from app.core.dependencies import catalogue_writer
from app.schemas.specialite import (
    SpecialiteCreate,
    SpecialiteRead,
    SpecialiteUpdate,
)
from app.services.specialite_service import SpecialiteService

router = APIRouter(prefix="/api/specialites", tags=["specialites"])


@router.get(
    "",
    response_model=List[SpecialiteRead],
    summary="Lister les spécialités",
)
def list_specialites(
    programme_id: Optional[int] = Query(
        default=None, ge=1, description="Filtrer par programme"
    ),
    q: Optional[str] = Query(
        default=None, description="Recherche sur le nom, le code ou la description"
    ),
    actif: Optional[bool] = Query(
        default=None, description="Filtrer par état actif/inactif"
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    return call_service(
        lambda: SpecialiteService.list_specialites(
            programme_id=programme_id,
            q=q,
            actif=actif,
            skip=skip,
            limit=limit,
        ),
        "Erreur inattendue lors de la lecture des spécialités.",
    )


@router.get(
    "/{specialite_id}",
    response_model=SpecialiteRead,
    summary="Récupérer une spécialité par ID",
)
def get_specialite(specialite_id: int):
    return call_service(
        lambda: SpecialiteService.get_or_404(specialite_id),
        "Erreur inattendue lors de la lecture de la spécialité.",
    )


@router.post(
    "",
    response_model=SpecialiteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une spécialité",
)
def create_specialite(
    payload: SpecialiteCreate,
    _user: object = Depends(catalogue_writer),
):
    return call_service(
        lambda: SpecialiteService.create_specialite(payload.model_dump()),
        "Erreur inattendue lors de la création de la spécialité.",
    )


@router.put(
    "/{specialite_id}",
    response_model=SpecialiteRead,
    summary="Mettre à jour une spécialité",
)
def update_specialite(
    specialite_id: int,
    payload: SpecialiteUpdate,
    _user: object = Depends(catalogue_writer),
):
    return call_service(
        lambda: SpecialiteService.update_specialite(
            specialite_id,
            **payload.model_dump(exclude_unset=True),
        ),
        "Erreur inattendue lors de la mise à jour de la spécialité.",
    )


@router.delete(
    "/{specialite_id}",
    summary="Supprimer une spécialité",
    status_code=status.HTTP_200_OK,
)
def delete_specialite(
    specialite_id: int,
    _user: object = Depends(catalogue_writer),
):
    return call_service(
        lambda: SpecialiteService.delete_specialite(specialite_id),
        "Erreur inattendue lors de la suppression de la spécialité.",
    )
