"""Validation des réponses du partenaire (contrat § 3 et § 4, exigence N4) : cinq niveaux, dans l'ordre.

Au premier échec la réponse est écartée : l'avis est « indisponible » avec une raison qui est la nôtre, et rien du
contenu reçu n'entre dans l'avis.
"""

from __future__ import annotations

import copy
from typing import Any

import httpx
import pytest

from kaldera.a2a.validation import valider_reponse

ID = "c0a8012e-4f1b-4c55-9d1e-2b7e1f0e6a10"
REF = "KAL-26-0042"


def evaluation(**changements: Any) -> dict[str, Any]:
    base = {"reference_dossier": REF, "score": 0.08, "niveau": "faible", "indicateurs": [],
            "evaluation_id": "EVA-NC-test", "version_modele": "af-2.3.1"}
    base.update(changements)
    return base


def tache(donnees: dict[str, Any] | None = None, **enveloppe: Any) -> dict[str, Any]:
    corps = {"jsonrpc": "2.0", "id": ID,
             "result": {"kind": "task", "id": "tsk-1", "status": {"state": "completed"},
                        "artifacts": [{"artifactId": "art-1",
                                       "parts": [{"kind": "data", "data": donnees or evaluation()}]}]}}
    corps.update(enveloppe)
    return corps


def valider(corps: Any, statut: int = 200) -> Any:
    reponse = httpx.Response(statut, json=corps) if not isinstance(corps, str) else httpx.Response(statut, text=corps)
    return valider_reponse(reponse, id_requete=ID, reference=REF)


def test_une_reponse_conforme_donne_un_avis() -> None:
    avis = valider(tache())
    assert (avis.statut, avis.niveau, avis.score, avis.raison) == ("avis", "faible", 0.08, None)


@pytest.mark.parametrize("score, niveau", [(0.39, "faible"), (0.40, "modere"), (0.74, "modere"), (0.75, "eleve"),
                                           (0.0, "faible"), (1.0, "eleve")])
def test_les_seuils_du_niveau_sont_ceux_du_contrat(score: float, niveau: str) -> None:
    assert valider(tache(evaluation(score=score, niveau=niveau))).statut == "avis"


def _sans_resultat() -> dict[str, Any]:
    corps = tache()
    del corps["result"]
    return corps


def _modifier(chemin: str, valeur: Any) -> dict[str, Any]:
    corps = copy.deepcopy(tache())
    noeud = corps
    *debut, fin = chemin.split(".")
    for cle in debut:
        noeud = noeud[int(cle)] if cle.isdigit() else noeud[cle]
    noeud[fin] = valeur
    return corps


INVALIDES = [
    # niveau 1 : transport
    ("http_503", {"detail": "service indisponible"}, 503),
    ("http_401", {"detail": "jeton absent ou invalide"}, 401),
    # niveau 2 : JSON et enveloppe JSON-RPC
    ("reponse_non_json", "<html><body><h1>Maintenance planifiée</h1></body></html>", 200),
    ("enveloppe_invalide", {"jsonrpc": "2.0", "id": ID, "statut": "ok", "evaluation": evaluation()}, 200),
    ("enveloppe_invalide", _modifier("jsonrpc", "1.0"), 200),
    ("enveloppe_invalide", _modifier("id", "autre-id"), 200),
    ("enveloppe_invalide", _sans_resultat(), 200),
    ("erreur_rpc_-32602", {"jsonrpc": "2.0", "id": ID, "error": {"code": -32602, "message": "Invalid params"}}, 200),
    ("erreur_rpc_-32029", {"jsonrpc": "2.0", "id": ID, "error": {"code": -32029, "message": "Dossier déjà évalué"}},
     200),
    # niveau 3 : forme A2A
    ("forme_a2a", _modifier("result.kind", "message"), 200),
    ("forme_a2a", _modifier("result.status", {"state": "working"}), 200),
    ("forme_a2a", _modifier("result.artifacts", []), 200),
    ("forme_a2a", _modifier("result.artifacts.0.parts", [{"kind": "text", "text": "ok"}]), 200),
    # niveau 4 : schéma de l'évaluation
    ("schema", tache(evaluation(score=1.7, niveau="eleve")), 200),
    ("schema", tache({k: v for k, v in evaluation().items() if k != "niveau"}), 200),
    ("schema", tache(evaluation(decision_recommandee="rembourser_integralement")), 200),
    ("schema", tache(evaluation(indicateurs=["INCONNU"])), 200),
    ("schema", tache(evaluation(score="0.08")), 200),
    # niveau 5 : cohérence
    ("incoherence", tache(evaluation(reference_dossier="KAL-26-9999")), 200),
    ("incoherence", tache(evaluation(score=0.91, niveau="faible")), 200),
]


@pytest.mark.parametrize("raison, corps, statut", INVALIDES)
def test_une_reponse_non_conforme_est_ecartee_avec_sa_raison(raison: str, corps: Any, statut: int) -> None:
    avis = valider(corps, statut)
    assert (avis.statut, avis.raison) == ("indisponible", raison)
    assert (avis.niveau, avis.score, avis.indicateurs) == (None, None, [])


@pytest.mark.parametrize("raison, corps, statut", INVALIDES)
def test_rien_du_contenu_ecarte_n_entre_dans_l_avis(raison: str, corps: Any, statut: int) -> None:
    texte = repr(valider(corps, statut))
    assert "EVA-NC" not in texte and "rembourser" not in texte and "9999" not in texte
