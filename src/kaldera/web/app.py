"""Poste du gestionnaire (prototype) : lire un dossier, faire confirmer ce qui a été lu, décider, piloter le partenaire.

Couche d'interface hors du moteur : elle n'appelle que des fonctions publiques (lire_dossier, traiter, le client A2A).
Le serveur relit lui-même les fichiers ; le navigateur ne peut que corriger une valeur lue, et chaque correction est
revérifiée par les mêmes schémas stricts que la lecture. Une pause humaine sépare la lecture de la décision : la
lecture a son budget de 10 s, la décision le sien, à partir de la confirmation.

Lancement : python -m kaldera.web (adresse locale http://127.0.0.1:8200).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from collections.abc import Callable
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from ..a2a.filtre import RequeteNonConforme, construire_donnees
from ..coordination import escalade_directe, traiter
from ..extraction.dossier import consulter_pour, lire_dossier, options
from ..extraction.lecteurs import ContratLu, FactureLue
from ..metriques import calculer_metriques
from ..regles import jours_entre

RACINE = Path(__file__).resolve().parents[3]
DOSSIERS = RACINE / "dossiers"
PAGE = Path(__file__).with_name("page.html")
JAMAIS_ENVOYE = ["nom", "prénom", "e-mail", "téléphone", "adresse", "code postal complet", "IBAN",
                 "identifiant client", "numéro de contrat", "description", "pièces"]


class ContratConfirme(BaseModel):
    model_config = ConfigDict(extra="forbid")
    numero: str = Field(pattern=r"^CTR-\d{6}$")
    formule: Literal["essentiel", "confort", "premium"]
    date_souscription: date
    statut: Literal["actif", "suspendu", "resilie"]
    cotisations_a_jour: bool


class PieceConfirmee(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lisible: bool
    montant: float | None = Field(default=None, gt=0)


class Confirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session: str
    contrat: ContratConfirme
    pieces: list[PieceConfirmee]
    depots: list[PieceConfirmee]


class Lecture(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dossier: str
    mode: Literal["modele", "reference"] = "reference"


class Reglage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["normal", "lent", "invalide", "panne", "reset"]
    variante: str | None = None
    delai_s: float | None = None


def appel_reference() -> Callable[..., Any]:
    """Lecture de démonstration sans modèle : les valeurs de référence de dossiers/verite.json, affichées comme telles."""
    verite = json.loads((DOSSIERS / "verite.json").read_text(encoding="utf-8"))
    contrats = {v["contrat"]["numero"]: v["contrat"] for v in verite.values()}
    factures = {hashlib.sha256((DOSSIERS / ref / nom).read_bytes()).hexdigest(): f
                for ref, v in verite.items() for nom, f in v["fichiers"].items() if f["type"] == "facture"}

    def appeler(consigne: str, schema: type, image_png: bytes | None = None, *, delai_s: float | None = None) -> Any:
        if schema is ContratLu:
            return ContratLu(**contrats[re.search(r"CTR-\d{6}", consigne).group(0)])
        vraie = factures[hashlib.sha256(image_png).hexdigest()]
        return FactureLue(lisible=True, montant_total_ttc=vraie["montant"])
    return appeler


def appel_modele_reel() -> Callable[..., Any]:
    from ..extraction import lecteurs, modele

    config = modele.configuration()
    return lecteurs.appel_modele(modele.client(config), config.deploiement)


def creer_app(partenaire_url: str | None = "auto") -> FastAPI:
    """partenaire_url : "auto" lit .env (comme --partenaire) ; None garde le bouchon (tests)."""
    app = FastAPI(title="Kaldera · poste du gestionnaire (prototype)")
    sessions: dict[str, dict[str, Any]] = {}
    url = options([".", "--partenaire"])[1] if partenaire_url == "auto" else partenaire_url

    def dossier_connu(nom: str) -> Path:
        if nom not in {p.name for p in DOSSIERS.iterdir() if p.is_dir()}:
            raise HTTPException(404, "dossier inconnu")
        return DOSSIERS / nom

    @app.get("/", response_class=HTMLResponse)
    def page() -> str:
        return PAGE.read_text(encoding="utf-8")

    @app.get("/api/dossiers")
    def dossiers() -> list[dict[str, Any]]:
        resultat = []
        for chemin in sorted(p for p in DOSSIERS.iterdir() if p.is_dir()):
            declaration = json.loads((chemin / "declaration.json").read_text(encoding="utf-8"))
            sinistre = declaration["sinistre"]
            resultat.append({"dossier": chemin.name, "type": sinistre["type"], "montant": sinistre["montant_declare"]})
        return resultat

    @app.post("/api/lire")
    def lire(demande: Lecture) -> dict[str, Any]:
        chemin = dossier_connu(demande.dossier)
        appeler = appel_modele_reel() if demande.mode == "modele" else appel_reference()
        debut = perf_counter()
        lu = lire_dossier(chemin, appeler)
        duree_ms = round((perf_counter() - debut) * 1000, 1)
        if lu["fiche"] is not None:  # escalade avant toute décision : rien à confirmer
            return {"session": None, "lecture": lu["lecture"], "duree_lecture_ms": duree_ms, "fiche": lu["fiche"]}
        session = uuid.uuid4().hex
        sessions[session] = {"demande": lu["demande"], "duree_lecture_ms": duree_ms}
        d = lu["demande"]
        appels = {ligne["fichier"]: ligne["appel_modele"] for ligne in lu["lecture"]}
        return {"session": session, "mode": demande.mode, "lecture": lu["lecture"], "duree_lecture_ms": duree_ms,
                "contrat": d["contrat"], "pieces": d["pieces"], "depots": d["espace_assure"]["depots"],
                "fichiers": {"pieces": [ligne["fichier"] for ligne in lu["lecture"] if ligne["agent"] == "lecteur_pieces"
                                        and not ligne["fichier"].startswith("depots/")],
                             "depots": [ligne["fichier"] for ligne in lu["lecture"]
                                        if ligne["fichier"].startswith("depots/")]},
                "appel_modele": appels,
                "declaration": {"reference": d["reference"], "sinistre": {k: v for k, v in d["sinistre"].items()
                                                                          if k != "description"},
                                "sinistres_12_mois": d["historique"]["sinistres_12_mois"],
                                "code_postal": d["assure"]["code_postal"]}}

    @app.post("/api/decider")
    def decider(confirmation: Confirmation) -> dict[str, Any]:
        lu = sessions.get(confirmation.session)
        if lu is None:
            raise HTTPException(404, "session inconnue : relire le dossier")
        demande = json.loads(json.dumps(lu["demande"]))  # copie : la lecture du serveur reste intacte
        if len(confirmation.pieces) != len(demande["pieces"]) or len(confirmation.depots) != len(
                demande["espace_assure"]["depots"]):
            raise HTTPException(422, "le nombre de pièces ne correspond pas à la lecture du serveur")
        corrections = []
        retenu = confirmation.contrat.model_dump(mode="json")
        for champ, valeur in retenu.items():
            if demande["contrat"][champ] != valeur:
                corrections.append({"champ": f"contrat.{champ}", "lu": demande["contrat"][champ], "retenu": valeur})
        declare = demande["contrat"]["numero"]  # égal au numéro déclaré : la lecture l'a vérifié
        demande["contrat"] = retenu
        for nom, lues, confirmees in (("pieces", demande["pieces"], confirmation.pieces),
                                      ("depots", demande["espace_assure"]["depots"], confirmation.depots)):
            for i, (piece, conf) in enumerate(zip(lues, confirmees, strict=True)):
                nouvelle = {"type": piece["type"], "lisible": conf.lisible}
                if piece["type"] == "facture" and conf.lisible:
                    if conf.montant is None or not math.isfinite(conf.montant):
                        raise HTTPException(422, f"{nom}[{i}] : une facture lisible doit avoir un montant positif")
                    nouvelle["montant"] = round(conf.montant, 2)
                if nouvelle != piece:
                    corrections.append({"champ": f"{nom}[{i}] ({piece['type']})", "lu": piece, "retenu": nouvelle})
                lues[i] = nouvelle
        debut = perf_counter()
        if retenu["numero"] != declare:
            fiche = escalade_directe(demande["reference"], f"Contrat confirmé ({retenu['numero']}) différent du contrat "
                                                           f"déclaré ({declare}) : reprise manuelle")
        else:
            fiche = traiter(demande, consulter=consulter_pour(url))  # nouveau budget de 10 s, après la confirmation
        duree_ms = round((perf_counter() - debut) * 1000, 1)
        appel = any(x["agent"] == "antifraude" and x["appel_externe"] for x in fiche["trace"])
        envoye = None
        if appel:
            s = demande["sinistre"]
            try:
                envoye = construire_donnees(reference=demande["reference"], type_sinistre=s["type"],
                                            date_survenance=s["date_survenance"], montant_declare=s["montant_declare"],
                                            anciennete_contrat_jours=jours_entre(retenu["date_souscription"],
                                                                                 s["date_survenance"]),
                                            sinistres_12_mois=demande["historique"]["sinistres_12_mois"],
                                            code_postal=demande["assure"]["code_postal"])
            except RequeteNonConforme:
                envoye = None
        factures = [p["montant"] for p in demande["pieces"] + demande["espace_assure"]["depots"]
                    if p["type"] == "facture" and p.get("lisible") and p.get("montant")]
        return {"fiche": fiche, "metriques": calculer_metriques([fiche]), "corrections": corrections,
                "envoye_au_partenaire": envoye, "jamais_envoye": JAMAIS_ENVOYE, "partenaire": url or "bouchon",
                "montants": {"declare": demande["sinistre"]["montant_declare"], "factures_lisibles": sum(factures),
                             "paye": fiche["montant_rembourse"]},
                "duree_lecture_ms": lu["duree_lecture_ms"], "duree_decision_ms": duree_ms}

    @app.get("/api/partenaire")
    def partenaire() -> dict[str, Any]:
        if not url:
            return {"adresse": None, "joignable": False}
        try:
            etat = httpx.get(f"{url}/_sim/etat", timeout=2).json()
        except (httpx.HTTPError, ValueError):
            return {"adresse": url, "joignable": False}
        return {"adresse": url, "joignable": True, "etat": etat}

    @app.post("/api/partenaire")
    def regler(reglage: Reglage) -> dict[str, Any]:
        if not url:
            raise HTTPException(409, "aucun partenaire configuré")
        try:
            if reglage.action == "reset":
                httpx.post(f"{url}/_sim/reset", timeout=2).raise_for_status()
            else:
                corps = {"mode": reglage.action}
                if reglage.variante:
                    corps["variante"] = reglage.variante
                if reglage.delai_s is not None:
                    corps["delai_s"] = reglage.delai_s
                httpx.post(f"{url}/_sim/mode", json=corps, timeout=2).raise_for_status()
        except httpx.HTTPError as erreur:
            raise HTTPException(502, f"partenaire injoignable ({type(erreur).__name__})") from None
        return partenaire()

    return app
