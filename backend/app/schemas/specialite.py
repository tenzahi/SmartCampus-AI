from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SpecialiteCreate(BaseModel):
    programme_id: int = Field(..., ge=1, description="Identifiant du programme parent")
    nom: str = Field(..., min_length=1, max_length=150, description="Nom de la spécialité")
    code: str = Field(..., min_length=1, max_length=30, description="Code de la spécialité")
    description: Optional[str] = Field(None, description="Description optionnelle")
    actif: bool = Field(True, description="Indique si la spécialité est active")

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


class SpecialiteUpdate(BaseModel):
    programme_id: Optional[int] = Field(None, ge=1)
    nom: Optional[str] = Field(None, min_length=1, max_length=150)
    code: Optional[str] = Field(None, min_length=1, max_length=30)
    description: Optional[str] = None
    actif: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def refuser_null_interdits(cls, data):
        if isinstance(data, dict):
            for field in ("programme_id", "nom", "code", "actif"):
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


class SpecialiteRead(BaseModel):
    id: int
    programme_id: int
    nom: str
    code: str
    description: Optional[str] = None
    actif: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
