"""Mesure des deux bornes tirées de l'expérience : la réserve de la fiche et le délai minimal d'un appel au partenaire.

1. Dépassement après l'échéance. Le partenaire simulé répond en 5 s : c'est l'échéance de la demande qui arrête
   l'appel. On mesure le temps écoulé entre l'échéance et la fiche rendue, seul et à trois demandes simultanées, puis
   sur le chemin des pièces (une lecture qui consomme tout le temps restant). La réserve de la fiche doit couvrir ce
   dépassement.
2. Durée d'un appel réussi. Le partenaire simulé répond normalement : on mesure la ligne de trace de l'agent
   Anti-fraude (filtre, requête HTTP, validation), seul et en lot de sept. En dessous de cette durée, un appel n'a pas
   le temps d'aboutir.

Les règles qui transforment ces mesures en valeurs sont dans src/kaldera/bornes.py ; un test vérifie que les valeurs
de Bornes en découlent. Lancement, depuis la racine du dépôt :
    .venv\\Scripts\\python.exe outils\\mesurer_bornes.py
Sorties (générées, ne pas modifier à la main) : evaluation/bornes/mesures.json et evaluation/bornes/rapport.md.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

RACINE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RACINE / "src"), str(RACINE), str(RACINE / "outils")]
SORTIE = RACINE / "evaluation" / "bornes"
REFERENCES_AF = [f"KAL-26-020{i}" for i in range(1, 8)]  # AF-01 à 07 : un indicateur, donc un appel
ESSAIS_SEUL, TOURS_A_TROIS, ESSAIS_LECTURE, ESSAIS_APPEL, LOTS_DE_SEPT = 20, 10, 20, 30, 5
BUDGET_COURT_S = 0.4


def demandes() -> dict[str, dict[str, Any]]:
    lignes = (RACINE / "eval" / "scenarios.jsonl").read_text(encoding="utf-8").splitlines()
    return {d["reference"]: d for ligne in lignes if ligne.strip() for d in json.loads(ligne)["demandes"]}


def preparer(pilote: httpx.Client, **reglage: Any) -> None:
    pilote.post("/_sim/reset").raise_for_status()
    pilote.post("/_sim/mode", json=reglage).raise_for_status()


def depassement_partenaire(url: str, demande: dict[str, Any]) -> float | None:
    """Une demande dont l'échéance tombe pendant l'appel : temps entre l'échéance et la fiche rendue."""
    from kaldera.a2a.client import partenaire_a2a
    from kaldera.coordination import traiter

    limite = time.monotonic() + BUDGET_COURT_S
    fiche = traiter(demande, consulter=partenaire_a2a(url), limite=limite)
    fin = time.monotonic()
    raisons = [x.get("raison") for x in fiche["trace"] if x["agent"] == "antifraude"]
    return fin - limite if raisons == ["delai_depasse"] else None  # mesure gardée seulement si l'échéance a coupé


def depassement_lecture() -> float:
    """Chemin des pièces : la lecture consomme tout le temps restant ; temps entre l'échéance et la fiche rendue."""
    from kaldera.bornes import Bornes
    from kaldera.extraction.dossier import traiter_dossier

    budget = Bornes(duree_max_s=0.5, reserve_fiche_s=0.0)  # échéance = arrivée + 0,5 s

    def lecture_qui_va_jusqu_a_l_echeance(*_args: Any, delai_s: float | None = None) -> Any:
        time.sleep(delai_s or 0)
        raise TimeoutError("délai épuisé")

    debut = time.monotonic()
    traiter_dossier(RACINE / "dossiers" / "KAL-26-0101", lecture_qui_va_jusqu_a_l_echeance, bornes=budget)
    return time.monotonic() - debut - budget.duree_max_s


def appels_reussis(url: str, lot: list[dict[str, Any]]) -> list[float]:
    import kaldera

    fiches = kaldera.traiter_lot(lot, partenaire_url=url)["fiches"]
    return [x["duree_ms"] / 1000 for f in fiches for x in f["trace"]
            if x["agent"] == "antifraude" and x["statut"] == "ok" and x["appel_externe"]]


def main() -> None:
    from kaldera.bornes import BORNES, delai_min_depuis_mesure, reserve_depuis_mesure
    from mesurer_epreuve import demarrer_partenaire

    tout = demandes()
    url, serveur = demarrer_partenaire()
    pilote = httpx.Client(base_url=url, timeout=15)

    depassements: list[float] = []
    for i in range(ESSAIS_SEUL):
        preparer(pilote, mode="lent", delai_s=5.0)
        mesure = depassement_partenaire(url, tout[REFERENCES_AF[i % 7]])
        if mesure is not None:
            depassements.append(mesure)
    for _ in range(TOURS_A_TROIS):
        preparer(pilote, mode="lent", delai_s=5.0)
        with ThreadPoolExecutor(max_workers=3) as executeur:
            for mesure in executeur.map(lambda r: depassement_partenaire(url, tout[r]), REFERENCES_AF[:3]):
                if mesure is not None:
                    depassements.append(mesure)
    depassements_lecture = [depassement_lecture() for _ in range(ESSAIS_LECTURE)]

    appels: list[float] = []
    for i in range(ESSAIS_APPEL):
        preparer(pilote, mode="normal")
        appels += appels_reussis(url, [tout[REFERENCES_AF[i % 7]]])
    for _ in range(LOTS_DE_SEPT):
        preparer(pilote, mode="normal")
        appels += appels_reussis(url, [tout[r] for r in REFERENCES_AF])
    serveur.should_exit = True

    tous_depassements = depassements + depassements_lecture
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                            cwd=RACINE).stdout.strip()
    mesures = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "commit": commit,
        "essais_depassement": len(tous_depassements),
        "depassement_max_s": round(max(tous_depassements), 4),
        "depassement_median_s": round(statistics.median(tous_depassements), 4),
        "depassement_partenaire_max_s": round(max(depassements), 4),
        "depassement_lecture_max_s": round(max(depassements_lecture), 4),
        "essais_appel": len(appels),
        "appel_reussi_max_s": round(max(appels), 4),
        "appel_reussi_median_s": round(statistics.median(appels), 4),
        "valeurs": {"reserve_fiche_s": reserve_depuis_mesure(round(max(tous_depassements), 4)),
                    "delai_partenaire_min_s": delai_min_depuis_mesure(round(max(appels), 4))},
        "valeurs_en_vigueur": {"reserve_fiche_s": BORNES.reserve_fiche_s,
                               "delai_partenaire_min_s": BORNES.delai_partenaire_min_s},
    }
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / "mesures.json").write_text(json.dumps(mesures, ensure_ascii=False, indent=2), encoding="utf-8")
    rapport = [
        "# Bornes tirées de la mesure", "",
        "Rapport généré par `outils/mesurer_bornes.py` contre le partenaire simulé fourni. Ne pas modifier à la main.", "",
        f"- date : {mesures['date']} ; commit : {commit}", "",
        "| Mesure | Essais | Médiane (s) | Maximum (s) | Règle (src/kaldera/bornes.py) | Valeur tirée |",
        "|---|---|---|---|---|---|",
        f"| Dépassement après l'échéance (partenaire seul, à trois, et chemin des pièces) | "
        f"{mesures['essais_depassement']} | {mesures['depassement_median_s']} | {mesures['depassement_max_s']} | "
        f"dix fois le maximum, arrondi au dixième supérieur, 0,1 s au moins | "
        f"reserve_fiche_s = {mesures['valeurs']['reserve_fiche_s']} |",
        f"| Durée d'un appel réussi au partenaire (seul et en lot de sept) | {mesures['essais_appel']} | "
        f"{mesures['appel_reussi_median_s']} | {mesures['appel_reussi_max_s']} | le maximum, arrondi au vingtième "
        f"supérieur, 0,05 s au moins | delai_partenaire_min_s = {mesures['valeurs']['delai_partenaire_min_s']} |",
        "",
        f"Détail du dépassement : partenaire {mesures['depassement_partenaire_max_s']} s au plus, chemin des pièces "
        f"{mesures['depassement_lecture_max_s']} s au plus.",
        "",
        "Limite : mesuré sur le partenaire simulé et sur cette machine. Contre le vrai partenaire (réponse garantie en "
        "2 s), la durée d'un appel réussi sera plus longue : relancer la mesure et appliquer la même règle.",
    ]
    (SORTIE / "rapport.md").write_text("\n".join(rapport) + "\n", encoding="utf-8")
    print(json.dumps(mesures, ensure_ascii=False))


if __name__ == "__main__":
    main()
