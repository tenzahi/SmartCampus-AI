from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.routes._service_call import call_service
from app.core.dependencies import catalogue_writer
from app.schemas.programme_pedagogique import (
    ProgrammePedagogiqueCreate,
    ProgrammePedagogiqueRead,
    ProgrammePedagogiqueUpdate,
)
from app.services.programme_pedagogique_service import (
    ProgrammePedagogiqueService,
)

router = APIRouter(
    prefix="/api/programmes-pedagogiques",
    tags=["programmes-pedagogiques"],
)


@router.get(
    "",
    response_model=List[ProgrammePedagogiqueRead],
    summary="Lister les programmes pédagogiques",
)
def list_programmes_pedagogiques(
    programme_id: Optional[int] = Query(default=None, ge=1),
    specialite_id: Optional[int] = Query(default=None, ge=1),
    niveau_etude: Optional[str] = Query(default=None),
    annee_academique: Optional[str] = Query(
        default=None, pattern=r"^\d{4}-\d{4}$"
    ),
    q: Optional[str] = Query(
        default=None, description="Recherche sur le nom, le niveau ou la description"
    ),
    actif: Optional[bool] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    return call_service(
        lambda: ProgrammePedagogiqueService.list_programmes_pedagogiques(
            programme_id=programme_id,
            specialite_id=specialite_id,
            niveau_etude=niveau_etude,
            annee_academique=annee_academique,
            q=q,
            actif=actif,
            skip=skip,
            limit=limit,
        ),
        "Erreur inattendue lors de la lecture des programmes pédagogiques.",
    )


@router.get(
    "/{programme_pedagogique_id}",
    response_model=ProgrammePedagogiqueRead,
    summary="Récupérer un programme pédagogique par ID",
)
def get_programme_pedagogique(programme_pedagogique_id: int):
    return call_service(
        lambda: ProgrammePedagogiqueService.get_or_404(
            programme_pedagogique_id
        ),
        "Erreur inattendue lors de la lecture du programme pédagogique.",
    )


@router.post(
    "",
    response_model=ProgrammePedagogiqueRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un programme pédagogique",
)
def create_programme_pedagogique(
    payload: ProgrammePedagogiqueCreate,
    _user: object = Depends(catalogue_writer),
):
    return call_service(
        lambda: ProgrammePedagogiqueService.create_programme_pedagogique(
            payload.model_dump()
        ),
        "Erreur inattendue lors de la création du programme pédagogique.",
    )


@router.put(
    "/{programme_pedagogique_id}",
    response_model=ProgrammePedagogiqueRead,
    summary="Mettre à jour un programme pédagogique",
)
def update_programme_pedagogique(
    programme_pedagogique_id: int,
    payload: ProgrammePedagogiqueUpdate,
    _user: object = Depends(catalogue_writer),
):
    return call_service(
        lambda: ProgrammePedagogiqueService.update_programme_pedagogique(
            programme_pedagogique_id,
            **payload.model_dump(exclude_unset=True),
        ),
        "Erreur inattendue lors de la mise à jour du programme pédagogique.",
    )


@router.delete(
    "/{programme_pedagogique_id}",
    summary="Supprimer un programme pédagogique",
    status_code=status.HTTP_200_OK,
)
def delete_programme_pedagogique(
    programme_pedagogique_id: int,
    _user: object = Depends(catalogue_writer),
):
    return call_service(
        lambda: ProgrammePedagogiqueService.delete_programme_pedagogique(
            programme_pedagogique_id
        ),
        "Erreur inattendue lors de la suppression du programme pédagogique.",
    )
