"""Agent Pièces : dit si les pièces exigées sont présentes, lisibles et du type attendu (§ 5).

Frontière : ne conclut pas, n'escalade pas, ne chiffre pas, ne juge pas la fraude.
La demande de complément arrive à l'étape 1.4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..regles import PIECES_EXIGEES


@dataclass(frozen=True)
class ResultatPieces:
    complet: bool
    manquantes: list[str] = field(default_factory=list)  # types absents ou illisibles
    factures_lisibles: list[float] = field(default_factory=list)  # montants, pour l'Estimation


def verifier_pieces(type_sinistre: str, pieces: list[dict[str, Any]]) -> ResultatPieces:
    """Reçoit le type de sinistre et les pièces, rien d'autre."""
    lisibles = {p["type"] for p in pieces if p.get("lisible")}
    manquantes = [t for t in PIECES_EXIGEES[type_sinistre] if t not in lisibles]
    factures = [p["montant"] for p in pieces if p["type"] == "facture" and p.get("lisible")]
    return ResultatPieces(complet=not manquantes, manquantes=manquantes, factures_lisibles=factures)
