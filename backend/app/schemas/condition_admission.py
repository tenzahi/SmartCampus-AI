from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ConditionAdmissionCreate(BaseModel):
    programme_id: Optional[int] = Field(
        None,
        ge=1,
        description="Programme parent (exclusif avec programme_pedagogique_id)",
    )
    programme_pedagogique_id: Optional[int] = Field(
        None,
        ge=1,
        description="Programme pédagogique parent (exclusif avec programme_id)",
    )
    type_condition: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1)
    valeur: Optional[str] = Field(None, max_length=100)
    obligatoire: bool = True
    actif: bool = True

    @field_validator("type_condition", "description")
    @classmethod
    def non_vide(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Le champ ne peut pas être vide.")
        return value.strip()

    @field_validator("valeur")
    @classmethod
    def valeur_normalisee(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def parent_exclusif(self):
        if (self.programme_id is None) == (
            self.programme_pedagogique_id is None
        ):
            raise ValueError(
                "Exactement un des deux parents doit être renseigné : "
                "programme_id ou programme_pedagogique_id."
            )
        return self


class ConditionAdmissionUpdate(BaseModel):
    programme_id: Optional[int] = Field(None, ge=1)
    programme_pedagogique_id: Optional[int] = Field(None, ge=1)
    type_condition: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, min_length=1)
    valeur: Optional[str] = Field(None, max_length=100)
    obligatoire: Optional[bool] = None
    actif: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def refuser_null_interdits(cls, data):
        if isinstance(data, dict):
            for field in (
                "type_condition",
                "description",
                "obligatoire",
                "actif",
            ):
                if field in data and data[field] is None:
                    raise ValueError(f"Le champ '{field}' ne peut pas être null.")
        return data

    @field_validator("type_condition", "description")
    @classmethod
    def non_vide(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("Le champ ne peut pas être vide.")
        return value.strip()

    @field_validator("valeur")
    @classmethod
    def valeur_normalisee(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ConditionAdmissionRead(BaseModel):
    id: int
    programme_id: Optional[int] = None
    programme_pedagogique_id: Optional[int] = None
    type_condition: str
    description: str
    valeur: Optional[str] = None
    obligatoire: bool
    actif: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
