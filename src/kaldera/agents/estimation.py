"""Agent Estimation : calcule le montant remboursable (§ 6), franchise et plafond compris.

Le plafond est appliqué ici, jamais par l'Éligibilité : c'est le point ambigu tranché
(NOM-05 : 4 200 € déclarés, moins 300 € de franchise, plafonnés à 3 000 €).
Frontière : ne juge pas la fraude, ne revient pas sur l'éligibilité.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..regles import FORMULES


@dataclass(frozen=True)
class ResultatEstimation:
    montant_justifie: float  # somme des factures lisibles
    montant_retenu: float  # le plus petit du déclaré et du justifié
    montant_estime: float  # retenu moins la franchise, jamais négatif, jamais au-delà du plafond


def estimer(montant_declare: float, formule: str, factures_lisibles: list[float]) -> ResultatEstimation:
    """Reçoit le montant déclaré, la formule et les factures lisibles, rien d'autre."""
    justifie = round(sum(factures_lisibles), 2)
    retenu = min(montant_declare, justifie)
    estime = max(0.0, retenu - FORMULES[formule]["franchise"])
    estime = min(estime, FORMULES[formule]["plafond"])
    return ResultatEstimation(justifie, round(retenu, 2), round(estime, 2))
