"""Bornes d'exécution : ce que `kaldera.bornes()` expose (docs/interface.md, § Bornes)."""

from __future__ import annotations

import kaldera


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
