"""Évaluation de l'agent Documents et cohérence (spec § 5) sur 42 dossiers étiquetés : les 34 dossiers (cohérents),
6 contradictions construites et 2 cas ambigus (evaluation/coherence/attendus.json, outils/generer_coherence.py).

Deux passages par dossier, avec le vrai modèle :
1. l'agent seul, sur toutes les images nettes du dossier : son verdict, mesuré sur les 42 dossiers, même ceux que la
   chaîne refuse avant (éligibilité) ;
2. la chaîne complète (lecture, Coordination, cohérence, fiche) : la durée du dossier dans le budget de 10 s et la
   fiche obtenue. Le partenaire est le bouchon (aucun réseau) : son temps n'est pas compté ici.
Portes, écrites avant la mesure (verdict calculé, jamais écrit) : les 6 contradictions arrivent à une personne
(verdict contradiction ou insuffisant) ; aucune fausse alerte (contradiction sur un dossier cohérent ou ambigu) ;
au plus 3 examens inutiles sur 34 (insuffisant sur un dossier cohérent) ; aucun échec technique ; aucun dossier au-delà
de 10 s.

Lancement réel (la clé doit être dans .env), depuis la racine du dépôt :
    .venv\\Scripts\\python.exe -m outils.evaluer_coherence
    .venv\\Scripts\\python.exe -m outils.evaluer_coherence --verifier
"""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from kaldera.agents.coherence import verifier_coherence
from kaldera.bornes import BORNES
from kaldera.coordination import traiter
from kaldera.extraction.dossier import lister_images, traiter_dossier
from kaldera.extraction.lecteurs import SEUIL_NETTETE, Appeler, Reponse, nettete
from outils.evaluer_extraction import _demandes_json, _stats

RACINE = Path(__file__).resolve().parents[1]
DOSSIERS = RACINE / "dossiers"
SORTIE = RACINE / "evaluation" / "coherence"
ISSUE = ("issue", "decision", "montant_rembourse", "file", "mode_degrade", "arret")
PORTES = {"fausses_alertes_max": 0, "examens_inutiles_max": 3, "echecs_techniques_max": 0, "au_dela_du_budget_max": 0}


def _dossier(reference: str) -> Path:
    return DOSSIERS / reference if (DOSSIERS / reference).is_dir() else SORTIE / "dossiers" / reference


def _images_nettes(dossier: Path) -> list[tuple[str, str, bytes]]:
    images = lister_images(dossier) + lister_images(dossier / "depots")
    return [(chemin.relative_to(dossier).as_posix(), type_piece, chemin.read_bytes())
            for type_piece, chemin in images if nettete(chemin) >= SEUIL_NETTETE]


def _decision_attendue(attendu: dict[str, Any], fiche: dict[str, Any], demandes: dict[str, Any], atteinte: bool) -> bool:
    """Cohérent : la fiche du chemin JSON. Contradiction atteinte par la chaîne : une personne. Ambigu : l'un ou l'autre."""
    meme = {k: fiche[k] for k in ISSUE} == {k: traiter(demandes[attendu.get("base", "")] if "base" in attendu
                                                     else demandes[fiche["reference"]])[k] for k in ISSUE}
    personne = fiche["issue"] == "escalade" and fiche["file"] == "gestionnaire"
    if attendu["attendu"] == "coherent":
        return meme
    if attendu["attendu"] == "non_coherent":
        return personne or not atteinte  # non atteinte : la chaîne a conclu avant la cohérence (règle § 4)
    return meme or personne


def _mesurer(reference: str, attendu: dict[str, Any], appeler: Appeler, demandes: dict[str, Any]) -> dict[str, Any]:
    dossier = _dossier(reference)
    sinistre = json.loads((dossier / "declaration.json").read_text(encoding="utf-8"))["sinistre"]
    jetons = [0, 0]

    def compte(*args: Any, **kwargs: Any) -> Any:
        reponse = appeler(*args, delai_s=BORNES.duree_max_s, **kwargs)
        if isinstance(reponse, Reponse):
            jetons[0] += reponse.jetons_entree
            jetons[1] += reponse.jetons_sortie
        return reponse

    debut = perf_counter()
    seul = verifier_coherence(sinistre, _images_nettes(dossier), compte)
    duree_coherence = perf_counter() - debut
    debut = perf_counter()
    chaine = traiter_dossier(dossier, appeler)
    duree_dossier = perf_counter() - debut
    ligne = next((x for x in chaine["lecture"] if x["agent"] == "coherence" and x["statut"] != "non_utilise"), None)
    fiche = chaine["fiche"]
    return {"reference": reference, "attendu": attendu["attendu"], "verdict": seul.verdict, "constats": seul.constats,
            "raison": seul.raison, "duree_coherence_s": round(duree_coherence, 3),
            "duree_dossier_s": round(duree_dossier, 3), "jetons_entree": jetons[0], "jetons_sortie": jetons[1],
            "verdict_chaine": ligne["verdict"] if ligne else "non_atteint",
            "fiche": {k: fiche[k] for k in ("issue", "decision", "file", "motif")},
            "decision_attendue": _decision_attendue(attendu, {**fiche, "reference": reference}, demandes, bool(ligne))}


def synthetiser(details: list[dict[str, Any]]) -> dict[str, Any]:
    par = {a: [d for d in details if d["attendu"] == a] for a in ("coherent", "non_coherent", "ambigu")}
    verdicts = ("coherent", "contradiction", "insuffisant", "non_effectue")
    matrice = {a: {v: sum(d["verdict"] == v for d in lot) for v in verdicts} for a, lot in par.items()}
    a_une_personne = sum(d["verdict"] in ("contradiction", "insuffisant") for d in par["non_coherent"])
    fausses = sum(d["verdict"] == "contradiction" for d in par["coherent"] + par["ambigu"])
    inutiles = sum(d["verdict"] == "insuffisant" for d in par["coherent"])
    echecs = sum("non_effectue" in (d["verdict"], d.get("verdict_chaine")) for d in details)
    lents = sum(d["duree_dossier_s"] > BORNES.duree_max_s for d in details)
    chaine = [d for d in details if d.get("verdict_chaine", d["verdict"]) != "non_atteint"]
    instables = sum(d["verdict"] != d.get("verdict_chaine", d["verdict"]) for d in chaine)
    reussi = (a_une_personne == len(par["non_coherent"]) and fausses <= PORTES["fausses_alertes_max"]
              and inutiles <= PORTES["examens_inutiles_max"] and echecs <= PORTES["echecs_techniques_max"]
              and lents <= PORTES["au_dela_du_budget_max"])
    return {"dossiers": len(details), "matrice": matrice,
            "detections": {"justes": a_une_personne, "total": len(par["non_coherent"])},
            "detections_strictes": sum(d["verdict"] == "contradiction" for d in par["non_coherent"]),
            "fausses_alertes": fausses, "examens_inutiles": inutiles, "echecs_techniques": echecs,
            "au_dela_du_budget": lents, "verdicts_differents_entre_passages": instables,
            "dossiers_ou_la_chaine_atteint_la_coherence": len(chaine),
            "decisions_attendues": {"justes": sum(d["decision_attendue"] for d in details), "total": len(details)},
            "duree_coherence": _stats([d["duree_coherence_s"] for d in details]),
            "duree_dossier": _stats([d["duree_dossier_s"] for d in details]),
            "jetons": {"entree": sum(d["jetons_entree"] for d in details),
                       "sortie": sum(d["jetons_sortie"] for d in details)},
            "portes": PORTES, "verdict": "réussi" if reussi else "échoué"}


def evaluer(appeler: Appeler, paralleles: int = 1, contexte: dict | None = None) -> dict[str, Any]:
    attendus = json.loads((SORTIE / "attendus.json").read_text(encoding="utf-8"))
    demandes = _demandes_json()
    debut = perf_counter()
    with ThreadPoolExecutor(max_workers=paralleles) as executeur:
        details = list(executeur.map(lambda ref: _mesurer(ref, attendus[ref], appeler, demandes), sorted(attendus)))
    return {"contexte": {**(contexte or {}), "duree_totale_s": round(perf_counter() - debut, 1)},
            "synthese": synthetiser(details), "details": details}


def _rapport_md(resultats: dict[str, Any]) -> str:
    s, c = resultats["synthese"], resultats["contexte"]
    d, p = s["detections"], s["portes"]
    lignes = ["# Évaluation de l'agent Documents et cohérence (spec § 5)", "",
              "Rapport généré par `outils/evaluer_coherence.py` depuis `resultats.json`. Ne pas le modifier à la main : "
              "`--verifier` le recalcule et le compare.", "",
              f"- Dossiers : {s['dossiers']} ; verdict : **{s['verdict']}**"]
    lignes += [f"- {k} : {v}" for k, v in c.items()]
    lignes += ["", "## Portes (écrites avant la mesure)", "", "| Porte | Mesure | Seuil |", "|---|---|---|",
               f"| Contradictions envoyées à une personne | {d['justes']}/{d['total']} | toutes |",
               f"| Fausses alertes (contradiction sur un dossier cohérent ou ambigu) | {s['fausses_alertes']} | "
               f"au plus {p['fausses_alertes_max']} |",
               f"| Examens inutiles (insuffisant sur un dossier cohérent) | {s['examens_inutiles']} | "
               f"au plus {p['examens_inutiles_max']} |",
               f"| Échecs techniques (non effectué) | {s['echecs_techniques']} | au plus {p['echecs_techniques_max']} |",
               f"| Dossiers au-delà de 10 s | {s['au_dela_du_budget']} | au plus {p['au_dela_du_budget_max']} |",
               "", "## Verdicts de l'agent seul, par étiquette", "",
               "| Étiquette | coherent | contradiction | insuffisant | non_effectue |", "|---|---|---|---|---|"]
    lignes += [f"| {a} | {m['coherent']} | {m['contradiction']} | {m['insuffisant']} | {m['non_effectue']} |"
               for a, m in s["matrice"].items()]
    da = s["decisions_attendues"]
    lignes += ["", f"Contradictions rendues « contradiction » (et non « insuffisant ») : {s['detections_strictes']}/"
               f"{d['total']}. Verdicts différents entre l'agent seul et la chaîne complète (même dossier, deux appels) : "
               f"{s['verdicts_differents_entre_passages']} sur {s['dossiers_ou_la_chaine_atteint_la_coherence']} "
               "dossiers où la chaîne atteint la cohérence.", "",
               "## Chaîne complète", "",
               f"Fiches conformes à l'attendu : {da['justes']}/{da['total']} (cohérent : la fiche du chemin JSON ; "
               "contradiction : un gestionnaire ; ambigu : l'un ou l'autre).", "",
               "| Durée | Mesures | Moyenne (s) | p95 (s) | Max (s) |", "|---|---|---|---|---|"]
    for nom, cle in (("appel de cohérence (agent seul)", "duree_coherence"), ("dossier complet", "duree_dossier")):
        v = s[cle]
        lignes.append(f"| {nom} | {v['appels']} | {v['moyenne_s']} | {v['p95_s']} | {v['max_s']} |")
    j = s["jetons"]
    lignes += ["", f"Jetons de l'agent seul : {j['entree']} en entrée, {j['sortie']} en sortie "
               f"({j['entree'] // max(1, s['dossiers'])} et {j['sortie'] // max(1, s['dossiers'])} par dossier).",
               "", "## Dossiers à regarder", ""]
    a_regarder = [x for x in resultats["details"] if x["attendu"] != "coherent" or x["verdict"] != "coherent"
                  or not x["decision_attendue"]]
    for x in a_regarder:
        constats = " ; ".join(x["constats"]) or x["raison"]
        lignes.append(f"- {x['reference']} ({x['attendu']}) : agent **{x['verdict']}**, chaîne {x['verdict_chaine']}, "
                      f"fiche {x['fiche']['issue']} {x['fiche']['decision'] or x['fiche']['file']} ; {constats}")
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
                "python": sys.version.split()[0], "dossiers_en_parallele": 3}
    resultats = evaluer(appeler, paralleles=3, contexte=contexte)
    ecrire_rapport(resultats)
    print(_rapport_md(resultats))


if __name__ == "__main__":
    main()
