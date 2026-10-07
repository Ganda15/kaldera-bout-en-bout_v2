"""Agent Anti-fraude : calcule les indicateurs F1 à F4 (§ 7) et, si l'un est présent,
obtient l'avis du partenaire en un seul appel. Il n'émet jamais d'avis lui-même.

Il reçoit exactement huit données, jamais l'identité, l'IBAN, la description ni les pièces.
Au chantier 1, le partenaire est un bouchon qui répond toujours « indisponible » ;
le vrai client A2A le remplace au chantier 2.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..regles import (
    ANCIENNETE_SENSIBLE_JOURS,
    ECART_DECLARATION_MAX,
    FREQUENCE_SENSIBLE,
    SEUIL_MONTANT_FRAUDE,
    jours_entre,
)


@dataclass(frozen=True)
class AvisFraude:
    statut: str  # "non_requis", "avis" ou "indisponible"
    indicateurs: list[str] = field(default_factory=list)
    niveau: str | None = None
    score: float | None = None
    raison: str | None = None  # pourquoi l'avis est indisponible


def partenaire_bouchon(**_donnees: Any) -> AvisFraude:
    """Chantier 1 : aucun partenaire branché, donc l'avis est toujours indisponible."""
    return AvisFraude(statut="indisponible", raison="partenaire_non_branche")


def evaluer_risque(
    *,
    reference: str,
    type_sinistre: str,
    date_survenance: str,
    montant_declare: float,
    date_souscription: str,
    sinistres_12_mois: int,
    code_postal: str,
    montant_justifie: float,
    consulter: Callable[..., AvisFraude] = partenaire_bouchon,
) -> AvisFraude:
    indicateurs = []
    if montant_declare >= SEUIL_MONTANT_FRAUDE:
        indicateurs.append("F1")
    if jours_entre(date_souscription, date_survenance) < ANCIENNETE_SENSIBLE_JOURS:
        indicateurs.append("F2")
    if sinistres_12_mois >= FREQUENCE_SENSIBLE:
        indicateurs.append("F3")
    if montant_declare > montant_justifie * (1 + ECART_DECLARATION_MAX):
        indicateurs.append("F4")
    if not indicateurs:
        return AvisFraude(statut="non_requis")
    avis = consulter(
        reference=reference,
        type_sinistre=type_sinistre,
        date_survenance=date_survenance,
        montant_declare=montant_declare,
        anciennete_contrat_jours=jours_entre(date_souscription, date_survenance),
        sinistres_12_mois=sinistres_12_mois,
        code_postal=code_postal,
    )
    return AvisFraude(avis.statut, indicateurs, avis.niveau, avis.score, avis.raison)
