"""Étape E3 : traiter_dossier, des pièces non structurées jusqu'à la fiche de décision.

Les agents de lecture produisent le JSON de la spec § 3 ; la chaîne du chantier 1 décide ensuite. Le modèle est
remplacé par des faux (aucun réseau). Avec un faux « oracle » qui rend les vraies valeurs, les 34 dossiers doivent
donner exactement les mêmes décisions que les 34 demandes JSON : l'assemblage ne perd ni ne déforme rien.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from kaldera.coordination import traiter
from kaldera.extraction.dossier import traiter_dossier
from kaldera.extraction.lecteurs import ContratLu, FactureLue

RACINE = Path(__file__).resolve().parents[2]
DOSSIERS = RACINE / "dossiers"
VERITE = json.loads((DOSSIERS / "verite.json").read_text(encoding="utf-8"))
DEMANDES = {d["reference"]: d for ligne in (RACINE / "eval" / "scenarios.jsonl").read_text(encoding="utf-8").splitlines()
            if ligne.strip() for d in json.loads(ligne)["demandes"]}
ISSUE = ("issue", "decision", "montant_rembourse", "file", "mode_degrade", "arret")


def oracle() -> Any:
    """Faux modèle parfait : le contrat d'après le numéro lu dans le texte, la facture d'après l'empreinte de l'image."""
    contrats = {v["contrat"]["numero"]: v["contrat"] for v in VERITE.values()}
    factures = {hashlib.sha256((DOSSIERS / ref / nom).read_bytes()).hexdigest(): f
                for ref, v in VERITE.items() for nom, f in v["fichiers"].items() if f["type"] == "facture"}

    def appeler(consigne: str, schema: type[BaseModel], image_png: bytes | None = None) -> Any:
        if schema is ContratLu:
            numero = re.search(r"CTR-\d{6}", consigne).group(0)
            return ContratLu(**contrats[numero])
        vraie = factures[hashlib.sha256(image_png).hexdigest()]
        return FactureLue(lisible=True, montant_total_ttc=vraie["montant"])
    return appeler


def test_les_34_dossiers_donnent_les_memes_decisions_que_les_34_demandes_json() -> None:
    appeler = oracle()
    for reference, demande in DEMANDES.items():
        resultat = traiter_dossier(DOSSIERS / reference, appeler)
        attendu = traiter(demande)
        assert {k: resultat["fiche"][k] for k in ISSUE} == {k: attendu[k] for k in ISSUE}, reference


def test_la_demande_extraite_a_le_format_de_la_spec(tmp_path: Path) -> None:
    resultat = traiter_dossier(DOSSIERS / "KAL-26-0101", oracle())
    demande = resultat["demande"]
    assert set(demande) == {"reference", "assure", "contrat", "sinistre", "pieces", "historique", "espace_assure"}
    assert demande["contrat"] == DEMANDES["KAL-26-0101"]["contrat"]
    assert demande["pieces"] == DEMANDES["KAL-26-0101"]["pieces"]


def test_la_lecture_est_tracee_a_part_de_la_decision() -> None:
    resultat = traiter_dossier(DOSSIERS / "KAL-26-0101", oracle())  # NOM-01 : contrat, facture, photo
    assert [ligne["agent"] for ligne in resultat["lecture"]] == ["lecteur_contrat", "lecteur_pieces", "lecteur_pieces"]
    assert [ligne["fichier"] for ligne in resultat["lecture"]] == ["contrat.pdf", "piece-1-facture.png",
                                                                   "piece-2-photo.png"]
    assert [ligne["appel_modele"] for ligne in resultat["lecture"]] == [True, True, False]
    assert resultat["fiche"]["decision"] == "acceptee" and resultat["fiche"]["montant_rembourse"] == 1700.0


def test_bcl01_depuis_ses_pieces_la_boucle_est_arretee_comme_depuis_le_json() -> None:
    resultat = traiter_dossier(DOSSIERS / "KAL-26-0601", oracle())
    assert resultat["fiche"]["arret"] == {"borne": "etat_repete"}
    assert resultat["demande"]["pieces"][0] == {"type": "facture", "lisible": False}


def test_un_modele_en_panne_donne_une_escalade_motivee_sans_decision() -> None:
    def en_panne(*_args: Any, **_kwargs: Any) -> Any:
        raise ConnectionError("Azure injoignable")

    resultat = traiter_dossier(DOSSIERS / "KAL-26-0101", en_panne)
    fiche = resultat["fiche"]
    assert (fiche["issue"], fiche["file"], fiche["decision"]) == ("escalade", "gestionnaire", None)
    assert "lecture" in fiche["motif"].lower()
    assert resultat["lecture"][-1]["statut"] == "echec"


def test_un_contrat_qui_ne_correspond_pas_a_la_declaration_est_escalade() -> None:
    def mauvais_contrat(consigne: str, schema: type[BaseModel], image_png: bytes | None = None) -> Any:
        return ContratLu(numero="CTR-000000", formule="premium", date_souscription="2020-01-01", statut="actif",
                         cotisations_a_jour=True)

    fiche = traiter_dossier(DOSSIERS / "KAL-26-0101", mauvais_contrat)["fiche"]
    assert (fiche["issue"], fiche["file"]) == ("escalade", "gestionnaire")
    assert "CTR-000000" in fiche["motif"] and "CTR-778801" in fiche["motif"]


@pytest.mark.parametrize("reference", ["KAL-26-0107", "KAL-26-0405"])  # NOM-07, PAN-01 : photo déposée ensuite
def test_les_depots_de_l_espace_assure_sont_lus_aussi(reference: str) -> None:
    resultat = traiter_dossier(DOSSIERS / reference, oracle())
    assert resultat["demande"]["espace_assure"]["depots"] == DEMANDES[reference]["espace_assure"]["depots"]
    assert resultat["fiche"]["decision"] == "acceptee"
