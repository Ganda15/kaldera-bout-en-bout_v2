"""Étape E4 : évaluation de l'extraction sur les 34 dossiers, contre la vérité connue (dossiers/verite.json).

Mesure, pour chaque dossier traité depuis ses pièces : chaque champ lu (contrat, lisibilité, montant des factures),
l'identité de la décision avec le chemin JSON, les appels au modèle (nombre, durées), les lectures impossibles.
Le rapport est généré depuis ces mesures ; `--verifier` recalcule tout depuis resultats.json et compare.

Lancement réel (la clé doit être dans .env), depuis la racine du dépôt :
    .venv\\Scripts\\python.exe -m outils.evaluer_extraction
    .venv\\Scripts\\python.exe -m outils.evaluer_extraction --verifier
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel

from kaldera.agents.coherence import Interpretation
from kaldera.coordination import traiter
from kaldera.extraction.dossier import lister_images, traiter_dossier
from kaldera.extraction.lecteurs import Appeler, ContratLu
from kaldera.metriques import calculer_metriques_lecture

RACINE = Path(__file__).resolve().parents[1]
DOSSIERS = RACINE / "dossiers"
SORTIE = RACINE / "evaluation" / "extraction"
SEUIL_CHAMP = 0.95  # exactitude minimale de chaque champ
SEUIL_DECISIONS = 0.95  # part minimale de décisions identiques au chemin JSON
CHAMPS_CONTRAT = ("numero", "formule", "date_souscription", "statut", "cotisations_a_jour")
ISSUE = ("issue", "decision", "montant_rembourse", "file", "mode_degrade", "arret")


def _demandes_json() -> dict[str, dict[str, Any]]:
    lignes = (RACINE / "eval" / "scenarios.jsonl").read_text(encoding="utf-8").splitlines()
    return {d["reference"]: d for ligne in lignes if ligne.strip() for d in json.loads(ligne)["demandes"]}


def _evaluer_dossier(dossier: Path, appeler: Appeler, verite: dict[str, Any], demande_json: dict[str, Any]) -> dict:
    appels: list[dict[str, Any]] = []

    def mesure(consigne: str, schema: type[BaseModel], image_png: bytes | list[bytes] | None = None, *,
               delai_s: float | None = None) -> Any:
        debut = perf_counter()
        try:
            return appeler(consigne, schema, image_png, delai_s=delai_s)
        finally:
            appels.append({"schema": "contrat" if schema is ContratLu else
                           "coherence" if schema is Interpretation else "facture",
                           "duree_s": round(perf_counter() - debut, 3)})

    resultat = traiter_dossier(dossier, mesure)
    demande, champs, erreurs = resultat["demande"], {}, []

    def noter(champ: str, lu: Any, attendu: Any, egal: bool) -> None:
        justes, total = champs.get(champ, (0, 0))
        champs[champ] = (justes + int(egal), total + 1)
        if not egal:
            erreurs.append(f"{champ} : lu {lu!r}, attendu {attendu!r}")

    for cle in CHAMPS_CONTRAT:
        lu = demande["contrat"][cle] if demande else None
        noter(f"contrat.{cle}", lu, verite["contrat"][cle], lu == verite["contrat"][cle])
    lus: dict[str, Any] = {}
    if demande:
        noms = [f"{c.name}" for _, c in lister_images(dossier)] + [f"depots/{c.name}" for _, c in lister_images(dossier / "depots")]
        lus = dict(zip(noms, demande["pieces"] + demande["espace_assure"]["depots"], strict=True))
    for nom, vrai in verite["fichiers"].items():
        lu = lus.get(nom, {})
        noter("pieces.lisible", f"{nom} {lu.get('lisible')}", vrai["lisible"], lu.get("lisible") == vrai["lisible"])
        if vrai["type"] == "facture" and vrai["lisible"]:
            montant = lu.get("montant")
            noter("factures.montant", f"{nom} {montant}", vrai["montant"],
                  montant is not None and abs(montant - vrai["montant"]) < 0.01)
    attendu = traiter(demande_json)
    identique = {k: resultat["fiche"][k] for k in ISSUE} == {k: attendu[k] for k in ISSUE}
    return {"reference": dossier.name, "impossible": demande is None, "decision_identique": identique,
            "champs": {k: list(v) for k, v in champs.items()}, "erreurs": erreurs, "appels": appels,
            "lecture": resultat["lecture"],
            "motif_si_impossible": None if demande else resultat["fiche"]["motif"]}


def _stats(durees: list[float]) -> dict[str, Any]:
    if not durees:
        return {"appels": 0, "moyenne_s": None, "p95_s": None, "max_s": None}
    triees = sorted(durees)
    p95 = triees[min(len(triees) - 1, math.ceil(0.95 * len(triees)) - 1)]
    return {"appels": len(triees), "moyenne_s": round(sum(triees) / len(triees), 2), "p95_s": round(p95, 2),
            "max_s": round(triees[-1], 2)}


def synthetiser(details: list[dict[str, Any]]) -> dict[str, Any]:
    champs: dict[str, list[int]] = {}
    for d in details:
        for champ, (justes, total) in d["champs"].items():
            champs.setdefault(champ, [0, 0])
            champs[champ][0] += justes
            champs[champ][1] += total
    champs_sortie = {k: {"justes": j, "total": t, "taux": round(j / t, 4)} for k, (j, t) in sorted(champs.items())}
    identiques = sum(d["decision_identique"] for d in details)
    impossibles = sum(d["impossible"] for d in details)
    appels = [a for d in details for a in d["appels"]]
    lectures = [d.get("lecture", []) for d in details]
    lignes = [x for lecture in lectures for x in lecture]
    reussi = (all(c["taux"] >= SEUIL_CHAMP for c in champs_sortie.values()) and impossibles == 0
              and identiques / len(details) >= SEUIL_DECISIONS)
    return {"dossiers": len(details), "champs": champs_sortie,
            "decisions_identiques": {"justes": identiques, "total": len(details)},
            "extractions_impossibles": impossibles,
            "appels_modele": {s: _stats([a["duree_s"] for a in appels if a["schema"] == s])
                              for s in ("contrat", "facture", "coherence")},
            "jetons": {"entree": sum(x.get("jetons_entree", 0) for x in lignes),
                       "sortie": sum(x.get("jetons_sortie", 0) for x in lignes)},
            "metriques_lecture": calculer_metriques_lecture(lectures),
            "seuils": {"champ": SEUIL_CHAMP, "decisions": SEUIL_DECISIONS},
            "verdict": "réussi" if reussi else "échoué"}


def evaluer(dossiers: Path, appeler: Appeler, paralleles: int = 1, contexte: dict | None = None) -> dict[str, Any]:
    verite = json.loads((dossiers / "verite.json").read_text(encoding="utf-8"))
    demandes = _demandes_json()
    references = sorted(verite)
    debut = perf_counter()
    with ThreadPoolExecutor(max_workers=paralleles) as executeur:
        details = list(executeur.map(
            lambda ref: _evaluer_dossier(dossiers / ref, appeler, verite[ref], demandes[ref]), references))
    return {"contexte": {**(contexte or {}), "duree_totale_s": round(perf_counter() - debut, 1)},
            "synthese": synthetiser(details), "details": details}


def _rapport_md(resultats: dict[str, Any]) -> str:
    s, c = resultats["synthese"], resultats["contexte"]
    lignes = ["# Évaluation de l'extraction (étape E4)", "",
              "Rapport généré par `outils/evaluer_extraction.py` depuis `resultats.json`. Ne pas le modifier à la "
              "main : `--verifier` le recalcule et le compare.", "",
              f"- Dossiers : {s['dossiers']} ; verdict : **{s['verdict']}** (seuils : {s['seuils']['champ']:.0%} par "
              f"champ, {s['seuils']['decisions']:.0%} de décisions identiques, aucune lecture impossible)"]
    lignes += [f"- {k} : {v}" for k, v in c.items()]
    lignes += ["", "## Exactitude par champ", "", "| Champ | Justes | Taux |", "|---|---|---|"]
    lignes += [f"| `{k}` | {v['justes']}/{v['total']} | {v['taux']:.2%} |" for k, v in s["champs"].items()]
    d = s["decisions_identiques"]
    lignes += ["", "## Décisions", "",
               f"Décisions identiques au chemin JSON (issue, décision, montant, file, mode dégradé, arrêt) : "
               f"{d['justes']}/{d['total']}. Lectures impossibles : {s['extractions_impossibles']}."]
    for x in resultats["details"]:  # une décision différente : dire si la lecture ou la cohérence l'a changée
        if not x["decision_identique"]:
            verdicts = [ligne.get("verdict") for ligne in x.get("lecture", [])
                        if ligne["agent"] == "coherence" and ligne.get("statut") != "non_utilise"]
            lignes.append(f"- {x['reference']} : décision différente du chemin JSON ; cohérence des pièces : "
                          f"{verdicts[0] if verdicts else 'non atteinte'}")
    lignes += ["", "## Appels au modèle", "", "| Lecture | Appels | Moyenne (s) | p95 (s) | Max (s) |", "|---|---|---|---|---|"]
    lignes += [f"| {k} | {v['appels']} | {v['moyenne_s']} | {v['p95_s']} | {v['max_s']} |"
               for k, v in s["appels_modele"].items()]
    j = s["jetons"]
    lignes += ["", "## Jetons consommés et métriques des agents de lecture", "",
               f"Jetons : {j['entree']} en entrée, {j['sortie']} en sortie, pour {s['dossiers']} dossiers "
               f"({j['entree'] // max(1, s['dossiers'])} et {j['sortie'] // max(1, s['dossiers'])} par dossier en moyenne). "
               "Coût = jetons d'entrée × prix d'entrée + jetons de sortie × prix de sortie, aux prix du déploiement "
               "(portail Azure).", "",
               "| Agent | Lectures | Échecs | Latence moyenne (ms) | Appels au modèle | Jetons entrée | Jetons sortie |",
               "|---|---|---|---|---|---|---|"]
    lignes += [f"| {k} | {v['appels']} | {v['echecs']} | {v['latence_ms']} | {v['appels_externes']} | "
               f"{v['jetons_entree']} | {v['jetons_sortie']} |" for k, v in s["metriques_lecture"].items()]
    erreurs = [d for d in resultats["details"] if d["erreurs"] or d["impossible"]]
    lignes += ["", "## Écarts", ""]
    if not erreurs:
        lignes.append("Aucun écart.")
    for d in erreurs:
        if d["impossible"]:
            lignes.append(f"- {d['reference']} : lecture impossible ({d['motif_si_impossible']})")
        lignes += [f"- {d['reference']} : {e}" for e in d["erreurs"] if not d["impossible"]]
    return "\n".join(lignes) + "\n"


def ecrire_rapport(resultats: dict[str, Any], sortie: Path = SORTIE) -> None:
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "resultats.json").write_text(json.dumps(resultats, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (sortie / "rapport.md").write_text(_rapport_md(resultats), encoding="utf-8")


def verifier(sortie: Path = SORTIE) -> list[str]:
    """Recalcule la synthèse depuis les détails, puis le rapport depuis le JSON : rend la liste des écarts."""
    resultats = json.loads((sortie / "resultats.json").read_text(encoding="utf-8"))
    problemes = []
    if synthetiser(resultats["details"]) != resultats["synthese"]:
        problemes.append("la synthèse ne correspond pas aux détails")
    if (sortie / "rapport.md").read_text(encoding="utf-8") != _rapport_md(resultats):
        problemes.append("rapport.md ne correspond pas à resultats.json (modifié à la main ?)")
    return problemes


def main() -> None:
    if "--verifier" in sys.argv:
        problemes = verifier()
        print("vérification :", "conforme" if not problemes else problemes)
        sys.exit(1 if problemes else 0)
    from kaldera.extraction import lecteurs, modele

    config = modele.configuration()
    appeler = lecteurs.appel_modele(modele.client(config), config.deploiement)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RACINE, capture_output=True,
                            text=True).stdout.strip()
    contexte = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "modele": config.deploiement, "commit": commit,
                "python": sys.version.split()[0], "lectures_en_parallele": 6}
    resultats = evaluer(DOSSIERS, appeler, paralleles=6, contexte=contexte)
    ecrire_rapport(resultats)
    print(_rapport_md(resultats))


if __name__ == "__main__":
    main()
