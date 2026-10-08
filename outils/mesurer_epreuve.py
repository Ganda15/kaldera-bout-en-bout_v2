"""Mesure de l'épreuve du réel : les 28 scénarios rejoués contre le partenaire simulé fourni, par le réseau local.

Pour chaque scénario : le partenaire est remis à zéro et réglé comme le scénario l'indique, puis `traiter_lot` traite
ses demandes avec le vrai client A2A. On mesure l'issue comparée au champ `attendu`, les appels reçus par le
partenaire, les échecs, la raison de chaque avis indisponible (lue dans la trace), la longueur de trace et la durée du
lot. Les scénarios de panne sont rejoués cinq fois (durées minimale et maximale).

Lancement, depuis la racine du dépôt :
    .venv\\Scripts\\python.exe outils\\mesurer_epreuve.py
Sorties (générées, ne pas modifier à la main) : evaluation/epreuve/mesures.json et evaluation/epreuve/rapport.md.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import uvicorn

RACINE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RACINE / "src"), str(RACINE)]
SORTIE = RACINE / "evaluation" / "epreuve"
REJEUX_PANNE = 5


def demarrer_partenaire() -> tuple[str, Any]:
    os.environ.setdefault("PARTENAIRE_JETON", "jeton-mesure")
    from external_agent.app import app

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    serveur = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", ws="none"))
    threading.Thread(target=serveur.run, daemon=True).start()
    limite = time.monotonic() + 10
    while not serveur.started:
        if time.monotonic() > limite:
            raise RuntimeError("le partenaire simulé n'a pas démarré")
        time.sleep(0.05)
    return f"http://127.0.0.1:{port}", serveur


def conforme(fiche: dict[str, Any], attendu: dict[str, Any]) -> bool:
    """Même règle que la suite d'acceptance : seuls les champs présents dans `attendu` sont comparés."""
    for champ in ("issue", "decision", "file"):
        if champ in attendu and fiche.get(champ) != attendu[champ]:
            return False
    if "montant_rembourse" in attendu:
        obtenu, prevu = fiche.get("montant_rembourse"), attendu["montant_rembourse"]
        if (prevu is None) != (obtenu is None) or (prevu is not None and abs(obtenu - prevu) >= 0.01):
            return False
    if "mode_degrade" in attendu and bool(fiche.get("mode_degrade")) is not attendu["mode_degrade"]:
        return False
    if "avis_fraude" in attendu:
        avis = fiche.get("avis_fraude")
        if (attendu["avis_fraude"] is None) != (avis is None):
            return False
        if avis is not None and avis.get("niveau") != attendu["avis_fraude"]:
            return False
    return not (attendu.get("arret") and not (fiche.get("arret") or {}).get("borne"))


def rejouer(scenario: dict[str, Any], url: str, pilote: httpx.Client) -> dict[str, Any]:
    import kaldera

    pilote.post("/_sim/reset").raise_for_status()
    pilote.post("/_sim/mode", json=scenario["partenaire"]).raise_for_status()
    debut = time.perf_counter()
    resultat = kaldera.traiter_lot(scenario["demandes"], partenaire_url=url)
    duree = time.perf_counter() - debut
    journal = pilote.get("/_sim/journal").json()
    fiches = {f["reference"]: f for f in resultat["fiches"]}
    lignes_af = [x for f in resultat["fiches"] for x in f["trace"] if x["agent"] == "antifraude"]
    return {
        "id": scenario["id"], "categorie": scenario["categorie"], "partenaire": scenario["partenaire"],
        "demandes": len(scenario["demandes"]),
        "conformes": sum(conforme(fiches[a["reference"]], a) for a in scenario["attendu"]),
        "appels_partenaire": len(journal),
        "doublons_recus": sum(1 for e in journal if e.get("doublon")),
        "max_appels_par_dossier": max([sum(1 for e in journal if e.get("reference") == r) for r in fiches] or [0]),
        "echecs": sum(1 for x in lignes_af if x["statut"] == "echec"),
        "raisons": sorted(x["raison"] for x in lignes_af if x.get("raison")),
        "trace_max": max(len(f["trace"]) for f in resultat["fiches"]),
        "duree_lot_s": round(duree, 3),
    }


def main() -> None:
    import kaldera

    scenarios = [json.loads(ligne) for ligne in (RACINE / "eval" / "scenarios.jsonl").read_text(encoding="utf-8")
                 .splitlines() if ligne.strip()]
    url, serveur = demarrer_partenaire()
    pilote = httpx.Client(base_url=url, timeout=15)
    mesures = []
    for scenario in scenarios:
        essais = [rejouer(scenario, url, pilote) for _ in range(REJEUX_PANNE if scenario["categorie"] == "panne" else 1)]
        mesure = essais[0]
        if len(essais) > 1:
            mesure["rejeux"] = len(essais)
            mesure["duree_lot_min_s"] = min(e["duree_lot_s"] for e in essais)
            mesure["duree_lot_max_s"] = max(e["duree_lot_s"] for e in essais)
            mesure["conformes_tous_rejeux"] = all(e["conformes"] == e["demandes"] for e in essais)
        mesures.append(mesure)
    serveur.should_exit = True

    synthese = {
        "scenarios": len(mesures), "demandes": sum(m["demandes"] for m in mesures),
        "demandes_conformes": sum(m["conformes"] for m in mesures),
        "appels_partenaire": sum(m["appels_partenaire"] for m in mesures),
        "doublons_recus": sum(m["doublons_recus"] for m in mesures),
        "max_appels_par_dossier": max(m["max_appels_par_dossier"] for m in mesures),
        "trace_max": max(m["trace_max"] for m in mesures),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "bornes": kaldera.bornes(),
    }
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / "mesures.json").write_text(json.dumps({"synthese": synthese, "scenarios": mesures}, ensure_ascii=False,
                                                    indent=2), encoding="utf-8")
    lignes = ["# Épreuve du réel : mesures", "",
              "Rapport généré par `outils/mesurer_epreuve.py` contre le partenaire simulé fourni. Ne pas modifier à la main.",
              "", f"- date : {synthese['date']}",
              f"- demandes conformes à `attendu` : {synthese['demandes_conformes']}/{synthese['demandes']} "
              f"({synthese['scenarios']} scénarios)",
              f"- appels reçus par le partenaire : {synthese['appels_partenaire']} ; doublons reçus : "
              f"{synthese['doublons_recus']} ; au plus {synthese['max_appels_par_dossier']} appel par dossier",
              f"- trace la plus longue : {synthese['trace_max']} étapes", "",
              "| Scénario | Partenaire | Conformes | Appels | Échecs | Raisons | Trace max | Durée du lot (s) |",
              "|---|---|---|---|---|---|---|---|"]
    for m in mesures:
        duree = (f"{m['duree_lot_min_s']} à {m['duree_lot_max_s']} ({m['rejeux']} rejeux)" if "rejeux" in m
                 else str(m["duree_lot_s"]))
        lignes.append(f"| {m['id']} | {m['partenaire'].get('mode')} | {m['conformes']}/{m['demandes']} | "
                      f"{m['appels_partenaire']} | {m['echecs']} | {', '.join(m['raisons']) or '·'} | "
                      f"{m['trace_max']} | {duree} |")
    (SORTIE / "rapport.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(json.dumps(synthese, ensure_ascii=False))


if __name__ == "__main__":
    main()
