"""Agent Pièces : dit si les pièces exigées sont présentes, lisibles et du type attendu (§ 5),
et adresse à l'assuré la demande de complément quand la Coordination la lui confie.

Frontière : ne conclut pas, n'escalade pas, ne chiffre pas, ne juge pas la fraude, ne décide
jamais seul d'une demande de complément.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..espace_assure import demander_piece
from ..regles import PIECES_EXIGEES


@dataclass(frozen=True)
class ResultatPieces:
    complet: bool
    manquantes: list[str] = field(default_factory=list)  # types absents ou illisibles
    factures_lisibles: list[float] = field(default_factory=list)  # montants, pour l'Estimation
    pieces: list[dict[str, Any]] = field(default_factory=list)  # pièces connues après ce contrôle
    sans_depot: list[str] = field(default_factory=list)  # types demandés jamais déposés (§ 5)


def verifier_pieces(type_sinistre: str, pieces: list[dict[str, Any]]) -> ResultatPieces:
    """Reçoit le type de sinistre et les pièces, rien d'autre."""
    lisibles = {p["type"] for p in pieces if p.get("lisible")}
    manquantes = [t for t in PIECES_EXIGEES[type_sinistre] if t not in lisibles]
    factures = [p["montant"] for p in pieces if p["type"] == "facture" and p.get("lisible")]
    return ResultatPieces(not manquantes, manquantes, factures, list(pieces))


def demander_complement(
    type_sinistre: str, pieces: list[dict[str, Any]], depots: list[dict[str, Any]], tentative: int
) -> ResultatPieces:
    """Sur délégation de la Coordination : demande chaque pièce manquante à l'assuré, ajoute ses
    dépôts aux pièces connues, puis contrôle à nouveau. `tentative` vaut 0 pour la première
    demande. Reçoit les dépôts de l'espace assuré, jamais son identité."""
    avant = verifier_pieces(type_sinistre, pieces)
    connues, sans_depot = list(pieces), []
    for type_piece in avant.manquantes:
        depot = demander_piece({"espace_assure": {"depots": depots}}, type_piece, tentative)
        if depot is None:
            sans_depot.append(type_piece)
        else:
            connues.append(depot)
    apres = verifier_pieces(type_sinistre, connues)
    return ResultatPieces(apres.complet, apres.manquantes, apres.factures_lisibles, connues, sans_depot)
