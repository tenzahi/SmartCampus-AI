from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MatiereCreate(BaseModel):
    programme_pedagogique_id: int = Field(
        ...,
        ge=1,
        description="Identifiant du programme pédagogique parent",
    )
    nom: str = Field(..., min_length=1, max_length=150)
    code: str = Field(..., min_length=1, max_length=30)
    description: Optional[str] = None
    semestre: int = Field(..., ge=1, le=12)
    coefficient: float = Field(..., ge=0, le=99.99)
    volume_horaire: float = Field(..., ge=0, le=999.99)
    credits: int = Field(..., ge=0)
    actif: bool = True

    @field_validator("nom", "code")
    @classmethod
    def non_vide(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Le champ ne peut pas être vide.")
        return value.strip()

    @field_validator("description")
    @classmethod
    def description_normalisee(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class MatiereUpdate(BaseModel):
    programme_pedagogique_id: Optional[int] = Field(None, ge=1)
    nom: Optional[str] = Field(None, min_length=1, max_length=150)
    code: Optional[str] = Field(None, min_length=1, max_length=30)
    description: Optional[str] = None
    semestre: Optional[int] = Field(None, ge=1, le=12)
    coefficient: Optional[float] = Field(None, ge=0, le=99.99)
    volume_horaire: Optional[float] = Field(None, ge=0, le=999.99)
    credits: Optional[int] = Field(None, ge=0)
    actif: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def refuser_null_interdits(cls, data):
        if isinstance(data, dict):
            for field in (
                "programme_pedagogique_id",
                "nom",
                "code",
                "semestre",
                "coefficient",
                "volume_horaire",
                "credits",
                "actif",
            ):
                if field in data and data[field] is None:
                    raise ValueError(f"Le champ '{field}' ne peut pas être null.")
        return data

    @field_validator("nom", "code")
    @classmethod
    def non_vide(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("Le champ ne peut pas être vide.")
        return value.strip()

    @field_validator("description")
    @classmethod
    def description_normalisee(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class MatiereRead(BaseModel):
    id: int
    programme_pedagogique_id: int
    nom: str
    code: str
    description: Optional[str] = None
    semestre: int
    coefficient: float
    volume_horaire: float
    credits: int
    actif: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
