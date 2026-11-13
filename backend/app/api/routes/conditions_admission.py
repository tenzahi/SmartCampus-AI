from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.routes._service_call import call_service
from app.core.dependencies import catalogue_writer
from app.schemas.condition_admission import (
    ConditionAdmissionCreate,
    ConditionAdmissionRead,
    ConditionAdmissionUpdate,
)
from app.services.condition_admission_service import (
    ConditionAdmissionService,
)

router = APIRouter(
    prefix="/api/conditions-admission",
    tags=["conditions-admission"],
)


@router.get(
    "",
    response_model=List[ConditionAdmissionRead],
    summary="Lister les conditions d'admission",
)
def list_conditions_admission(
    programme_id: Optional[int] = Query(default=None, ge=1),
    programme_pedagogique_id: Optional[int] = Query(default=None, ge=1),
    type_condition: Optional[str] = Query(default=None),
    obligatoire: Optional[bool] = Query(default=None),
    q: Optional[str] = Query(
        default=None,
        description="Recherche sur le type, la description ou la valeur",
    ),
    actif: Optional[bool] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    return call_service(
        lambda: ConditionAdmissionService.list_conditions_admission(
            programme_id=programme_id,
            programme_pedagogique_id=programme_pedagogique_id,
            type_condition=type_condition,
            obligatoire=obligatoire,
            q=q,
            actif=actif,
            skip=skip,
            limit=limit,
        ),
        "Erreur inattendue lors de la lecture des conditions d'admission.",
    )


@router.get(
    "/{condition_id}",
    response_model=ConditionAdmissionRead,
    summary="Récupérer une condition d'admission par ID",
)
def get_condition_admission(condition_id: int):
    return call_service(
        lambda: ConditionAdmissionService.get_or_404(condition_id),
        "Erreur inattendue lors de la lecture de la condition d'admission.",
    )


@router.post(
    "",
    response_model=ConditionAdmissionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une condition d'admission",
)
def create_condition_admission(
    payload: ConditionAdmissionCreate,
    _user: object = Depends(catalogue_writer),
):
    return call_service(
        lambda: ConditionAdmissionService.create_condition_admission(
            payload.model_dump()
        ),
        "Erreur inattendue lors de la création de la condition d'admission.",
    )


@router.put(
    "/{condition_id}",
    response_model=ConditionAdmissionRead,
    summary="Mettre à jour une condition d'admission",
)
def update_condition_admission(
    condition_id: int,
    payload: ConditionAdmissionUpdate,
    _user: object = Depends(catalogue_writer),
):
    return call_service(
        lambda: ConditionAdmissionService.update_condition_admission(
            condition_id,
            **payload.model_dump(exclude_unset=True),
        ),
        "Erreur inattendue lors de la mise à jour de la condition d'admission.",
    )


@router.delete(
    "/{condition_id}",
    summary="Supprimer une condition d'admission",
    status_code=status.HTTP_200_OK,
)
def delete_condition_admission(
    condition_id: int,
    _user: object = Depends(catalogue_writer),
):
    return call_service(
        lambda: ConditionAdmissionService.delete_condition_admission(
            condition_id
        ),
        "Erreur inattendue lors de la suppression de la condition d'admission.",
    )
