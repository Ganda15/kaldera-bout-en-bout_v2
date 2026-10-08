"""Client A2A du partenaire anti-fraude (contrat § 1, § 5, § 6) : filtre, un seul appel, délai réel, aucune relance.

Le réseau est remplacé par un transport simulé d'httpx (aucune connexion) : chaque test compte les requêtes envoyées.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx
import pytest

from kaldera.a2a.client import partenaire_a2a

JETON = "jeton-secret-de-test"
DONNEES = {"reference": "KAL-26-0042", "type_sinistre": "degat_des_eaux", "date_survenance": "2026-08-14",
           "montant_declare": 1850.0, "anciennete_contrat_jours": 942, "sinistres_12_mois": 0,
           "code_postal": "69003"}


@pytest.fixture(autouse=True)
def jeton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PARTENAIRE_JETON", JETON)


class Partenaire:
    """Transport simulé : note chaque requête et rend une tâche conforme (ou ce qu'on lui demande)."""

    def __init__(self, attente_s: float = 0.0, erreur: Exception | None = None) -> None:
        self.requetes: list[httpx.Request] = []
        self.attente_s, self.erreur = attente_s, erreur

    def __call__(self, requete: httpx.Request) -> httpx.Response:
        self.requetes.append(requete)
        if self.erreur:
            raise self.erreur
        time.sleep(self.attente_s)
        corps = json.loads(requete.content)
        data = corps["params"]["message"]["parts"][0]["data"]
        evaluation = {"reference_dossier": data["reference_dossier"], "score": 0.08, "niveau": "faible",
                      "indicateurs": [], "evaluation_id": "EVA-1", "version_modele": "af-2.3.1"}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": corps["id"], "result": {
            "kind": "task", "id": "tsk-1", "status": {"state": "completed"},
            "artifacts": [{"artifactId": "art-1", "parts": [{"kind": "data", "data": evaluation}]}]}})


def client(partenaire: Partenaire) -> Any:
    return partenaire_a2a("http://partenaire.test", transport=httpx.MockTransport(partenaire))


def test_une_demande_valide_part_filtree_en_un_seul_appel_message_send() -> None:
    partenaire = Partenaire()
    avis = client(partenaire)(**DONNEES, delai_s=3.0)
    assert (avis.statut, avis.niveau, avis.score, avis.appel_externe) == ("avis", "faible", 0.08, True)
    (requete,) = partenaire.requetes
    assert (requete.method, str(requete.url)) == ("POST", "http://partenaire.test/a2a")
    assert requete.headers["authorization"] == f"Bearer {JETON}"
    corps = json.loads(requete.content)
    assert (corps["jsonrpc"], corps["method"]) == ("2.0", "message/send")
    (partie,) = corps["params"]["message"]["parts"]
    assert partie["kind"] == "data" and len(partie["data"]) == 7
    assert "69003" not in requete.content.decode("utf-8")


def test_une_requete_refusee_par_le_filtre_ne_fait_aucun_appel_reseau() -> None:
    partenaire = Partenaire()
    avis = client(partenaire)(**{**DONNEES, "code_postal": "6900"}, delai_s=3.0)
    assert partenaire.requetes == []
    assert (avis.statut, avis.raison, avis.appel_externe) == ("indisponible", "requete_non_conforme", False)


def test_le_delai_donne_est_transmis_a_httpx() -> None:
    vus: list[dict[str, Any]] = []
    partenaire = Partenaire()

    def espion(requete: httpx.Request) -> httpx.Response:
        vus.append(requete.extensions["timeout"])
        return partenaire(requete)

    partenaire_a2a("http://partenaire.test", transport=httpx.MockTransport(espion))(**DONNEES, delai_s=1.25)
    assert vus and all(v == 1.25 for v in vus[0].values())


def test_un_delai_depasse_donne_indisponible_sans_relance() -> None:
    partenaire = Partenaire(erreur=httpx.ReadTimeout("trop lent"))
    avis = client(partenaire)(**DONNEES, delai_s=0.5)
    assert len(partenaire.requetes) == 1
    assert (avis.statut, avis.raison, avis.appel_externe) == ("indisponible", "delai_depasse", True)


def test_une_reponse_arrivee_apres_le_delai_n_est_jamais_lue() -> None:
    partenaire = Partenaire(attente_s=0.15)  # le transport simulé n'applique pas le délai : le client le fait
    avis = client(partenaire)(**DONNEES, delai_s=0.05)
    assert (avis.statut, avis.raison, avis.score) == ("indisponible", "delai_depasse", None)


def test_une_panne_reseau_donne_indisponible_sans_relance() -> None:
    partenaire = Partenaire(erreur=httpx.ConnectError("refusé"))
    avis = client(partenaire)(**DONNEES, delai_s=3.0)
    assert len(partenaire.requetes) == 1
    assert (avis.statut, avis.raison) == ("indisponible", "erreur_transport")


def test_sans_adresse_du_partenaire_aucun_appel() -> None:
    avis = partenaire_a2a(None)(**DONNEES, delai_s=3.0)
    assert (avis.statut, avis.raison, avis.appel_externe) == ("indisponible", "partenaire_non_configure", False)


def test_ni_le_jeton_ni_une_donnee_personnelle_n_apparait_dans_les_journaux(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    client(Partenaire())(**DONNEES, delai_s=3.0)
    client(Partenaire(erreur=httpx.ConnectError("refusé")))(**DONNEES, delai_s=3.0)
    assert caplog.records  # httpx journalise bien quelque chose : le test regarde un vrai contenu
    assert JETON not in caplog.text and "69003" not in caplog.text
