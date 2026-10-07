"""Mémoire partagée d'une demande. Seule la Coordination la lit et l'écrit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Chaque agent n'a droit qu'à une section, et chaque section n'a qu'un agent (interface.md).
SECTION_DE = {
    "eligibilite": "eligibilite",
    "pieces": "pieces",
    "estimation": "estimation",
    "antifraude": "avis_fraude",
    "coordination": "issue",
}


class ErreurDeDroits(Exception):
    """Un résultat qu'on essaie de ranger dans une section qui n'est pas celle de son agent."""


@dataclass
class EtatDemande:
    demande: dict[str, Any]  # la demande reçue, jamais modifiée
    sections: dict[str, Any] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)

    def ranger(self, agent: str, resultat: Any, action: str, duree_ms: float) -> None:
        """Range le résultat d'un agent dans SA section et ajoute une ligne de trace."""
        section = SECTION_DE.get(agent)
        if section is None:
            raise ErreurDeDroits(f"agent inconnu : {agent}")
        if section in self.sections and section != "pieces":
            raise ErreurDeDroits(f"la section {section} est déjà écrite")
        self.sections[section] = resultat
        self.trace.append(
            {"agent": agent, "ecrit": [section], "action": action, "duree_ms": round(duree_ms, 2)}
        )
