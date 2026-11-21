import os

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.dependencies import catalogue_writer
from app.core.exceptions import SmartCampusException
from app.main import app
from app.schemas.condition_admission import (
    ConditionAdmissionCreate,
    ConditionAdmissionUpdate,
)
from app.schemas.matiere import MatiereCreate
from app.schemas.programme_pedagogique import ProgrammePedagogiqueCreate
from app.schemas.specialite import SpecialiteCreate
from app.services.catalogue_service import CatalogueRepository
from app.services.condition_admission_service import (
    ConditionAdmissionRepository,
    ConditionAdmissionService,
)
from app.services.formation_service import FormationService
from app.services.matiere_service import MatiereService
from app.services.programme_pedagogique_service import (
    ProgrammePedagogiqueService,
)
from app.services.specialite_service import (
    SpecialiteRepository,
    SpecialiteService,
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def _bypass_rbac():
    """Les tests métier Task20 s'exécutent avec un rédacteur autorisé."""
    app.dependency_overrides[catalogue_writer] = lambda: {
        "id": 1,
        "role": "admin",
    }
    yield
    app.dependency_overrides.pop(catalogue_writer, None)


def _specialite_payload(**overrides):
    payload = {
        "programme_id": 1,
        "nom": "Génie logiciel",
        "code": "GL",
        "description": "Spécialité de démonstration",
        "actif": True,
    }
    payload.update(overrides)
    return payload


def _condition_payload(**overrides):
    payload = {
        "programme_id": 1,
        "type_condition": "Moyenne minimale",
        "description": "Avoir au moins 12/20",
        "valeur": "12",
        "obligatoire": True,
        "actif": True,
    }
    payload.update(overrides)
    return payload


def test_openapi_expose_les_cinq_entites():
    paths = app.openapi()["paths"]

    expected = {
        "/api/formations",
        "/api/formations/{formation_id}",
        "/api/specialites",
        "/api/specialites/{specialite_id}",
        "/api/programmes-pedagogiques",
        "/api/programmes-pedagogiques/{programme_pedagogique_id}",
        "/api/matieres",
        "/api/matieres/{matiere_id}",
        "/api/conditions-admission",
        "/api/conditions-admission/{condition_id}",
    }

    assert expected.issubset(paths.keys())
    for path in expected:
        assert "get" in paths[path]


def test_specialite_refuse_un_nom_vide():
    with pytest.raises(ValidationError):
        SpecialiteCreate(**_specialite_payload(nom="   "))


def test_programme_pedagogique_refuse_une_annee_invalide():
    with pytest.raises(ValidationError):
        ProgrammePedagogiqueCreate(
            programme_id=1,
            nom="Programme test",
            annee_academique="2025/2026",
            niveau_etude="Licence",
        )


def test_matiere_refuse_les_valeurs_hors_bornes():
    base = {
        "programme_pedagogique_id": 1,
        "nom": "Algorithmique",
        "code": "ALGO",
        "semestre": 1,
        "coefficient": 2,
        "volume_horaire": 42,
        "credits": 4,
    }

    with pytest.raises(ValidationError):
        MatiereCreate(**{**base, "semestre": 13})
    with pytest.raises(ValidationError):
        MatiereCreate(**{**base, "coefficient": -1})
    with pytest.raises(ValidationError):
        MatiereCreate(**{**base, "credits": -1})


def test_condition_admission_exige_un_seul_parent():
    with pytest.raises(ValidationError):
        ConditionAdmissionCreate(**_condition_payload(programme_id=None))
    with pytest.raises(ValidationError):
        ConditionAdmissionCreate(
            **_condition_payload(programme_pedagogique_id=2)
        )


def test_condition_admission_update_refuse_null_sur_champ_obligatoire():
    with pytest.raises(ValidationError):
        ConditionAdmissionUpdate(description=None)


@pytest.mark.parametrize(
    ("path", "service", "method"),
    [
        ("/api/specialites", SpecialiteService, "list_specialites"),
        (
            "/api/programmes-pedagogiques",
            ProgrammePedagogiqueService,
            "list_programmes_pedagogiques",
        ),
        ("/api/matieres", MatiereService, "list_matieres"),
        (
            "/api/conditions-admission",
            ConditionAdmissionService,
            "list_conditions_admission",
        ),
    ],
)
def test_listes_sont_branchees_sur_les_services(
    monkeypatch,
    path,
    service,
    method,
):
    monkeypatch.setattr(service, method, lambda **kwargs: [])

    response = client.get(path)

    assert response.status_code == 200
    assert response.json() == []


def test_liste_specialites_est_branchee_sur_le_service(monkeypatch):
    monkeypatch.setattr(
        SpecialiteService,
        "list_specialites",
        lambda **kwargs: [
            {
                "id": 1,
                "programme_id": 1,
                "nom": "Génie logiciel",
                "code": "GL",
                "description": None,
                "actif": True,
                "created_at": None,
                "updated_at": None,
            }
        ],
    )

    response = client.get("/api/specialites?programme_id=1")

    assert response.status_code == 200
    assert response.json()[0]["code"] == "GL"


def test_creation_specialite_conserve_les_erreurs_metier(monkeypatch):
    def duplicate(payload):
        raise SmartCampusException(
            message="Une spécialité avec ce nom existe déjà pour ce programme.",
            status_code=409,
        )

    monkeypatch.setattr(SpecialiteService, "create_specialite", duplicate)

    response = client.post("/api/specialites", json=_specialite_payload())

    assert response.status_code == 409
    assert response.json()["status_code"] == 409


def test_creation_specialite_valide_le_corps_de_requete():
    response = client.post(
        "/api/specialites",
        json={"programme_id": 1, "code": "GL"},
    )

    assert response.status_code == 422


def test_detail_specialite_renvoie_404(monkeypatch):
    def missing(entity_id):
        raise SmartCampusException(
            message=f"Spécialité ID {entity_id} introuvable.",
            status_code=404,
        )

    monkeypatch.setattr(SpecialiteService, "get_or_404", missing)

    response = client.get("/api/specialites/999")

    assert response.status_code == 404


def test_service_specialite_refuse_un_doublon(monkeypatch):
    monkeypatch.setattr(
        FormationService,
        "get_formation_by_id",
        lambda programme_id: {"id": programme_id},
    )
    monkeypatch.setattr(
        SpecialiteRepository,
        "exists",
        lambda conditions, exclude_id=None: True,
    )

    with pytest.raises(SmartCampusException) as exc:
        SpecialiteService.create_specialite(_specialite_payload())

    assert exc.value.status_code == 409


def test_update_condition_admission_bascule_le_parent(monkeypatch):
    existing = {
        "id": 1,
        "programme_id": 1,
        "programme_pedagogique_id": None,
        "type_condition": "Moyenne minimale",
        "description": "Avoir au moins 12/20",
        "valeur": "12",
        "obligatoire": True,
        "actif": True,
    }
    captured = {}

    monkeypatch.setattr(
        ConditionAdmissionService,
        "get_or_404",
        lambda condition_id: existing,
    )
    monkeypatch.setattr(
        FormationService,
        "get_formation_by_id",
        lambda programme_id: {"id": programme_id},
    )

    def fake_update(condition_id, values):
        captured.update(values)
        return {**existing, **values}

    monkeypatch.setattr(
        ConditionAdmissionRepository,
        "update_row",
        fake_update,
    )

    result = ConditionAdmissionService.update_condition_admission(
        1,
        programme_id=2,
    )

    assert captured["programme_id"] == 2
    assert captured["programme_pedagogique_id"] is None
    assert result["programme_id"] == 2


def test_update_condition_admission_refuse_deux_parents(monkeypatch):
    existing = {
        "id": 1,
        "programme_id": 1,
        "programme_pedagogique_id": None,
        "type_condition": "Moyenne minimale",
        "description": "Avoir au moins 12/20",
        "valeur": "12",
        "obligatoire": True,
        "actif": True,
    }
    monkeypatch.setattr(
        ConditionAdmissionService,
        "get_or_404",
        lambda condition_id: existing,
    )

    with pytest.raises(SmartCampusException) as exc:
        ConditionAdmissionService.update_condition_admission(
            1,
            programme_id=2,
            programme_pedagogique_id=3,
        )

    assert exc.value.status_code == 400


def test_programme_pedagogique_refuse_une_specialite_d_un_autre_programme(
    monkeypatch,
):
    monkeypatch.setattr(
        FormationService,
        "get_formation_by_id",
        lambda programme_id: {"id": programme_id},
    )
    monkeypatch.setattr(
        SpecialiteService,
        "get_specialite_by_id",
        lambda specialite_id: {"id": specialite_id, "programme_id": 99},
    )

    with pytest.raises(SmartCampusException) as exc:
        ProgrammePedagogiqueService.create_programme_pedagogique(
            {
                "programme_id": 1,
                "specialite_id": 2,
                "nom": "Programme test",
                "annee_academique": "2025-2026",
                "niveau_etude": "Licence",
                "description": None,
                "actif": True,
            }
        )

    assert exc.value.status_code == 400


def test_creation_formation_ne_masque_pas_une_erreur_de_connexion(monkeypatch):
    from app.services import formation_service as formation_module

    monkeypatch.setattr(
        FormationService,
        "_check_duplicate",
        lambda nom, etablissement: False,
    )

    class FailingEngine:
        def connect(self):
            raise Exception("connexion impossible")

    monkeypatch.setattr(formation_module, "engine", FailingEngine())

    with pytest.raises(SmartCampusException) as exc:
        FormationService.create_formation(
            {
                "nom": "Formation test",
                "etablissement": "IIT",
                "niveau": "Licence",
                "description": None,
            }
        )

    assert exc.value.status_code == 500


def test_repository_genere_is_null_pour_specialite_absente():
    class DemoRepository(CatalogueRepository):
        columns = ("id", "programme_id", "specialite_id", "nom")

    where_clause, params = DemoRepository._build_where(
        {"specialite_id": None}
    )

    assert "specialite_id IS NULL" in where_clause
    assert params == {}
