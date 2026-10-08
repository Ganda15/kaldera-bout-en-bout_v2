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
from ..metriques import calculer_metriques_lecture
from .lecteurs import Appeler, ExtractionImpossible, Reponse

PIECE = re.compile(r"^(?:piece-)?(\d+)-(facture|photo|depot_plainte)\.png$")


def lister_images(dossier: Path) -> list[tuple[str, Path]]:
    """Les images d'un dossier, dans l'ordre de leur numéro, avec leur type."""
    trouves = []
    for chemin in dossier.glob("*.png"):
        correspondance = PIECE.match(chemin.name)
        if correspondance:
            trouves.append((int(correspondance.group(1)), correspondance.group(2), chemin))
    return [(type_piece, chemin) for _, type_piece, chemin in sorted(trouves)]


def fichiers_non_reconnus(dossier: Path) -> list[str]:
    """Les fichiers que le système ne sait pas traiter : signalés, jamais ignorés en silence."""
    attendus_a_la_racine = {"contrat.pdf", "declaration.json"}
    inconnus = [f.name for f in dossier.iterdir()
                if f.is_file() and f.name not in attendus_a_la_racine and not PIECE.match(f.name)]
    if (dossier / "depots").is_dir():
        inconnus += [f"depots/{f.name}" for f in (dossier / "depots").iterdir()
                     if f.is_file() and not PIECE.match(f.name)]
    return sorted(inconnus)


def traiter_dossier(dossier: Path, appeler: Appeler, *, consulter: Callable[..., AvisFraude] = partenaire_bouchon,
                    registre: RegistreAppels | None = None) -> dict[str, Any]:
    """Rend {"demande": JSON § 3 extrait, "lecture": une ligne par pièce lue, "fiche": fiche de décision}.

    Aucune erreur brute (exigence N1) : un dossier inexploitable donne une escalade motivée vers un gestionnaire ;
    une pièce illisible suit, elle, la demande de complément du § 5.
    """
    try:
        declaration = json.loads((dossier / "declaration.json").read_text(encoding="utf-8"))
        reference = declaration["reference"]
    except (OSError, ValueError, KeyError, TypeError):
        motif = "Formulaire de déclaration absent ou illisible : reprise manuelle"
        return {"demande": None, "lecture": [], "fiche": escalade_directe(dossier.name, motif)}
    inconnus = fichiers_non_reconnus(dossier)
    if inconnus:
        motif = f"Fichier non pris en charge ({', '.join(inconnus)}) : reprise manuelle"
        return {"demande": None, "lecture": [], "fiche": escalade_directe(reference, motif)}
    if not (dossier / "contrat.pdf").is_file():
        motif = "Contrat absent du dossier : reprise manuelle"
        return {"demande": None, "lecture": [], "fiche": escalade_directe(reference, motif)}
    lecture: list[dict[str, Any]] = []
    appels, jetons = [0], [0, 0]

    def compte(*args: Any, **kwargs: Any) -> Any:
        appels[0] += 1
        reponse = appeler(*args, **kwargs)
        if isinstance(reponse, Reponse):
            jetons[0] += reponse.jetons_entree
            jetons[1] += reponse.jetons_sortie
        return reponse

    def lire(agent: str, chemin: Path, fonction: Callable[..., Any], *args: Any) -> Any:
        avant, jetons_avant, debut = appels[0], list(jetons), perf_counter()
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
            ligne["jetons_entree"] = jetons[0] - jetons_avant[0]
            ligne["jetons_sortie"] = jetons[1] - jetons_avant[1]

    try:
        contrat = lire("lecteur_contrat", dossier / "contrat.pdf", lecteurs.lire_contrat)
        if contrat["numero"] != declaration["numero_contrat"]:
            motif = (f"Contrat lu ({contrat['numero']}) différent du contrat déclaré "
                     f"({declaration['numero_contrat']}) : reprise manuelle")
            return {"demande": None, "lecture": lecture, "fiche": escalade_directe(reference, motif)}
        pieces = [lire("lecteur_pieces", chemin, lecteurs.lire_piece, type_piece)
                  for type_piece, chemin in lister_images(dossier)]
        depots = [lire("lecteur_pieces", chemin, lecteurs.lire_piece, type_piece)
                  for type_piece, chemin in lister_images(dossier / "depots")]
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
    print(json.dumps({"metriques_lecture": calculer_metriques_lecture([resultat["lecture"]])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
