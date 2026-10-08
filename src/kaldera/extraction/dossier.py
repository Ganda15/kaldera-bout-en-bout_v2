"""Étape E3 : traiter un dossier de pièces non structurées, de la lecture jusqu'à la fiche de décision.

Un dossier contient le formulaire de l'assuré (`declaration.json`), le contrat (`contrat.pdf`), les pièces jointes
(`piece-<n>-<type>.png`, le type étant le créneau de dépôt choisi par l'assuré) et ses dépôts (`depots/<n>-<type>.png`).

1. Lecture : les agents de lecture produisent les données de la spec § 3. Elle est tracée à part (`lecture`), car elle
   précède la chaîne de décision et ses 10 secondes (un appel au modèle peut à lui seul en durer davantage).
2. Décision : la chaîne du chantier 1 (`coordination.traiter`), inchangée.
Une lecture impossible (modèle en panne, réponse hors schéma) ou un contrat qui ne correspond pas à la déclaration
donnent une escalade motivée vers un gestionnaire : jamais une décision prise sur des données douteuses.

Lancement réel, depuis la racine du dépôt (la clé doit être dans .env) :
    .venv\\Scripts\\python.exe -m kaldera.extraction.dossier dossiers\\KAL-26-0101
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any

from ..agents.antifraude import AvisFraude, partenaire_bouchon
from ..coordination import RegistreAppels, escalade_directe, traiter
from . import lecteurs
from .lecteurs import Appeler, ExtractionImpossible

PIECE = re.compile(r"^(?:piece-)?(\d+)-(facture|photo|depot_plainte)\.png$")


def _fichiers(dossier: Path) -> list[tuple[str, Path]]:
    """Les images d'un dossier, dans l'ordre de leur numéro, avec leur type."""
    trouves = []
    for chemin in dossier.glob("*.png"):
        correspondance = PIECE.match(chemin.name)
        if correspondance:
            trouves.append((int(correspondance.group(1)), correspondance.group(2), chemin))
    return [(type_piece, chemin) for _, type_piece, chemin in sorted(trouves)]


def traiter_dossier(dossier: Path, appeler: Appeler, *, consulter: Callable[..., AvisFraude] = partenaire_bouchon,
                    registre: RegistreAppels | None = None) -> dict[str, Any]:
    """Rend {"demande": JSON § 3 extrait, "lecture": une ligne par pièce lue, "fiche": fiche de décision}."""
    declaration = json.loads((dossier / "declaration.json").read_text(encoding="utf-8"))
    reference = declaration["reference"]
    lecture: list[dict[str, Any]] = []
    appels = [0]

    def compte(*args: Any, **kwargs: Any) -> Any:
        appels[0] += 1
        return appeler(*args, **kwargs)

    def lire(agent: str, chemin: Path, fonction: Callable[..., Any], *args: Any) -> Any:
        avant, debut = appels[0], perf_counter()
        ligne = {"agent": agent, "fichier": chemin.relative_to(dossier).as_posix(), "statut": "ok"}
        lecture.append(ligne)
        try:
            return fonction(chemin, *args, compte)
        except ExtractionImpossible:
            ligne["statut"] = "echec"
            raise
        finally:
            ligne["duree_ms"] = round((perf_counter() - debut) * 1000, 2)
            ligne["appel_modele"] = appels[0] > avant

    try:
        contrat = lire("lecteur_contrat", dossier / "contrat.pdf", lecteurs.lire_contrat)
        if contrat["numero"] != declaration["numero_contrat"]:
            motif = (f"Contrat lu ({contrat['numero']}) différent du contrat déclaré "
                     f"({declaration['numero_contrat']}) : reprise manuelle")
            return {"demande": None, "lecture": lecture, "fiche": escalade_directe(reference, motif)}
        pieces = [lire("lecteur_pieces", chemin, lecteurs.lire_piece, type_piece)
                  for type_piece, chemin in _fichiers(dossier)]
        depots = [lire("lecteur_pieces", chemin, lecteurs.lire_piece, type_piece)
                  for type_piece, chemin in _fichiers(dossier / "depots")]
    except ExtractionImpossible as erreur:
        motif = f"Lecture des pièces impossible ({erreur}) : reprise manuelle"
        return {"demande": None, "lecture": lecture, "fiche": escalade_directe(reference, motif)}

    demande = {"reference": reference, "assure": declaration["assure"], "contrat": contrat,
               "sinistre": declaration["sinistre"], "pieces": pieces, "historique": declaration["historique"],
               "espace_assure": {"depots": depots}}
    return {"demande": demande, "lecture": lecture,
            "fiche": traiter(demande, consulter=consulter, registre=registre)}


def main() -> None:
    from . import modele

    config = modele.configuration()
    appeler = lecteurs.appel_modele(modele.client(config), config.deploiement)
    resultat = traiter_dossier(Path(sys.argv[1]), appeler)
    for ligne in resultat["lecture"]:
        print(json.dumps(ligne, ensure_ascii=False))
    fiche = {k: v for k, v in resultat["fiche"].items() if k != "trace"}
    print(json.dumps(fiche, ensure_ascii=False))


if __name__ == "__main__":
    main()
