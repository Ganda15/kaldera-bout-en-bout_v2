"""Bornes d'exécution d'une demande (docs/interface.md, § Bornes d'exécution).

Trois origines, jamais au doigt mouillé :
- imposées par la spec ou le contrat : durée, appel unique, délai du partenaire ;
- fondées sur les scénarios et éprouvées par leur rejeu : étapes, compléments ;
- tirées d'une mesure par une règle écrite : réserve de la fiche, délai minimal d'un appel
  (outils/mesurer_bornes.py, résultat dans evaluation/bornes/mesures.json, vérifié par un test).
Tout changement est consigné dans conception/journal-ajustements.md.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any


def reserve_depuis_mesure(depassement_max_s: float) -> float:
    """Règle : dix fois le plus grand dépassement mesuré après l'échéance, arrondi au dixième de seconde supérieur,
    0,1 s au moins. Le facteur dix couvre ce que la mesure ne voit pas (machine chargée, pause du ramasse-miettes)."""
    return round(max(0.1, math.ceil(round(depassement_max_s * 100, 6)) / 10), 1)


def delai_min_depuis_mesure(appel_reussi_max_s: float) -> float:
    """Règle : la durée du plus long appel réussi mesuré, arrondie au vingtième de seconde supérieur, 0,05 s au moins.
    En dessous, un appel n'a pas le temps d'aboutir : on ne gâche pas le seul appel permis (contrat § 6)."""
    return round(max(0.05, math.ceil(round(appel_reussi_max_s * 20, 6)) / 20), 2)


@dataclass(frozen=True)
class Bornes:
    etapes_max: int = 8  # 5 étapes nominales + 2 compléments + 1 de marge ; la dernière est l'issue
    duree_max_s: float = 10  # engagement de service, specs_metier.md § 12
    complements_max: int = 2  # NOM-07 et PAN-01 en demandent un ; aucun scénario n'en justifie plus
    appels_partenaire_max: int = 1  # contrat § 6 : un seul appel par dossier, aucune relance
    delai_partenaire_s: float = 3  # contrat § 5 : abandon au plus tard 3 s après l'envoi
    # en dessous, pas d'appel (un seul permis) : avis indisponible. Mesuré le 08/10 : appel réussi le plus long
    # 0,104 s sur 65 essais ; règle delai_min_depuis_mesure -> 0,15 s (evaluation/bornes/mesures.json)
    delai_partenaire_min_s: float = 0.15
    delai_controle_interne_s: float = 1  # contrôles en code, sans réseau
    # temps gardé après l'échéance pour produire la fiche. Mesuré le 08/10 : dépassement le plus long 0,038 s sur
    # 70 essais ; règle reserve_depuis_mesure -> 0,4 s (evaluation/bornes/mesures.json)
    reserve_fiche_s: float = 0.4


BORNES = Bornes()


def bornes() -> dict[str, Any]:
    """Retourne les bornes en vigueur, sous forme de copie : la modifier ne change rien."""
    return asdict(BORNES)
