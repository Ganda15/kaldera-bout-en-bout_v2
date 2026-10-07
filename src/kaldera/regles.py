"""Référentiel métier : formules, pièces exigées, seuils (docs/specs_metier.md).

Chaque chiffre est vérifié contre la spec par tests/unit/test_regles.py. Un changement de règle
métier se fait ici seulement, avec la version de la spec qui le porte.
"""

from __future__ import annotations

from datetime import date

VERSION_SPEC = "3.2"

FORMULES: dict[str, dict] = {
    "essentiel": {
        "garanties": {"degat_des_eaux", "incendie"},
        "franchise": 300.0,
        "plafond": 3_000.0,
    },
    "confort": {
        "garanties": {"degat_des_eaux", "incendie", "bris_de_glace", "vol"},
        "franchise": 150.0,
        "plafond": 8_000.0,
    },
    "premium": {
        "garanties": {"degat_des_eaux", "incendie", "bris_de_glace", "vol"},
        "franchise": 0.0,
        "plafond": 20_000.0,
    },
}

PIECES_EXIGEES: dict[str, tuple[str, ...]] = {
    "degat_des_eaux": ("facture", "photo"),
    "incendie": ("facture", "photo"),
    "bris_de_glace": ("facture", "photo"),
    "vol": ("facture", "depot_plainte"),
}

CARENCE_JOURS = 30
DELAI_DECLARATION_JOURS = 30
DELAI_DECLARATION_VOL_JOURS = 5

SEUIL_DELEGATION = 10_000.0  # § 8, règle 5 : escalade strictement au-delà
SEUIL_MODE_DEGRADE = 1_500.0  # § 9 : sans avis, la demande continue jusqu'à ce montant inclus

# Indicateurs déclenchant le contrôle anti-fraude
SEUIL_MONTANT_FRAUDE = 5_000.0
ANCIENNETE_SENSIBLE_JOURS = 90
FREQUENCE_SENSIBLE = 3
ECART_DECLARATION_MAX = 0.20


def jours_entre(debut: str, fin: str) -> int:
    return (date.fromisoformat(fin) - date.fromisoformat(debut)).days


def _centimes(montant: float) -> int:
    return round(montant * 100)


def ecart_declaration_depasse(montant_declare: float, montant_justifie: float) -> bool:
    """F4 : déclaré supérieur de PLUS de 20 % au justifié. Calcul en centimes entiers :
    en nombres à virgule, 1 234,50 × 1,2 ne vaut pas exactement 1 481,40."""
    pourcentage = round(ECART_DECLARATION_MAX * 100)
    return _centimes(montant_declare) * 100 > _centimes(montant_justifie) * (100 + pourcentage)


def depasse_seuil_delegation(montant_estime: float) -> bool:
    return _centimes(montant_estime) > _centimes(SEUIL_DELEGATION)


def continue_en_mode_degrade(montant_estime: float) -> bool:
    return _centimes(montant_estime) <= _centimes(SEUIL_MODE_DEGRADE)
