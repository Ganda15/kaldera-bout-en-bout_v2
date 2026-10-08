"""Preuve d'exécution des tests d'acceptance : un fichier généré par une commande, jamais écrit à la main."""

from __future__ import annotations

from pathlib import Path

from outils.preuve_acceptance import construire_rapport, lire_junit

PREUVE = Path(__file__).resolve().parents[2] / "evaluation" / "acceptance" / "preuve-execution.md"

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" errors="0" failures="1" skipped="1" tests="3" time="1.5">
<testcase classname="tests.acceptance.test_a" name="test_un[NOM-01]" time="0.010"/>
<testcase classname="tests.acceptance.test_a" name="test_deux[AF-01]" time="0.200"><failure message="x">t</failure></testcase>
<testcase classname="tests.acceptance.test_b" name="test_trois" time="0.000"><skipped message="y"/></testcase>
</testsuite></testsuites>"""

CONTEXTE = {"date": "2026-10-08 20:00", "commit": "abc1234", "arbre_propre": True, "python": "3.11.15",
            "systeme": "Windows", "commande": "python -m pytest tests/acceptance", "duree_s": 1.5, "ci": None}


def test_lire_junit_donne_le_statut_de_chaque_test() -> None:
    cas = lire_junit(JUNIT)
    assert [(c["test"], c["statut"]) for c in cas] == [
        ("test_a::test_un[NOM-01]", "réussi"), ("test_a::test_deux[AF-01]", "échoué"), ("test_b::test_trois", "ignoré")]
    assert cas[1]["duree_s"] == 0.2


def test_le_rapport_ne_dit_tout_passe_que_si_tout_passe() -> None:
    cas = lire_junit(JUNIT)
    rapport = construire_rapport(CONTEXTE, cas)
    assert "**Verdict : échec**" in rapport and "1 réussi(s), 1 échoué(s), 1 ignoré(s)" in rapport
    tout_vert = [c for c in cas if c["statut"] == "réussi"]
    assert "**Verdict : tous les tests d'acceptance passent**" in construire_rapport(CONTEXTE, tout_vert)


def test_le_rapport_signale_un_arbre_de_travail_modifie() -> None:
    rapport = construire_rapport({**CONTEXTE, "arbre_propre": False}, lire_junit(JUNIT))
    assert "modifications non enregistrées" in rapport


def test_la_preuve_enregistree_montre_56_tests_passes() -> None:
    texte = PREUVE.read_text(encoding="utf-8")
    assert "**Verdict : tous les tests d'acceptance passent**" in texte
    assert "56 réussi(s), 0 échoué(s), 0 ignoré(s)" in texte
    assert sum(1 for ligne in texte.splitlines() if ligne.startswith("| test_") and "| réussi |" in ligne) == 56
    assert "modifications non enregistrées" not in texte
