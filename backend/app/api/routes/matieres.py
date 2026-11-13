from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.routes._service_call import call_service
from app.core.dependencies import catalogue_writer
from app.schemas.matiere import MatiereCreate, MatiereRead, MatiereUpdate
from app.services.matiere_service import MatiereService

router = APIRouter(prefix="/api/matieres", tags=["matieres"])


@router.get(
    "",
    response_model=List[MatiereRead],
    summary="Lister les matières",
)
def list_matieres(
    programme_pedagogique_id: Optional[int] = Query(default=None, ge=1),
    semestre: Optional[int] = Query(default=None, ge=1, le=12),
    q: Optional[str] = Query(
        default=None, description="Recherche sur le nom, le code ou la description"
    ),
    actif: Optional[bool] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    return call_service(
        lambda: MatiereService.list_matieres(
            programme_pedagogique_id=programme_pedagogique_id,
            semestre=semestre,
            q=q,
            actif=actif,
            skip=skip,
            limit=limit,
        ),
        "Erreur inattendue lors de la lecture des matières.",
    )


@router.get(
    "/{matiere_id}",
    response_model=MatiereRead,
    summary="Récupérer une matière par ID",
)
def get_matiere(matiere_id: int):
    return call_service(
        lambda: MatiereService.get_or_404(matiere_id),
        "Erreur inattendue lors de la lecture de la matière.",
    )


@router.post(
    "",
    response_model=MatiereRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une matière",
)
def create_matiere(
    payload: MatiereCreate,
    _user: object = Depends(catalogue_writer),
):
    return call_service(
        lambda: MatiereService.create_matiere(payload.model_dump()),
        "Erreur inattendue lors de la création de la matière.",
    )


@router.put(
    "/{matiere_id}",
    response_model=MatiereRead,
    summary="Mettre à jour une matière",
)
def update_matiere(
    matiere_id: int,
    payload: MatiereUpdate,
    _user: object = Depends(catalogue_writer),
):
    return call_service(
        lambda: MatiereService.update_matiere(
            matiere_id,
            **payload.model_dump(exclude_unset=True),
        ),
        "Erreur inattendue lors de la mise à jour de la matière.",
    )


@router.delete(
    "/{matiere_id}",
    summary="Supprimer une matière",
    status_code=status.HTTP_200_OK,
)
def delete_matiere(
    matiere_id: int,
    _user: object = Depends(catalogue_writer),
):
    return call_service(
        lambda: MatiereService.delete_matiere(matiere_id),
        "Erreur inattendue lors de la suppression de la matière.",
    )
