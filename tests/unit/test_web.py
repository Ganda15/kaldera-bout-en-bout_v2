"""Poste du gestionnaire (prototype) : ce que le serveur garantit, quel que soit le navigateur."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from kaldera.web.app import creer_app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(creer_app(partenaire_url=None))  # bouchon : aucun réseau


def lire(client: TestClient, dossier: str = "KAL-26-0101") -> dict[str, Any]:
    reponse = client.post("/api/lire", json={"dossier": dossier, "mode": "reference"})
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


def confirmer(lu: dict[str, Any], **changements: Any) -> dict[str, Any]:
    corps = {"session": lu["session"], "contrat": dict(lu["contrat"]),
             "pieces": [{"lisible": p["lisible"], "montant": p.get("montant")} for p in lu["pieces"]],
             "depots": [{"lisible": p["lisible"], "montant": p.get("montant")} for p in lu["depots"]]}
    corps.update(changements)
    return corps


def test_la_page_et_la_liste_des_34_dossiers(client: TestClient) -> None:
    assert "poste du gestionnaire" in client.get("/").text
    assert len(client.get("/api/dossiers").json()) == 34


def test_un_dossier_hors_de_la_liste_est_refuse(client: TestClient) -> None:
    for nom in ("../src", "KAL-26-9999", "..\\..\\Windows"):
        assert client.post("/api/lire", json={"dossier": nom, "mode": "reference"}).status_code == 404


def test_lire_rend_ce_qui_a_ete_lu_sans_decider(client: TestClient) -> None:
    lu = lire(client)
    assert lu["contrat"]["numero"] == "CTR-778801" and len(lu["pieces"]) == 2
    assert [ligne["appel_modele"] for ligne in lu["lecture"]] == [True, True, False]
    assert "description" not in lu["declaration"]["sinistre"]


def test_confirmer_sans_correction_donne_la_meme_decision_que_le_moteur(client: TestClient) -> None:
    r = client.post("/api/decider", json=confirmer(lire(client))).json()
    assert (r["fiche"]["decision"], r["fiche"]["montant_rembourse"], r["corrections"]) == ("acceptee", 1700.0, [])


def test_une_correction_est_gardee_pour_l_audit_et_change_la_decision(client: TestClient) -> None:
    lu = lire(client)
    pieces = [{"lisible": True, "montant": 1000.0}, {"lisible": True, "montant": None}]
    r = client.post("/api/decider", json=confirmer(lu, pieces=pieces)).json()
    assert r["fiche"]["montant_rembourse"] == 850.0  # 1 000 € moins 150 € de franchise
    (correction,) = r["corrections"]
    assert correction["lu"]["montant"] == 1850.0 and correction["retenu"]["montant"] == 1000.0


@pytest.mark.parametrize("champ, valeur", [("formule", "luxe"), ("statut", "peut-etre"), ("numero", "12"),
                                           ("date_souscription", "hier")])
def test_une_correction_hors_schema_est_refusee(client: TestClient, champ: str, valeur: str) -> None:
    lu = lire(client)
    reponse = client.post("/api/decider", json=confirmer(lu, contrat={**lu["contrat"], champ: valeur}))
    assert reponse.status_code == 422


def test_une_facture_lisible_sans_montant_positif_est_refusee(client: TestClient) -> None:
    lu = lire(client)
    for montant in (None, -5, 0):
        corps = confirmer(lu, pieces=[{"lisible": True, "montant": montant}, {"lisible": True, "montant": None}])
        assert client.post("/api/decider", json=corps).status_code == 422


def test_le_navigateur_ne_peut_pas_ajouter_de_piece(client: TestClient) -> None:
    lu = lire(client)
    corps = confirmer(lu, pieces=[{"lisible": True, "montant": 1850.0}, {"lisible": True}, {"lisible": True}])
    assert client.post("/api/decider", json=corps).status_code == 422


def test_un_numero_de_contrat_corrige_different_du_declare_part_en_escalade(client: TestClient) -> None:
    lu = lire(client)
    r = client.post("/api/decider", json=confirmer(lu, contrat={**lu["contrat"], "numero": "CTR-000001"})).json()
    assert (r["fiche"]["issue"], r["fiche"]["file"]) == ("escalade", "gestionnaire")


def test_une_session_inconnue_est_refusee(client: TestClient) -> None:
    corps = confirmer(lire(client))
    corps["session"] = "inexistante"
    assert client.post("/api/decider", json=corps).status_code == 404


def test_sans_partenaire_configure_l_etat_le_dit(client: TestClient) -> None:
    assert client.get("/api/partenaire").json() == {"adresse": None, "joignable": False}
