"""Kaldera : traitement des demandes de remboursement d'assurance par une équipe d'agents."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .a2a import client as client_a2a
from .agents.antifraude import AvisFraude, partenaire_bouchon
from .bornes import bornes
from .coordination import RegistreAppels, traiter
from .metriques import calculer_metriques

__all__ = ["bornes", "traiter_demande", "traiter_lot"]

FILS_MAX = 32  # demandes traitées en même temps, au plus


def _consulter(partenaire_url: str | None, consulter: Callable[..., AvisFraude] | None) -> Callable[..., AvisFraude]:
    """Le partenaire à consulter : celui fourni (tests), sinon le client A2A à cette adresse, sinon le bouchon."""
    if consulter is not None:
        return consulter
    return client_a2a.partenaire_a2a(partenaire_url) if partenaire_url else partenaire_bouchon


def traiter_demande(
    demande: dict[str, Any], *, partenaire_url: str | None = None,
    consulter: Callable[..., AvisFraude] | None = None,
) -> dict[str, Any]:
    """Traite une demande et retourne sa fiche de décision."""
    return traiter(demande, consulter=_consulter(partenaire_url, consulter))


def traiter_lot(
    demandes: list[dict[str, Any]], *, partenaire_url: str | None = None,
    consulter: Callable[..., AvisFraude] | None = None,
) -> dict[str, Any]:
    """Traite un lot en concurrence : une demande lente ne retarde jamais les autres (§ 12).

    Chaque demande a son propre état et tient ses propres bornes de l'intérieur ; le registre des
    appels est partagé par le lot. Les fiches sont rendues dans l'ordre des demandes.
    """
    if not demandes:
        return {"fiches": [], "metriques": {}}
    registre, consulter = RegistreAppels(), _consulter(partenaire_url, consulter)
    with ThreadPoolExecutor(max_workers=min(len(demandes), FILS_MAX)) as executeur:
        fiches = list(executeur.map(
            lambda demande: traiter(demande, consulter=consulter, registre=registre), demandes))
    return {"fiches": fiches, "metriques": calculer_metriques(fiches)}
