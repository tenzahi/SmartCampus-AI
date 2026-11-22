import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ANNEE_ACADEMIQUE_PATTERN = re.compile(r"^\d{4}-\d{4}$")


def _valider_annee(value: str) -> str:
    value = value.strip()
    if not ANNEE_ACADEMIQUE_PATTERN.fullmatch(value):
        raise ValueError(
            "L'année académique doit respecter le format AAAA-AAAA."
        )
    return value


class ProgrammePedagogiqueCreate(BaseModel):
    programme_id: int = Field(..., ge=1, description="Identifiant du programme parent")
    specialite_id: Optional[int] = Field(
        None,
        ge=1,
        description="Spécialité du programme (facultative)",
    )
    nom: str = Field(..., min_length=1, max_length=150)
    annee_academique: str = Field(..., min_length=9, max_length=9)
    niveau_etude: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    actif: bool = True

    @field_validator("nom", "niveau_etude")
    @classmethod
    def non_vide(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Le champ ne peut pas être vide.")
        return value.strip()

    @field_validator("annee_academique")
    @classmethod
    def annee_valide(cls, value: str) -> str:
        return _valider_annee(value)

    @field_validator("description")
    @classmethod
    def description_normalisee(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ProgrammePedagogiqueUpdate(BaseModel):
    programme_id: Optional[int] = Field(None, ge=1)
    specialite_id: Optional[int] = Field(None, ge=1)
    nom: Optional[str] = Field(None, min_length=1, max_length=150)
    annee_academique: Optional[str] = Field(None, min_length=9, max_length=9)
    niveau_etude: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    actif: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def refuser_null_interdits(cls, data):
        if isinstance(data, dict):
            for field in (
                "programme_id",
                "nom",
                "annee_academique",
                "niveau_etude",
                "actif",
            ):
                if field in data and data[field] is None:
                    raise ValueError(f"Le champ '{field}' ne peut pas être null.")
        return data

    @field_validator("nom", "niveau_etude")
    @classmethod
    def non_vide(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("Le champ ne peut pas être vide.")
        return value.strip()

    @field_validator("annee_academique")
    @classmethod
    def annee_valide(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _valider_annee(value)

    @field_validator("description")
    @classmethod
    def description_normalisee(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ProgrammePedagogiqueRead(BaseModel):
    id: int
    programme_id: int
    specialite_id: Optional[int] = None
    nom: str
    annee_academique: str
    niveau_etude: str
    description: Optional[str] = None
    actif: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
