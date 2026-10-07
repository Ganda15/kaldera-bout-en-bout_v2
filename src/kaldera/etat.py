"""Mémoire partagée d'une demande. Seule la Coordination la lit et l'écrit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .agents.antifraude import AvisFraude
from .agents.eligibilite import ResultatEligibilite
from .agents.estimation import ResultatEstimation
from .agents.pieces import ResultatPieces

# Chaque agent n'a droit qu'à une section, et chaque section n'a qu'un agent (interface.md).
SECTION_DE = {
    "eligibilite": "eligibilite",
    "pieces": "pieces",
    "estimation": "estimation",
    "antifraude": "avis_fraude",
    "coordination": "issue",
}

# Le type de résultat attendu de chaque agent : un résultat d'un autre type est refusé.
TYPE_DE = {
    "eligibilite": ResultatEligibilite,
    "pieces": ResultatPieces,
    "estimation": ResultatEstimation,
    "antifraude": AvisFraude,
    "coordination": dict,
}


class ErreurDeDroits(Exception):
    """Un rangement interdit : agent inconnu, mauvais type ou section déjà écrite."""


@dataclass
class EtatDemande:
    demande: dict[str, Any]  # la demande reçue, jamais modifiée
    sections: dict[str, Any] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)

    def ranger(self, agent: str, resultat: Any, action: str, duree_ms: float,
               statut: str = "ok") -> None:
        """Range le résultat d'un agent dans SA section et ajoute une ligne de trace."""
        section = SECTION_DE.get(agent)
        if section is None:
            raise ErreurDeDroits(f"agent inconnu : {agent}")
        if not isinstance(resultat, TYPE_DE[agent]):
            raise ErreurDeDroits(f"{agent} doit rendre un {TYPE_DE[agent].__name__}")
        if section in self.sections and section != "pieces":
            raise ErreurDeDroits(f"la section {section} est déjà écrite")
        self.sections[section] = resultat
        self.trace.append({"agent": agent, "ecrit": [section], "action": action,
                           "duree_ms": round(duree_ms, 2), "statut": statut})

    def noter_echec(self, agent: str, action: str, duree_ms: float) -> None:
        """Un agent a échoué sans rendre de résultat : une ligne de trace, aucune section écrite."""
        self.trace.append({"agent": agent, "ecrit": [], "action": action,
                           "duree_ms": round(duree_ms, 2), "statut": "echec"})
