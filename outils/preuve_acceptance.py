"""Preuve d'exécution des tests d'acceptance fournis (livrable du brief) : générée par une commande, jamais à la main.

Lance la suite tests/acceptance avec pytest, lit le rapport JUnit (un fichier XML qui donne le statut et la durée de
chaque test) et écrit evaluation/acceptance/preuve-execution.md : date, commit, arbre de travail propre ou non,
version de Python, commande, verdict, et une ligne par test. `--verifier` relance la suite et compare au fichier.

Lancement, depuis la racine du dépôt :
    .venv\\Scripts\\python.exe -m outils.preuve_acceptance
    .venv\\Scripts\\python.exe -m outils.preuve_acceptance --verifier
"""

from __future__ import annotations

import platform
import subprocess
import sys
import tempfile
import time
# Analyseur XML de la bibliothèque standard : le XML vient de notre propre exécution de pytest, jamais de
# l'extérieur ; ElementTree ne charge aucune entité externe et expat (2.4 et plus) bloque l'expansion en cascade.
import xml.etree.ElementTree as ET  # noqa: S405
from datetime import datetime
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "evaluation" / "acceptance" / "preuve-execution.md"
COMMANDE = "python -m pytest tests/acceptance -q -p no:cacheprovider --junitxml=<rapport.xml>"
CI = "https://github.com/Ganda15/kaldera-bout-en-bout_v2/actions"


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
    tout_passe = compte["échoué"] == 0 and compte["ignoré"] == 0 and compte["réussi"] > 0
    verdict = "**Verdict : tous les tests d'acceptance passent**" if tout_passe else "**Verdict : échec**"
    arbre = ("propre (le code testé est exactement celui du commit)" if contexte["arbre_propre"]
             else "modifications non enregistrées : le code testé n'est pas exactement celui du commit")
    lignes = [
        "# Preuve d'exécution des tests d'acceptance", "",
        "Fichier généré par `outils/preuve_acceptance.py`. Ne pas le modifier à la main : "
        "`python -m outils.preuve_acceptance --verifier` relance la suite et compare.", "",
        f"- date : {contexte['date']}",
        f"- commit testé : `{contexte['commit']}` ; arbre de travail : {arbre}",
        f"- Python {contexte['python']} ; système : {contexte['systeme']}",
        f"- commande : `{contexte['commande']}`",
        f"- durée de la suite : {contexte['duree_s']} s",
        f"- la même suite tourne en intégration continue à chaque envoi sur GitHub : {CI}", "",
        verdict, "",
        f"{compte['réussi']} réussi(s), {compte['échoué']} échoué(s), {compte['ignoré']} ignoré(s), sur {len(cas)} tests.",
        "",
        "| Test | Statut | Durée (s) |",
        "|---|---|---|",
    ]
    lignes += [f"| {c['test']} | {c['statut']} | {c['duree_s']} |" for c in cas]
    return "\n".join(lignes) + "\n"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=RACINE).stdout.strip()


def executer() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with tempfile.TemporaryDirectory() as dossier:
        rapport_xml = Path(dossier) / "rapport.xml"
        debut = time.perf_counter()
        subprocess.run([sys.executable, "-m", "pytest", "tests/acceptance", "-q", "-p", "no:cacheprovider",
                        f"--junitxml={rapport_xml}"], cwd=RACINE, capture_output=True, text=True)
        duree = round(time.perf_counter() - debut, 1)
        cas = lire_junit(rapport_xml.read_text(encoding="utf-8"))
    modifs = [ligne for ligne in _git("status", "--porcelain").splitlines()
              if "evaluation/acceptance/" not in ligne]  # le fichier de preuve lui-même ne compte pas
    contexte = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "commit": _git("rev-parse", "--short", "HEAD"),
                "arbre_propre": not modifs, "python": platform.python_version(),
                "systeme": f"{platform.system()} {platform.release()}", "commande": COMMANDE, "duree_s": duree}
    return contexte, cas


def verifier() -> list[str]:
    """Relance la suite ; rend les écarts entre le fichier enregistré et l'exécution (liste vide : conforme)."""
    _, cas = executer()
    enregistres = {ligne.split(" | ")[0].lstrip("| ").strip(): ligne.split(" | ")[1].strip()
                   for ligne in SORTIE.read_text(encoding="utf-8").splitlines() if ligne.startswith("| test_")}
    obtenus = {c["test"]: c["statut"] for c in cas}
    return sorted(f"{t} : enregistré {enregistres.get(t)!r}, obtenu {obtenus.get(t)!r}"
                  for t in set(enregistres) | set(obtenus) if enregistres.get(t) != obtenus.get(t))


def main() -> None:
    if "--verifier" in sys.argv:
        ecarts = verifier()
        print("vérification : conforme" if not ecarts else "vérification : écarts\n" + "\n".join(ecarts))
        raise SystemExit(1 if ecarts else 0)
    contexte, cas = executer()
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(construire_rapport(contexte, cas), encoding="utf-8")
    print(f"{sum(c['statut'] == 'réussi' for c in cas)}/{len(cas)} réussis ; commit {contexte['commit']} ; "
          f"arbre propre : {contexte['arbre_propre']}")


if __name__ == "__main__":
    main()
