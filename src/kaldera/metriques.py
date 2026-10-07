"""Métriques par agent, calculées depuis les traces (docs/interface.md, § Métriques).

Une seule source de vérité : chaque métrique est un comptage ou une moyenne des lignes de trace,
jamais un compteur tenu à part.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def calculer_metriques(fiches: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Pour chaque agent nommé dans les traces : appels, échecs, latence moyenne, appels externes."""
    lignes_par_agent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fiche in fiches:
        for ligne in fiche.get("trace", []):
            lignes_par_agent[ligne["agent"]].append(ligne)
    return {
        agent: {
            "appels": len(lignes),
            "echecs": sum(1 for ligne in lignes if ligne.get("statut") == "echec"),
            "latence_ms": round(sum(ligne.get("duree_ms", 0.0) for ligne in lignes) / len(lignes), 2),
            "appels_externes": sum(1 for ligne in lignes if ligne.get("appel_externe")),
        }
        for agent, lignes in lignes_par_agent.items()
    }
