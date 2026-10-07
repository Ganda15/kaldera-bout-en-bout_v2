"""Bornes d'exécution d'une demande (docs/interface.md, § Bornes d'exécution).

Les valeurs imposées par la spec ou le contrat ne sont pas provisoires (durée, appel unique,
délai du partenaire). Les autres sont des valeurs de départ, éprouvées par le rejeu des
scénarios ; tout changement est consigné dans conception/journal-ajustements.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Bornes:
    etapes_max: int = 8  # 5 étapes nominales + 2 compléments + 1 de marge ; la dernière est l'issue
    duree_max_s: float = 10  # engagement de service, specs_metier.md § 12
    complements_max: int = 2  # NOM-07 et PAN-01 en demandent un ; aucun scénario n'en justifie plus
    appels_partenaire_max: int = 1  # contrat § 6 : un seul appel par dossier, aucune relance
    delai_partenaire_s: float = 3  # contrat § 5 : abandon au plus tard 3 s après l'envoi
    delai_controle_interne_s: float = 1  # contrôles en code, sans réseau
    reserve_fiche_s: float = 0.5  # temps gardé pour produire la fiche ; provisoire, à mesurer (1.7)


BORNES = Bornes()


def bornes() -> dict[str, Any]:
    """Retourne les bornes en vigueur, sous forme de copie : la modifier ne change rien."""
    return asdict(BORNES)
