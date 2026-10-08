"""Bornes d'exécution : ce que `kaldera.bornes()` expose (docs/interface.md, § Bornes)."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

import kaldera
from kaldera.bornes import BORNES, delai_min_depuis_mesure, reserve_depuis_mesure


def test_bornes_expose_les_deux_cles_exigees_par_interface() -> None:
    bornes = kaldera.bornes()
    assert isinstance(bornes["etapes_max"], int) and bornes["etapes_max"] > 0
    assert isinstance(bornes["duree_max_s"], (int, float))
    assert 0 < bornes["duree_max_s"] <= 10  # engagement de service, specs_metier.md § 12


def test_bornes_valeurs_de_depart_de_la_conception() -> None:
    bornes = kaldera.bornes()
    assert bornes["etapes_max"] == 8  # 5 étapes nominales + 2 compléments + 1 de marge
    assert bornes["duree_max_s"] == 10
    assert bornes["complements_max"] == 2
    assert bornes["appels_partenaire_max"] == 1  # contrat § 6
    assert bornes["delai_partenaire_s"] == 3  # contrat § 5
    assert bornes["delai_controle_interne_s"] == 1


def test_la_reserve_de_la_fiche_tient_dans_la_duree() -> None:
    bornes = kaldera.bornes()
    assert 0 < bornes["reserve_fiche_s"] < bornes["duree_max_s"]
    assert bornes["delai_partenaire_s"] < bornes["duree_max_s"] - bornes["reserve_fiche_s"]


def test_modifier_le_resultat_ne_change_pas_les_bornes() -> None:
    copie = kaldera.bornes()
    copie["etapes_max"] = 999
    assert kaldera.bornes()["etapes_max"] == 8


# ---------------------------------------------------------------- deux bornes tirées de la mesure, pas au doigt mouillé

MESURES = Path(__file__).resolve().parents[2] / "evaluation" / "bornes" / "mesures.json"


@pytest.mark.parametrize("depassement_s, reserve_s", [(0.0, 0.1), (0.004, 0.1), (0.0101, 0.2), (0.012, 0.2),
                                                       (0.05, 0.5)])
def test_regle_de_la_reserve_dix_fois_le_pire_depassement(depassement_s: float, reserve_s: float) -> None:
    assert reserve_depuis_mesure(depassement_s) == reserve_s


@pytest.mark.parametrize("appel_s, delai_s", [(0.0, 0.05), (0.06, 0.1), (0.1, 0.1), (0.101, 0.15)])
def test_regle_du_delai_minimal_le_plus_long_appel_reussi(appel_s: float, delai_s: float) -> None:
    assert delai_min_depuis_mesure(appel_s) == delai_s


def test_les_deux_bornes_viennent_de_la_mesure_enregistree() -> None:
    mesures = json.loads(MESURES.read_text(encoding="utf-8"))
    assert mesures["essais_depassement"] >= 20 and mesures["essais_appel"] >= 20
    assert BORNES.reserve_fiche_s == reserve_depuis_mesure(mesures["depassement_max_s"])
    assert BORNES.delai_partenaire_min_s == delai_min_depuis_mesure(mesures["appel_reussi_max_s"])


def test_plus_aucune_de_ces_deux_bornes_n_est_marquee_provisoire() -> None:
    # importlib : `kaldera.bornes` désigne aussi la fonction bornes() exportée par le paquet
    lignes = Path(importlib.import_module("kaldera.bornes").__file__).read_text(encoding="utf-8").splitlines()
    for champ in ("reserve_fiche_s", "delai_partenaire_min_s"):
        (ligne,) = [x for x in lignes if x.strip().startswith(f"{champ}:")]
        assert "provisoire" not in ligne, ligne
