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
from kaldera.extraction.lecteurs import ContratLu, FactureLue, Reponse
from kaldera.metriques import calculer_metriques_lecture

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


# ---------------------------------------------------------------- jetons et métriques des agents de lecture

def avec_jetons(appeler: Any, entree: int, sortie: int) -> Any:
    """Le même faux modèle, qui annonce en plus une consommation de jetons par appel."""
    def appel(*args: Any, **kwargs: Any) -> Any:
        return Reponse(appeler(*args, **kwargs), entree, sortie)
    return appel


def test_chaque_ligne_de_lecture_porte_les_jetons_consommes() -> None:
    resultat = traiter_dossier(DOSSIERS / "KAL-26-0101", avec_jetons(oracle(), 400, 30))
    assert [(x["fichier"], x["jetons_entree"], x["jetons_sortie"]) for x in resultat["lecture"]] == [
        ("contrat.pdf", 400, 30), ("piece-1-facture.png", 400, 30), ("piece-2-photo.png", 0, 0)]
    assert resultat["fiche"]["decision"] == "acceptee"


def test_les_agents_de_lecture_ont_leurs_metriques() -> None:
    lectures = [traiter_dossier(DOSSIERS / ref, avec_jetons(oracle(), 400, 30))["lecture"]
                for ref in ("KAL-26-0101", "KAL-26-0601")]  # NOM-01, puis BCL-01 : deux factures floues
    metriques = calculer_metriques_lecture(lectures)
    assert set(metriques) == {"lecteur_contrat", "lecteur_pieces"}
    contrat, pieces = metriques["lecteur_contrat"], metriques["lecteur_pieces"]
    assert (contrat["appels"], contrat["appels_externes"], contrat["jetons_entree"]) == (2, 2, 800)
    assert (pieces["appels"], pieces["appels_externes"], pieces["jetons_sortie"]) == (5, 1, 30)
    assert contrat["echecs"] == pieces["echecs"] == 0
    assert isinstance(pieces["latence_ms"], float)


def test_une_lecture_en_echec_compte_comme_echec() -> None:
    def en_panne(*_args: Any, **_kwargs: Any) -> Any:
        raise ConnectionError("Azure injoignable")

    metriques = calculer_metriques_lecture([traiter_dossier(DOSSIERS / "KAL-26-0101", en_panne)["lecture"]])
    assert metriques["lecteur_contrat"]["echecs"] == 1


# ---------------------------------------------------------------- aucune erreur brute sur le chemin des pièces (N1)

def copie_du_dossier(tmp_path: Path, reference: str = "KAL-26-0101") -> Path:
    import shutil
    cible = tmp_path / reference
    shutil.copytree(DOSSIERS / reference, cible)
    return cible


def sans_appel(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("le modèle ne devait pas être appelé")


def doit_escalader(resultat: dict[str, Any], mot: str) -> None:
    fiche = resultat["fiche"]
    assert (fiche["issue"], fiche["file"], fiche["decision"]) == ("escalade", "gestionnaire", None)
    assert mot in fiche["motif"], fiche["motif"]
    assert resultat["demande"] is None


def test_un_contrat_absent_donne_une_escalade_motivee(tmp_path: Path) -> None:
    dossier = copie_du_dossier(tmp_path)
    (dossier / "contrat.pdf").unlink()
    doit_escalader(traiter_dossier(dossier, sans_appel), "Contrat absent")


def test_un_contrat_corrompu_donne_une_escalade_motivee(tmp_path: Path) -> None:
    dossier = copie_du_dossier(tmp_path)
    (dossier / "contrat.pdf").write_bytes(b"ceci n'est pas un PDF")
    doit_escalader(traiter_dossier(dossier, sans_appel), "corrompu")


def test_un_contrat_sans_texte_donne_une_escalade_sans_appel_au_modele(tmp_path: Path) -> None:
    import pymupdf
    dossier = copie_du_dossier(tmp_path)
    document = pymupdf.open()
    page = document.new_page()
    page.insert_image(page.rect, filename=str(dossier / "piece-1-facture.png"))
    document.save(dossier / "contrat.pdf")
    doit_escalader(traiter_dossier(dossier, sans_appel), "sans texte")


def test_un_formulaire_absent_donne_une_escalade_sous_le_nom_du_dossier(tmp_path: Path) -> None:
    dossier = copie_du_dossier(tmp_path)
    (dossier / "declaration.json").unlink()
    resultat = traiter_dossier(dossier, sans_appel)
    doit_escalader(resultat, "Formulaire")
    assert resultat["fiche"]["reference"] == "KAL-26-0101"


@pytest.mark.parametrize("nom", ["piece-3-facture.jpg", "piece-3-facture.PNG", "facture-scan.png"])
def test_un_fichier_non_reconnu_n_est_jamais_ignore(tmp_path: Path, nom: str) -> None:
    dossier = copie_du_dossier(tmp_path)
    (dossier / nom).write_bytes((dossier / "piece-1-facture.png").read_bytes())
    doit_escalader(traiter_dossier(dossier, sans_appel), nom)


def test_une_image_corrompue_est_une_piece_illisible_qui_suit_le_complement(tmp_path: Path) -> None:
    dossier = copie_du_dossier(tmp_path)
    (dossier / "piece-1-facture.png").write_bytes(b"pas une image")
    resultat = traiter_dossier(dossier, oracle())  # le modèle ne lit que le contrat
    assert resultat["demande"]["pieces"][0] == {"type": "facture", "lisible": False}
    assert resultat["fiche"]["motif"].startswith("Pièces manquantes")  # complément demandé, aucun dépôt (§ 5)
