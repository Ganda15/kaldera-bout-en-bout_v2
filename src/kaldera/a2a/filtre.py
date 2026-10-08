"""Filtre des données sortantes vers le partenaire anti-fraude (contrat § 2, exigence N3).

Le message est un objet neuf, construit champ par champ à partir d'une liste blanche : on ne part jamais de la
demande pour en retirer des champs. Il est ensuite validé contre un schéma strict (sept champs, types, valeurs
permises, aucun champ en plus). En cas d'échec, `RequeteNonConforme` est levée et rien ne part : c'est un défaut de
notre côté, à signaler.
"""

from __future__ import annotations

import math
import re
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

CODE_POSTAL = re.compile(r"\d{5}")


class RequeteNonConforme(Exception):
    """Les données ne respectent pas le contrat : le message n'est pas envoyé."""


class DonneesFraude(BaseModel):
    """La partie `data` du message, telle que le contrat § 2 la définit."""

    model_config = ConfigDict(extra="forbid", strict=True)
    reference_dossier: Annotated[str, Field(pattern=r"^KAL-\d{2}-\d{4}$")]
    type_sinistre: Literal["degat_des_eaux", "incendie", "bris_de_glace", "vol"]
    montant_declare: Annotated[float, Field(gt=0)]
    date_survenance: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    anciennete_contrat_jours: Annotated[int, Field(ge=0)]
    sinistres_12_mois: Annotated[int, Field(ge=0)]
    departement: Annotated[str, Field(pattern=r"^(?:\d{2}|2[AB]|9[78]\d)$")]

    @field_validator("montant_declare")
    @classmethod
    def _fini(cls, montant: float) -> float:
        if not math.isfinite(montant):
            raise ValueError("montant non fini")
        return montant

    @field_validator("date_survenance")
    @classmethod
    def _date_reelle(cls, valeur: str) -> str:
        date.fromisoformat(valeur)  # refuse 2026-02-30
        return valeur


def departement(code_postal: str) -> str:
    """Le département sans le code postal complet : 2 chiffres, 2A/2B pour la Corse, 3 chiffres outre-mer."""
    if not isinstance(code_postal, str) or not CODE_POSTAL.fullmatch(code_postal):
        raise RequeteNonConforme("code postal invalide")
    if code_postal.startswith("20"):
        return "2A" if code_postal[2] in "01" else "2B"
    if code_postal.startswith(("97", "98")):
        return code_postal[:3]
    return code_postal[:2]


def construire_donnees(*, reference: str, type_sinistre: str, date_survenance: str, montant_declare: float,
                       anciennete_contrat_jours: int, sinistres_12_mois: int, code_postal: str) -> dict[str, Any]:
    """Les sept champs du contrat, et eux seuls ; lève `RequeteNonConforme` si l'un est invalide."""
    try:
        donnees = DonneesFraude(
            reference_dossier=reference,
            type_sinistre=type_sinistre,
            montant_declare=montant_declare,
            date_survenance=date_survenance,
            anciennete_contrat_jours=anciennete_contrat_jours,
            sinistres_12_mois=sinistres_12_mois,
            departement=departement(code_postal),
        )
    except ValidationError as erreur:
        champs = sorted({str(e["loc"][0]) for e in erreur.errors() if e["loc"]})
        raise RequeteNonConforme(f"champs non conformes : {', '.join(champs)}") from None
    return donnees.model_dump()
