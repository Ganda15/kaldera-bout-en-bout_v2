"""Preuve d'exécution des tests d'acceptance : un fichier généré par une commande, jamais écrit à la main."""

from __future__ import annotations

from pathlib import Path

from outils.preuve_acceptance import construire_rapport, lire_junit, verifier_provenance

PREUVE = Path(__file__).resolve().parents[2] / "evaluation" / "acceptance" / "preuve-execution.md"

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" errors="0" failures="1" skipped="1" tests="3" time="1.5">
<testcase classname="tests.acceptance.test_a" name="test_un[NOM-01]" time="0.010"/>
<testcase classname="tests.acceptance.test_a" name="test_deux[AF-01]" time="0.200"><failure message="x">t</failure></testcase>
<testcase classname="tests.acceptance.test_b" name="test_trois" time="0.000"><skipped message="y"/></testcase>
</testsuite></testsuites>"""

CONTEXTE = {"date": "2026-10-08 20:00", "commit": "abc1234", "arbre_propre": True, "python": "3.11.15",
            "systeme": "Windows", "commande": "python -m pytest tests/acceptance", "duree_s": 1.5, "ci": None,
            "code_retour": 0, "attendus": 1}


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


def test_un_seul_test_reussi_ne_suffit_pas_si_56_etaient_attendus() -> None:
    un_seul = [c for c in lire_junit(JUNIT) if c["statut"] == "réussi"]
    rapport = construire_rapport({**CONTEXTE, "attendus": 56}, un_seul)
    assert "**Verdict : échec**" in rapport and "1 test(s) exécuté(s) pour 56 collecté(s)" in rapport


def test_un_code_de_retour_de_pytest_non_nul_est_un_echec() -> None:
    tout_vert = [c for c in lire_junit(JUNIT) if c["statut"] == "réussi"]
    rapport = construire_rapport({**CONTEXTE, "code_retour": 2}, tout_vert)
    assert "**Verdict : échec**" in rapport and "code de retour de pytest : 2" in rapport


def test_un_etat_git_inconnu_n_est_jamais_dit_propre() -> None:
    rapport = construire_rapport({**CONTEXTE, "arbre_propre": None}, lire_junit(JUNIT))
    assert "impossible à vérifier" in rapport and "propre (" not in rapport


def test_la_ci_cite_une_execution_precise_ou_dit_non_verifiee() -> None:
    ci = {"url": "https://github.com/o/r/actions/runs/42", "conclusion": "success", "commit": "abc1234def"}
    avec = construire_rapport({**CONTEXTE, "ci": ci}, lire_junit(JUNIT))
    assert "https://github.com/o/r/actions/runs/42" in avec and "conclusion success" in avec
    assert "non vérifiée" in construire_rapport(CONTEXTE, lire_junit(JUNIT))


def faux_git(reponses: dict[tuple[str, ...], tuple[bool, str]]):
    return lambda *args: reponses.get(args, (True, ""))


def test_la_provenance_signale_un_commit_absent_un_code_modifie_et_des_totaux_faux() -> None:
    texte = construire_rapport(CONTEXTE, [c for c in lire_junit(JUNIT) if c["statut"] == "réussi"])
    assert verifier_provenance(texte, faux_git({})) == []
    absent = faux_git({("cat-file", "-e", "abc1234^{commit}"): (False, "")})
    assert any("commit" in e for e in verifier_provenance(texte, absent))
    modifie = faux_git({("diff", "--quiet", "abc1234", "--", "src", "tests/acceptance", "external_agent", "eval"):
                        (False, "")})
    assert any("modifié" in e for e in verifier_provenance(texte, modifie))
    faux_total = texte.replace("1 réussi(s)", "9 réussi(s)")
    assert any("totaux" in e for e in verifier_provenance(faux_total, faux_git({})))


def test_le_rapport_signale_un_arbre_de_travail_modifie() -> None:
    rapport = construire_rapport({**CONTEXTE, "arbre_propre": False}, lire_junit(JUNIT))
    assert "modifications non enregistrées" in rapport


def test_la_preuve_enregistree_montre_56_tests_passes() -> None:
    texte = PREUVE.read_text(encoding="utf-8")
    assert "**Verdict : tous les tests d'acceptance passent**" in texte
    assert "56 réussi(s), 0 échoué(s), 0 ignoré(s)" in texte
    assert sum(1 for ligne in texte.splitlines() if ligne.startswith("| test_") and "| réussi |" in ligne) == 56
    assert "modifications non enregistrées" not in texte and "impossible à vérifier" not in texte
    # La ligne « intégration continue » n'est pas vérifiée ici : elle cite l'exécution CI du commit testé, qui
    # n'existe qu'après l'envoi de ce commit ; l'exiger ferait échouer la CI de ce même commit.
