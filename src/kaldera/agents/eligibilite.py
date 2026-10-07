"""Agent Éligibilité : dit si le contrat couvre le sinistre (specs_metier.md § 4, conditions E1 à E5).

Frontière : ne chiffre rien, n'applique pas le plafond, ne juge ni les pièces ni la fraude.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..regles import (
    CARENCE_JOURS,
    DELAI_DECLARATION_JOURS,
    DELAI_DECLARATION_VOL_JOURS,
    FORMULES,
    jours_entre,
)


@dataclass(frozen=True)
class ResultatEligibilite:
    eligible: bool
    conditions_non_remplies: list[str] = field(default_factory=list)


def verifier_eligibilite(contrat: dict[str, Any], sinistre: dict[str, Any]) -> ResultatEligibilite:
    """Reçoit le contrat et le sinistre, rien d'autre (ni identité, ni IBAN, ni pièces)."""
    non_remplies = []
    if contrat["statut"] != "actif":
        non_remplies.append("E1 contrat non actif")
    if not contrat["cotisations_a_jour"]:
        non_remplies.append("E2 cotisations non à jour")
    if jours_entre(contrat["date_souscription"], sinistre["date_survenance"]) < CARENCE_JOURS:
        non_remplies.append("E3 sinistre pendant la carence de 30 jours")
    delai = DELAI_DECLARATION_VOL_JOURS if sinistre["type"] == "vol" else DELAI_DECLARATION_JOURS
    if jours_entre(sinistre["date_survenance"], sinistre["date_declaration"]) > delai:
        non_remplies.append(f"E4 déclaration au-delà de {delai} jours")
    if sinistre["type"] not in FORMULES[contrat["formule"]]["garanties"]:
        non_remplies.append("E5 sinistre non couvert par la formule")
    return ResultatEligibilite(eligible=not non_remplies, conditions_non_remplies=non_remplies)
