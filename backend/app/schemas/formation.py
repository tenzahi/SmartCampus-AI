from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FormationCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=150, description="Nom de la formation")
    etablissement: str = Field(..., max_length=10, description="Établissant (IIT ou ISB)")
    niveau: str = Field(..., max_length=50, description="Niveau (Licence, Prépa, Ingénierie...)")
    description: Optional[str] = Field(None, description="Description optionnelle")

    @field_validator("etablissement")
    def etablissement_must_be_iit_or_isb(cls, v: str) -> str:
        """Valider strictement que l'établissement est IIT ou ISB."""
        val = v.strip().upper()
        if val not in ("IIT", "ISB"):
            raise ValueError("L'établissement doit être 'IIT' ou 'ISB'.")
        return val

    @field_validator("nom")
    def nom_non_vide(cls, v: str) -> str:
        """S'assurer que le nom n'est pas vide après strip."""
        if not v.strip():
            raise ValueError("Le nom ne peut pas être vide.")
        return v.strip()

    @field_validator("niveau")
    def niveau_non_vide_preserve_capitalisation(cls, v: str) -> str:
        """Valider que niveau n'est pas vide après strip, garder la capitalisation d'origine."""
        if not v.strip():
            raise ValueError("Le niveau ne peut pas être vide.")
        return v.strip()


class FormationRead(BaseModel):
    id: int
    nom: str
    etablissement: str
    niveau: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FormationUpdate(BaseModel):
    nom: Optional[str] = Field(None, min_length=1, max_length=150, description="Nom de la formation (omettre pour garder la valeur existante)")
    etablissement: Optional[str] = Field(None, max_length=10, description="Établissant (IIT ou ISB, omettre pour garder la valeur existante)")
    niveau: Optional[str] = Field(None, max_length=50, description="Niveau (Licence, Prépa, Ingénierie, omettre pour garder la valeur existante)")
    description: Optional[str] = Field(None, description="Description (None pour remettre à NULL, omettre pour garder la valeur existante)")

    @field_validator("etablissement", mode="before")
    def etablissement_before(cls, v):
        if v is None:
            return v
        return v.strip()

    @field_validator("etablissement")
    def etablissement_must_be_iit_or_isb(cls, v: str) -> str:
        """Valider strictement que l'établissement est IIT ou ISB (même en UPDATE)."""
        if v is None:
            return v
        val = v.strip().upper()
        if val not in ("IIT", "ISB"):
            raise ValueError("L'établissement doit être 'IIT' ou 'ISB'.")
        return val

    @field_validator("nom")
    def nom_non_vide(cls, v: str) -> str:
        """Rejouter blank/whitespace-only ; stripper si valide."""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Le nom ne peut pas être vide ou ne contenir que des espaces.")
        return v.strip()

    @field_validator("niveau", mode="before")
    def niveau_before(cls, v):
        if v is None:
            return v
        return v.strip()

    @field_validator("niveau")
    def niveau_non_vide_et_validation(cls, v: str) -> str:
        """Valider non vide après strip, préserver capitalisation."""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Le niveau ne peut pas être vide.")
        return v.strip()