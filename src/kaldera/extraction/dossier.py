"""Étape E3 : traiter un dossier de pièces non structurées, de la lecture jusqu'à la fiche de décision.

Un dossier contient le formulaire de l'assuré (`declaration.json`), le contrat (`contrat.pdf`), les pièces jointes
(`piece-<n>-<type>.png`, le type étant le créneau de dépôt choisi par l'assuré) et ses dépôts (`depots/<n>-<type>.png`).

0. Contrôle du dossier, avant toute lecture : formulaire validé par un schéma, fichiers reconnus, contrat présent.
1. Lecture : les agents de lecture produisent les données de la spec § 3. Elle est tracée à part (`lecture`).
2. Décision : la chaîne du chantier 1 (`coordination.traiter`), plus l'agent Documents et cohérence (§ 5). Son appel
   au modèle part dès l'arrivée, avec les images nettes, en parallèle de la lecture ; la Coordination s'en sert après
   un contrôle des pièces complet.
Un seul budget de 10 s (§ 12) couvre les trois : il commence à l'arrivée du dossier, chaque appel au modèle reçoit
le temps restant comme délai, et la Coordination continue la même limite au lieu d'en ouvrir une nouvelle.
Une lecture impossible (modèle en panne, réponse hors schéma) ou un contrat qui ne correspond pas à la déclaration
donnent une escalade motivée vers un gestionnaire : jamais une décision prise sur des données douteuses.

Lancement réel, depuis la racine du dépôt (la clé doit être dans .env) :
    .venv\\Scripts\\python.exe -m kaldera.extraction.dossier dossiers\\KAL-26-0101
Avec le vrai partenaire (lancé à part : python -m external_agent), adresse et jeton lus dans .env :
    .venv\\Scripts\\python.exe -m kaldera.extraction.dossier dossiers\\KAL-26-0201 --partenaire
Sans --partenaire, le partenaire est le bouchon du chantier 1, qui répond toujours « indisponible ».
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
import re
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturDepasse
from pathlib import Path
from time import monotonic, perf_counter
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..agents import coherence as agent_coherence
from ..agents.antifraude import AvisFraude, partenaire_bouchon
from ..agents.coherence import ResultatCoherence
from ..bornes import BORNES, Bornes
from ..coordination import RegistreAppels, escalade_directe, traiter
from . import lecteurs
from ..metriques import calculer_metriques_lecture
from .lecteurs import Appeler, ExtractionImpossible, Reponse

PIECE = re.compile(r"^(?:piece-)?(\d+)-(facture|photo|depot_plainte)\.png$")


class _Assure(BaseModel):
    code_postal: str  # seul champ de l'assuré lu par la chaîne ; les autres restent dans la demande, jamais transmis


class _Sinistre(BaseModel):
    model_config = ConfigDict(strict=True)
    type: str
    date_survenance: date
    date_declaration: date
    montant_declare: Annotated[float, Field(ge=0)]


class _Historique(BaseModel):
    model_config = ConfigDict(strict=True)
    sinistres_12_mois: Annotated[int, Field(ge=0)]


class Declaration(BaseModel):
    """Ce que la chaîne lit dans le formulaire : vérifié avant toute lecture, pour qu'aucun champ manquant ne
    provoque une erreur brute après des appels au modèle déjà payés."""

    reference: str
    numero_contrat: str
    assure: _Assure
    sinistre: _Sinistre
    historique: _Historique


def lire_declaration(dossier: Path) -> tuple[dict[str, Any] | None, str, str | None]:
    """Rend (formulaire, référence, motif d'escalade ou None)."""
    try:
        texte = (dossier / "declaration.json").read_text(encoding="utf-8")
        brut = json.loads(texte)
    except (OSError, ValueError):
        return None, dossier.name, "Formulaire de déclaration absent ou illisible : reprise manuelle"
    reference = brut.get("reference") if isinstance(brut, dict) and isinstance(brut.get("reference"), str) \
        else dossier.name
    try:
        Declaration.model_validate_json(texte)
    except ValidationError as erreur:
        champs = sorted({str(e["loc"][0]) for e in erreur.errors() if e["loc"]}) or ["formulaire"]
        return None, reference, (f"Formulaire de déclaration incomplet ou invalide ({', '.join(champs)}) : "
                                 "reprise manuelle")
    return brut, reference, None


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
                    registre: RegistreAppels | None = None, bornes: Bornes = BORNES) -> dict[str, Any]:
    """Rend {"demande": JSON § 3 extrait, "lecture": une ligne par pièce lue, "fiche": fiche de décision}.

    Aucune erreur brute (exigence N1) : un dossier inexploitable donne une escalade motivée vers un gestionnaire ;
    une pièce illisible suit, elle, la demande de complément du § 5.
    """
    limite = monotonic() + bornes.duree_max_s - bornes.reserve_fiche_s  # le budget commence à l'arrivée du dossier
    declaration, reference, motif = lire_declaration(dossier)
    if motif:
        return {"demande": None, "lecture": [], "fiche": escalade_directe(reference, motif)}
    inconnus = fichiers_non_reconnus(dossier)
    if inconnus:
        motif = f"Fichier non pris en charge ({', '.join(inconnus)}) : reprise manuelle"
        return {"demande": None, "lecture": [], "fiche": escalade_directe(reference, motif)}
    if not (dossier / "contrat.pdf").is_file():
        motif = "Contrat absent du dossier : reprise manuelle"
        return {"demande": None, "lecture": [], "fiche": escalade_directe(reference, motif)}
    lecture: list[dict[str, Any]] = []
    coherence = _CoherenceAnticipee(dossier, declaration["sinistre"], appeler, limite, bornes, lecture)
    try:
        return _lire_et_decider(dossier, declaration, reference, appeler, lecture, coherence, consulter=consulter,
                                registre=registre, bornes=bornes, limite=limite)
    finally:
        coherence.clore()


def _lire_et_decider(dossier: Path, declaration: dict[str, Any], reference: str, appeler: Appeler,
                     lecture: list[dict[str, Any]], coherence: _CoherenceAnticipee, *,
                     consulter: Callable[..., AvisFraude], registre: RegistreAppels | None, bornes: Bornes,
                     limite: float) -> dict[str, Any]:
    appels, jetons = [0], [0, 0]

    def compte(*args: Any) -> Any:
        restant = limite - monotonic()
        if restant <= 0:
            raise ExtractionImpossible(f"délai de {bornes.duree_max_s:g} s dépassé pendant la lecture", "delai_depasse")
        appels[0] += 1
        try:
            reponse = appeler(*args, delai_s=restant)
        except Exception as erreur:
            if monotonic() >= limite:  # l'appel a été abandonné faute de temps
                raise ExtractionImpossible(f"délai de {bornes.duree_max_s:g} s dépassé pendant la lecture",
                                           "delai_depasse") from erreur
            raise
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
        lues = [(chemin, lire("lecteur_pieces", chemin, lecteurs.lire_piece, type_piece))
                for type_piece, chemin in lister_images(dossier)]
        deposees = [(chemin, lire("lecteur_pieces", chemin, lecteurs.lire_piece, type_piece))
                    for type_piece, chemin in lister_images(dossier / "depots")]
    except ExtractionImpossible as erreur:
        motif = f"Lecture des pièces impossible ({erreur}) : reprise manuelle"
        return {"demande": None, "lecture": lecture, "fiche": escalade_directe(reference, motif)}

    demande = {"reference": reference, "assure": declaration["assure"], "contrat": contrat,
               "sinistre": declaration["sinistre"], "pieces": [piece for _, piece in lues],
               "historique": declaration["historique"],
               "espace_assure": {"depots": [piece for _, piece in deposees]}}
    return {"demande": demande, "lecture": lecture,
            "fiche": traiter(demande, consulter=consulter, registre=registre, bornes=bornes, limite=limite,
                             coherence=coherence.verifier_coherence)}


def _nette(chemin: Path) -> bool:
    try:
        return lecteurs.nettete(chemin) >= lecteurs.SEUIL_NETTETE
    except OSError:  # image qu'on ne sait pas ouvrir : illisible, elle suit le complément
        return False


class _CoherenceAnticipee:
    """L'agent Documents et cohérence, côté dossier. Son interprétation ne dépend que du formulaire et des images :
    elle part dès l'arrivée, en parallèle de la lecture du contrat et des factures. Mesuré le 08/10 (essai 2) : 4 s
    en moyenne, après 4 s de lecture ; en série, 2 dossiers sur 42 dépassaient le budget de 10 s.

    La Coordination décide quand s'en servir : après un contrôle des pièces complet. Un appel dont le résultat ne sert
    pas (demande refusée avant, lecture impossible) reste dans la lecture, avec son coût : il a été payé.
    """

    def __init__(self, dossier: Path, sinistre: dict[str, Any], appeler: Appeler, limite: float, bornes: Bornes,
                 lecture: list[dict[str, Any]]) -> None:
        self.nettes = [(chemin.relative_to(dossier).as_posix(), type_piece, chemin)
                       for type_piece, chemin in lister_images(dossier) + lister_images(dossier / "depots")
                       if _nette(chemin)]  # netteté mesurée en code ; une image floue suit le complément
        self.sinistre, self.appeler, self.limite, self.bornes, self.lecture = sinistre, appeler, limite, bornes, lecture
        self.jetons, self.duree_s, self.utilise = [0, 0], 0.0, False
        self.futur = None
        if self.nettes:
            executeur = ThreadPoolExecutor(max_workers=1)
            self.futur = executeur.submit(self._interpreter, sinistre)
            executeur.shutdown(wait=False)  # un seul appel ; le fil s'arrête avec lui

    def _compte(self, *args: Any) -> Any:
        """Le même budget que la lecture, et des jetons comptés à part : la lecture tourne en même temps."""
        restant = self.limite - monotonic()
        delai = f"délai de {self.bornes.duree_max_s:g} s dépassé pendant la cohérence"
        if restant <= 0:
            raise ExtractionImpossible(delai, "delai_depasse")
        try:
            reponse = self.appeler(*args, delai_s=restant)
        except Exception as erreur:
            if monotonic() >= self.limite:
                raise ExtractionImpossible(delai, "delai_depasse") from erreur
            raise
        if isinstance(reponse, Reponse):
            self.jetons[0] += reponse.jetons_entree
            self.jetons[1] += reponse.jetons_sortie
        return reponse

    def _interpreter(self, sinistre: dict[str, Any]) -> ResultatCoherence:
        debut = perf_counter()
        try:
            documents = [(fichier, type_piece, chemin.read_bytes()) for fichier, type_piece, chemin in self.nettes]
            return agent_coherence.verifier_coherence(sinistre, documents, self._compte)
        finally:
            self.duree_s = perf_counter() - debut

    def _attendre(self) -> ResultatCoherence:
        if self.futur is None:
            return ResultatCoherence("non_effectue", raison="aucune_piece_nette", statut="indisponible")
        try:
            return self.futur.result(timeout=max(0.0, self.limite - monotonic()))
        except FuturDepasse:
            return ResultatCoherence("non_effectue", raison="delai_depasse", statut="indisponible", appel_externe=True)

    def _noter(self, resultat: ResultatCoherence, statut: str, attente_s: float) -> None:
        self.lecture.append({"agent": "coherence", "fichier": ", ".join(f for f, _, _ in self.nettes),
                             "statut": statut, "duree_ms": round(self.duree_s * 1000, 2),
                             "attente_ms": round(attente_s * 1000, 2), "appel_modele": self.futur is not None,
                             "jetons_entree": self.jetons[0], "jetons_sortie": self.jetons[1],
                             "verdict": resultat.verdict})

    def verifier_coherence(self, sinistre: dict[str, Any]) -> ResultatCoherence:
        """Ce que la Coordination appelle : le résultat de l'appel parti à l'arrivée, attendu dans le budget restant."""
        self.utilise, debut = True, perf_counter()
        resultat = self._attendre() if sinistre == self.sinistre else self._interpreter(sinistre)
        self._noter(resultat, "echec" if resultat.verdict == "non_effectue" else "ok", perf_counter() - debut)
        return resultat

    def clore(self) -> None:
        """Demande conclue sans la cohérence : l'appel parti à l'arrivée est attendu (dans le budget) et noté."""
        if self.futur is not None and not self.utilise:
            debut = perf_counter()
            self._noter(self._attendre(), "non_utilise", perf_counter() - debut)


def options(argv: list[str], fichier_env: Path | None = None) -> tuple[Path, str | None]:
    """(dossier, adresse du partenaire ou None). `--partenaire` sans valeur prend PARTENAIRE_URL de l'environnement,
    sinon du fichier .env ; le jeton PARTENAIRE_JETON est chargé de la même façon s'il manque (jamais affiché)."""
    from .modele import RACINE, _lire_env

    parser = argparse.ArgumentParser(description="Traite un dossier de pièces jusqu'à la fiche de décision.")
    parser.add_argument("dossier", type=Path)
    parser.add_argument("--partenaire", nargs="?", const="", default=None,
                        help="adresse du partenaire anti-fraude ; sans valeur : PARTENAIRE_URL (.env)")
    args = parser.parse_args(argv)
    if args.partenaire is None:
        return args.dossier, None
    fichier = _lire_env(fichier_env or RACINE / ".env")
    if not os.environ.get("PARTENAIRE_JETON") and fichier.get("PARTENAIRE_JETON"):
        os.environ["PARTENAIRE_JETON"] = fichier["PARTENAIRE_JETON"]
    adresse = args.partenaire or os.environ.get("PARTENAIRE_URL") or fichier.get("PARTENAIRE_URL")
    # Sous Windows, « localhost » est d'abord essayé en IPv6 alors que le partenaire n'écoute que 127.0.0.1 :
    # mesuré le 08/10, 2,1 s par requête au lieu de 0,03 s, pris sur les 3 s de l'appel. Même machine, sans détour.
    return args.dossier, adresse.replace("://localhost", "://127.0.0.1", 1) if adresse else adresse


def consulter_pour(url: str | None) -> Callable[..., AvisFraude]:
    """Le vrai client A2A si une adresse est donnée, sinon le bouchon du chantier 1."""
    from ..a2a.client import partenaire_a2a

    return partenaire_a2a(url) if url else partenaire_bouchon


def main() -> None:
    from . import modele

    dossier, url = options(sys.argv[1:])
    config = modele.configuration()
    appeler = lecteurs.appel_modele(modele.client(config), config.deploiement)
    print(json.dumps({"partenaire": url or "bouchon (aucun appel réseau)"}, ensure_ascii=False))
    resultat = traiter_dossier(dossier, appeler, consulter=consulter_pour(url))
    for ligne in resultat["lecture"]:
        print(json.dumps(ligne, ensure_ascii=False))
    fiche = {k: v for k, v in resultat["fiche"].items() if k != "trace"}
    print(json.dumps(fiche, ensure_ascii=False))
    print(json.dumps({"metriques_lecture": calculer_metriques_lecture([resultat["lecture"]])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
