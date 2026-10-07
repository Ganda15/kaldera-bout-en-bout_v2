"""Coordination : délègue chaque contrôle, range chaque résultat, applique le § 10, conclut.

Squelette de l'étape 1.2 : le chemin nominal, en séquence avec court-circuit.
À venir à l'étape 1.6 : compléments de pièces, bornes, règle 4 complète, filet de sécurité.
"""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from .agents.antifraude import evaluer_risque
from .agents.eligibilite import verifier_eligibilite
from .agents.estimation import estimer
from .agents.pieces import verifier_pieces
from .etat import EtatDemande
from .regles import SEUIL_DELEGATION


def _deleguer(etat: EtatDemande, agent: str, fonction: Callable[..., Any], **entrees: Any) -> Any:
    """Appelle un agent avec ses seules entrées, puis range son résultat dans sa section."""
    debut = perf_counter()
    resultat = fonction(**entrees)
    etat.ranger(agent, resultat, fonction.__name__, (perf_counter() - debut) * 1000)
    return resultat


def _conclure(etat: EtatDemande, motif: str, *, decision: str | None = None,
              montant: float | None = None, file: str | None = None) -> dict[str, Any]:
    """Écrit la section issue (dernière étape) et construit la fiche de décision (§ 11)."""
    issue = "decision" if decision else "escalade"
    etat.ranger("coordination", {"issue": issue, "motif": motif}, "conclure", 0.0)
    return {
        "reference": etat.demande["reference"],
        "issue": issue,
        "decision": decision,
        "montant_rembourse": montant,
        "motif": motif,
        "file": file,
        "avis_fraude": None,
        "mode_degrade": False,
        "trace": etat.trace,
        "arret": None,
    }


def traiter(demande: dict[str, Any]) -> dict[str, Any]:
    etat = EtatDemande(demande)
    contrat, sinistre = demande["contrat"], demande["sinistre"]

    eligibilite = _deleguer(etat, "eligibilite", verifier_eligibilite, contrat=contrat, sinistre=sinistre)
    if not eligibilite.eligible:  # règle 1, court-circuit : les pièces ne sont pas contrôlées
        motif = "Non éligible : " + ", ".join(eligibilite.conditions_non_remplies)
        return _conclure(etat, motif, decision="refusee", montant=0.0)

    pieces = _deleguer(etat, "pieces", verifier_pieces,
                       type_sinistre=sinistre["type"], pieces=demande["pieces"])
    if not pieces.complet:  # règle 2
        return _conclure(etat, "Pièces manquantes : " + ", ".join(pieces.manquantes),
                         file="gestionnaire")

    estimation = _deleguer(etat, "estimation", estimer, montant_declare=sinistre["montant_declare"],
                           formule=contrat["formule"], factures_lisibles=pieces.factures_lisibles)
    if estimation.montant_estime == 0:  # règle 3
        return _conclure(etat, "Dommage inférieur ou égal à la franchise", decision="refusee",
                         montant=0.0)

    _deleguer(etat, "antifraude", evaluer_risque, reference=demande["reference"],
              type_sinistre=sinistre["type"], date_survenance=sinistre["date_survenance"],
              montant_declare=sinistre["montant_declare"],
              date_souscription=contrat["date_souscription"],
              sinistres_12_mois=demande["historique"]["sinistres_12_mois"],
              code_postal=demande["assure"]["code_postal"],
              montant_justifie=estimation.montant_justifie)
    # Règle 4 (avis modéré, élevé, indisponible) : étape 1.6.

    if estimation.montant_estime > SEUIL_DELEGATION:  # règle 5
        return _conclure(etat, "Seuil de délégation dépassé", file="gestionnaire")
    return _conclure(etat, "Demande acceptée", decision="acceptee",  # règle 6
                     montant=estimation.montant_estime)
