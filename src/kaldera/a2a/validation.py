"""Validation d'une réponse du partenaire anti-fraude (contrat § 3 et § 4, exigence N4).

Cinq niveaux, dans l'ordre : transport, enveloppe JSON-RPC, forme A2A, schéma de l'évaluation, cohérence. Au premier
échec, la réponse est écartée : l'avis est « indisponible » avec une raison qui est la nôtre (un code court), et rien
du contenu reçu n'est recopié. Une réponse qui ne respecte pas le contrat « n'engage pas le partenaire » (§ 3).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..agents.antifraude import AvisFraude


class EvaluationPartenaire(BaseModel):
    """La partie `data` de l'artefact, telle que le contrat § 3 la définit : aucun champ en plus."""

    model_config = ConfigDict(extra="forbid", strict=True)
    reference_dossier: str
    score: Annotated[float, Field(ge=0, le=1)]
    niveau: Literal["faible", "modere", "eleve"]
    indicateurs: list[Literal["MONTANT_ELEVE", "SINISTRE_PRECOCE", "FREQUENCE_ELEVEE", "TYPE_SENSIBLE"]]
    evaluation_id: str
    version_modele: str


def niveau_attendu(score: float) -> str:
    return "faible" if score < 0.40 else "modere" if score < 0.75 else "eleve"


def _ecartee(raison: str) -> AvisFraude:
    return AvisFraude(statut="indisponible", raison=raison, appel_externe=True)


def _donnees_a2a(resultat: Any) -> Any:
    """La seule partie `data` d'une tâche terminée, ou None si la forme A2A n'est pas respectée."""
    if not isinstance(resultat, dict) or resultat.get("kind") != "task":
        return None
    if not isinstance(resultat.get("status"), dict) or resultat["status"].get("state") != "completed":
        return None
    artefacts = resultat.get("artifacts")
    if not isinstance(artefacts, list) or len(artefacts) != 1 or not isinstance(artefacts[0], dict):
        return None
    parties = artefacts[0].get("parts")
    if not isinstance(parties, list) or len(parties) != 1 or not isinstance(parties[0], dict):
        return None
    if parties[0].get("kind") != "data":
        return None
    return parties[0].get("data")


def valider_reponse(reponse: httpx.Response, *, id_requete: str, reference: str) -> AvisFraude:
    # 1 · transport
    if reponse.status_code != 200:
        return _ecartee(f"http_{reponse.status_code}")
    # 2 · JSON, puis enveloppe JSON-RPC (un HTTP 200 qui porte une erreur reste une erreur)
    try:
        corps = reponse.json()
    except ValueError:
        return _ecartee("reponse_non_json")
    if not isinstance(corps, dict) or corps.get("jsonrpc") != "2.0" or corps.get("id") != id_requete:
        return _ecartee("enveloppe_invalide")
    if "error" in corps:
        erreur = corps["error"]
        code = erreur.get("code") if isinstance(erreur, dict) else None
        return _ecartee(f"erreur_rpc_{code}" if isinstance(code, int) else "enveloppe_invalide")
    if "result" not in corps:
        return _ecartee("enveloppe_invalide")
    # 3 · forme A2A : une tâche terminée, un artefact, une partie data
    donnees = _donnees_a2a(corps["result"])
    if donnees is None:
        return _ecartee("forme_a2a")
    # 4 · schéma de l'évaluation
    try:
        evaluation = EvaluationPartenaire.model_validate(donnees)
    except ValidationError:
        return _ecartee("schema")
    # 5 · cohérence : même dossier, niveau conforme au score
    if evaluation.reference_dossier != reference or evaluation.niveau != niveau_attendu(evaluation.score):
        return _ecartee("incoherence")
    return AvisFraude(statut="avis", niveau=evaluation.niveau, score=evaluation.score, appel_externe=True,
                      evaluation_id=evaluation.evaluation_id)
