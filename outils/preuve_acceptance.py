"""Preuve d'exécution des tests d'acceptance fournis (livrable du brief) : générée par une commande, jamais à la main.

Compte d'abord les tests collectés, puis lance la suite tests/acceptance avec pytest, lit le rapport JUnit (un fichier
XML qui donne le statut et la durée de chaque test) et écrit evaluation/acceptance/preuve-execution.md : date, commit,
état de l'arbre de travail, version de Python, commande, code de retour, verdict, exécution de la CI pour ce commit,
une ligne par test. Le verdict « tout passe » exige un code de retour 0, aucun échec ni test ignoré, et autant de tests
exécutés que collectés. Une vérification Git qui échoue est dite « impossible à vérifier », jamais « propre ».

`--verifier` relance la suite et compare les noms et statuts des tests, puis contrôle la provenance du rapport : le
commit existe, le code testé n'a pas changé depuis, les totaux correspondent aux lignes. Les durées varient d'une
exécution à l'autre : elles ne sont pas comparées.

Lancement, depuis la racine du dépôt :
    .venv\\Scripts\\python.exe -m outils.preuve_acceptance
    .venv\\Scripts\\python.exe -m outils.preuve_acceptance --verifier
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
import tempfile
import time

# Analyseur XML de la bibliothèque standard : le XML vient de notre propre exécution de pytest, jamais de
# l'extérieur ; ElementTree ne charge aucune entité externe et expat (2.4 et plus) bloque l'expansion en cascade.
import xml.etree.ElementTree as ET  # noqa: S405
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "evaluation" / "acceptance" / "preuve-execution.md"
COMMANDE = "python -m pytest tests/acceptance -q -p no:cacheprovider --junitxml=<rapport.xml>"
CODE_TESTE = ("src", "tests/acceptance", "external_agent", "eval")  # ce dont dépend le résultat de la suite
Git = Callable[..., tuple[bool, str]]


def _git(*args: str) -> tuple[bool, str]:
    """(réussi, sortie) : une commande Git qui échoue n'est jamais confondue avec une réponse vide."""
    try:
        resultat = subprocess.run(["git", *args], capture_output=True, text=True, cwd=RACINE)
    except OSError:
        return False, ""
    return resultat.returncode == 0, resultat.stdout.strip()


def lire_junit(xml: str) -> list[dict[str, Any]]:
    """Une entrée par test : nom (fichier::test), statut (réussi, échoué, ignoré), durée en secondes."""
    cas = []
    for test in ET.fromstring(xml).iter("testcase"):
        if test.find("failure") is not None or test.find("error") is not None:
            statut = "échoué"
        elif test.find("skipped") is not None:
            statut = "ignoré"
        else:
            statut = "réussi"
        cas.append({"test": f"{test.get('classname', '').split('.')[-1]}::{test.get('name')}", "statut": statut,
                    "duree_s": round(float(test.get("time", 0)), 3)})
    return cas


def construire_rapport(contexte: dict[str, Any], cas: list[dict[str, Any]]) -> str:
    compte = {s: sum(1 for c in cas if c["statut"] == s) for s in ("réussi", "échoué", "ignoré")}
    tout_passe = (contexte["code_retour"] == 0 and compte["échoué"] == 0 and compte["ignoré"] == 0
                  and compte["réussi"] > 0 and len(cas) == contexte["attendus"])
    verdict = "**Verdict : tous les tests d'acceptance passent**" if tout_passe else "**Verdict : échec**"
    if contexte["arbre_propre"] is None:
        arbre = "impossible à vérifier (Git n'a pas répondu)"
    elif contexte["arbre_propre"]:
        arbre = "propre (le code testé est exactement celui du commit)"
    else:
        arbre = "modifications non enregistrées : le code testé n'est pas exactement celui du commit"
    ci = contexte.get("ci")
    ligne_ci = (f"exécution {ci['url']} sur le commit `{ci['commit'][:7]}`, conclusion {ci['conclusion']}" if ci
                else "non vérifiée (aucune exécution terminée trouvée pour ce commit)")
    lignes = [
        "# Preuve d'exécution des tests d'acceptance", "",
        "Fichier généré par `outils/preuve_acceptance.py`. Ne pas le modifier à la main. "
        "`python -m outils.preuve_acceptance --verifier` relance la suite et compare les noms et statuts des tests, "
        "puis contrôle la provenance (commit existant, code testé inchangé depuis, totaux) ; les durées ne sont pas "
        "comparées, elles varient d'une exécution à l'autre.", "",
        f"- date : {contexte['date']}",
        f"- commit testé : `{contexte['commit']}` ; arbre de travail : {arbre}",
        f"- Python {contexte['python']} ; système : {contexte['systeme']}",
        f"- commande : `{contexte['commande']}` ; code de retour de pytest : {contexte['code_retour']}",
        f"- durée de la suite : {contexte['duree_s']} s (les {len(cas)} tests ensemble ; ce n'est pas la durée "
        "d'une demande)",
        f"- intégration continue : {ligne_ci}", "",
        verdict, "",
        f"{compte['réussi']} réussi(s), {compte['échoué']} échoué(s), {compte['ignoré']} ignoré(s), sur {len(cas)} tests ; "
        f"{len(cas)} test(s) exécuté(s) pour {contexte['attendus']} collecté(s).",
        "",
        "| Test | Statut | Durée (s) |",
        "|---|---|---|",
    ]
    lignes += [f"| {c['test']} | {c['statut']} | {c['duree_s']} |" for c in cas]
    return "\n".join(lignes) + "\n"


def compter_collectes() -> int:
    sortie = subprocess.run([sys.executable, "-m", "pytest", "tests/acceptance", "--collect-only", "-q",
                             "-p", "no:cacheprovider"], cwd=RACINE, capture_output=True, text=True).stdout
    trouve = re.search(r"(\d+) tests? collected", sortie)
    return int(trouve.group(1)) if trouve else 0


def execution_ci(commit_complet: str) -> dict[str, str] | None:
    """L'exécution GitHub Actions terminée pour ce commit (via gh), ou None si introuvable."""
    ok, origine = _git("remote", "get-url", "origin")
    depot = re.search(r"github\.com[:/](.+?)(?:\.git)?$", origine) if ok else None
    if not depot:
        return None
    try:
        sortie = subprocess.run(["gh", "run", "list", "-R", depot.group(1), "--commit", commit_complet, "--json",
                                 "url,conclusion,headSha,status", "-L", "5"], capture_output=True, text=True, cwd=RACINE)
        executions = json.loads(sortie.stdout or "[]")
    except (OSError, ValueError):
        return None
    terminees = [e for e in executions if e.get("status") == "completed"]
    return ({"url": terminees[0]["url"], "conclusion": terminees[0]["conclusion"], "commit": terminees[0]["headSha"]}
            if terminees else None)


def executer() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    attendus = compter_collectes()
    with tempfile.TemporaryDirectory() as dossier:
        rapport_xml = Path(dossier) / "rapport.xml"
        debut = time.perf_counter()
        resultat = subprocess.run([sys.executable, "-m", "pytest", "tests/acceptance", "-q", "-p", "no:cacheprovider",
                                   f"--junitxml={rapport_xml}"], cwd=RACINE, capture_output=True, text=True)
        duree = round(time.perf_counter() - debut, 1)
        cas = lire_junit(rapport_xml.read_text(encoding="utf-8")) if rapport_xml.exists() else []
    ok_statut, statut = _git("status", "--porcelain")
    modifs = [ligne for ligne in statut.splitlines() if "evaluation/acceptance/" not in ligne]  # la preuve elle-même
    ok_commit, commit_complet = _git("rev-parse", "HEAD")
    contexte = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "commit": commit_complet[:7] if ok_commit else "inconnu",
                "arbre_propre": (not modifs) if ok_statut else None, "python": platform.python_version(),
                "systeme": f"{platform.system()} {platform.version()}",  # release() dit « 10 » sous Windows 11
                "commande": COMMANDE, "duree_s": duree, "code_retour": resultat.returncode, "attendus": attendus,
                "ci": execution_ci(commit_complet) if ok_commit else None}
    return contexte, cas


def verifier_provenance(texte: str, git: Git = _git) -> list[str]:
    """Ce que la relance ne montre pas : le commit existe, le code testé n'a pas changé depuis, les totaux tiennent."""
    ecarts = []
    trouve = re.search(r"commit testé : `([0-9a-f]+)`", texte)
    if not trouve:
        return ["commit testé absent du rapport"]
    commit = trouve.group(1)
    if not git("cat-file", "-e", f"{commit}^{{commit}}")[0]:
        ecarts.append(f"commit {commit} introuvable dans le dépôt (ou Git n'a pas répondu)")
    elif not git("diff", "--quiet", commit, "--", *CODE_TESTE)[0]:
        ecarts.append(f"code testé modifié depuis le commit {commit} (ou Git n'a pas répondu) : rapport à régénérer")
    lignes = [ligne.split(" | ")[1].strip() for ligne in texte.splitlines() if ligne.startswith("| test_")]
    total = re.search(r"(\d+) réussi\(s\), (\d+) échoué\(s\), (\d+) ignoré\(s\), sur (\d+) tests", texte)
    attendu = (lignes.count("réussi"), lignes.count("échoué"), lignes.count("ignoré"), len(lignes))
    if not total or tuple(int(x) for x in total.groups()) != attendu:
        ecarts.append(f"totaux du rapport différents des lignes de test {attendu}")
    return ecarts


def verifier() -> list[str]:
    """Relance la suite et contrôle la provenance ; rend les écarts (liste vide : conforme)."""
    texte = SORTIE.read_text(encoding="utf-8")
    _, cas = executer()
    enregistres = {ligne.split(" | ")[0].lstrip("| ").strip(): ligne.split(" | ")[1].strip()
                   for ligne in texte.splitlines() if ligne.startswith("| test_")}
    obtenus = {c["test"]: c["statut"] for c in cas}
    ecarts = sorted(f"{t} : enregistré {enregistres.get(t)!r}, obtenu {obtenus.get(t)!r}"
                    for t in set(enregistres) | set(obtenus) if enregistres.get(t) != obtenus.get(t))
    return ecarts + verifier_provenance(texte)


def main() -> None:
    if "--verifier" in sys.argv:
        ecarts = verifier()
        print("vérification : conforme" if not ecarts else "vérification : écarts\n" + "\n".join(ecarts))
        raise SystemExit(1 if ecarts else 0)
    contexte, cas = executer()
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    rapport = construire_rapport(contexte, cas)
    SORTIE.write_text(rapport, encoding="utf-8")
    tout_passe = "**Verdict : tous les tests d'acceptance passent**" in rapport
    print(f"{sum(c['statut'] == 'réussi' for c in cas)}/{contexte['attendus']} réussis ; commit {contexte['commit']} ; "
          f"arbre : {contexte['arbre_propre']} ; CI : {(contexte['ci'] or {}).get('conclusion', 'non vérifiée')}")
    raise SystemExit(0 if tout_passe else 1)


if __name__ == "__main__":
    main()
