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

from kaldera.agents.coherence import Interpretation
from kaldera.coordination import traiter
from kaldera.extraction.dossier import traiter_dossier
from kaldera.extraction.lecteurs import ContratLu, FactureLue, Reponse
from kaldera.metriques import calculer_metriques_lecture
from tests.faux_coherence import interpretation

RACINE = Path(__file__).resolve().parents[2]
DOSSIERS = RACINE / "dossiers"
VERITE = json.loads((DOSSIERS / "verite.json").read_text(encoding="utf-8"))
DEMANDES = {d["reference"]: d for ligne in (RACINE / "eval" / "scenarios.jsonl").read_text(encoding="utf-8").splitlines()
            if ligne.strip() for d in json.loads(ligne)["demandes"]}
ISSUE = ("issue", "decision", "montant_rembourse", "file", "mode_degrade", "arret")


def oracle() -> Any:
    """Faux modèle parfait : le contrat d'après le numéro lu dans le texte, la facture d'après l'empreinte de l'image,
    la cohérence d'après les étiquettes (toutes les pièces des 34 dossiers concordent)."""
    contrats = {v["contrat"]["numero"]: v["contrat"] for v in VERITE.values()}
    factures = {hashlib.sha256((DOSSIERS / ref / nom).read_bytes()).hexdigest(): f
                for ref, v in VERITE.items() for nom, f in v["fichiers"].items() if f["type"] == "facture"}

    def appeler(consigne: str, schema: type[BaseModel], image_png: bytes | None = None, *,
                delai_s: float | None = None) -> Any:
        if schema is ContratLu:
            numero = re.search(r"CTR-\d{6}", consigne).group(0)
            return ContratLu(**contrats[numero])
        if schema is Interpretation:
            return interpretation(consigne)
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
    assert [ligne["agent"] for ligne in resultat["lecture"]] == ["lecteur_contrat", "lecteur_pieces", "lecteur_pieces",
                                                                 "coherence"]
    assert [ligne["fichier"] for ligne in resultat["lecture"]] == ["contrat.pdf", "piece-1-facture.png",
                                                                   "piece-2-photo.png",
                                                                   "piece-1-facture.png, piece-2-photo.png"]
    assert [ligne["appel_modele"] for ligne in resultat["lecture"]] == [True, True, False, True]
    etapes = [(ligne["agent"], ligne["raison"]) for ligne in resultat["fiche"]["trace"]]
    assert ("coherence", "coherent") in etapes  # la Coordination a délégué la cohérence avant de conclure
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
    assert [(x["agent"], x["statut"]) for x in resultat["lecture"]] == [
        ("lecteur_contrat", "echec"), ("coherence", "non_utilise")]  # l'appel anticipé a échoué lui aussi
    assert resultat["lecture"][-1]["verdict"] == "non_effectue"


def test_un_contrat_qui_ne_correspond_pas_a_la_declaration_est_escalade() -> None:
    def mauvais_contrat(consigne: str, schema: type[BaseModel], image_png: bytes | None = None, *,
                        delai_s: float | None = None) -> Any:
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
        ("contrat.pdf", 400, 30), ("piece-1-facture.png", 400, 30), ("piece-2-photo.png", 0, 0),
        ("piece-1-facture.png, piece-2-photo.png", 400, 30)]
    assert resultat["fiche"]["decision"] == "acceptee"


def test_les_agents_de_lecture_ont_leurs_metriques() -> None:
    lectures = [traiter_dossier(DOSSIERS / ref, avec_jetons(oracle(), 400, 30))["lecture"]
                for ref in ("KAL-26-0101", "KAL-26-0601")]  # NOM-01, puis BCL-01 : deux factures floues
    metriques = calculer_metriques_lecture(lectures)
    assert set(metriques) == {"lecteur_contrat", "lecteur_pieces", "coherence"}
    contrat, pieces = metriques["lecteur_contrat"], metriques["lecteur_pieces"]
    # BCL-01 s'arrête avant la cohérence, mais l'appel anticipé a eu lieu (sur la photo nette) : il est compté
    assert (metriques["coherence"]["appels"], metriques["coherence"]["jetons_entree"]) == (2, 800)
    assert [x["statut"] for x in lectures[1] if x["agent"] == "coherence"] == ["non_utilise"]
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


# ---------------------------------------------------------------- formulaire validé avant toute lecture (N1)

def formulaire_modifie(tmp_path: Path, modifier: Any) -> Path:
    dossier = copie_du_dossier(tmp_path)
    chemin = dossier / "declaration.json"
    declaration = json.loads(chemin.read_text(encoding="utf-8"))
    modifier(declaration)
    chemin.write_text(json.dumps(declaration, ensure_ascii=False), encoding="utf-8")
    return dossier


@pytest.mark.parametrize("modifier, champ", [
    (lambda d: d.pop("assure"), "assure"),
    (lambda d: d["assure"].pop("code_postal"), "assure"),
    (lambda d: d.pop("numero_contrat"), "numero_contrat"),
    (lambda d: d["sinistre"].pop("type"), "sinistre"),
    (lambda d: d["sinistre"].update(date_survenance="14/08/2026"), "sinistre"),
    (lambda d: d["sinistre"].update(montant_declare="1850"), "sinistre"),
    (lambda d: d.pop("historique"), "historique"),
    (lambda d: d["historique"].update(sinistres_12_mois=-1), "historique"),
])
def test_un_formulaire_incomplet_donne_une_escalade_sans_appel_au_modele(tmp_path: Path, modifier: Any,
                                                                         champ: str) -> None:
    resultat = traiter_dossier(formulaire_modifie(tmp_path, modifier), sans_appel)
    doit_escalader(resultat, "Formulaire")
    assert champ in resultat["fiche"]["motif"]
    assert resultat["fiche"]["reference"] == "KAL-26-0101"


# ---------------------------------------------------------------- un seul budget de 10 s, lecture comprise (§ 12)

def test_chaque_appel_au_modele_recoit_le_temps_restant_du_budget() -> None:
    delais: dict[str, float] = {}
    appeler = oracle()

    def mesure(consigne: str, schema: type[BaseModel], image_png: Any = None, *,
               delai_s: float | None = None) -> Any:
        delais[schema.__name__] = delai_s
        return appeler(consigne, schema, image_png)

    traiter_dossier(DOSSIERS / "KAL-26-0101", mesure)
    from kaldera.bornes import BORNES
    plafond = BORNES.duree_max_s - BORNES.reserve_fiche_s  # 10 s moins la réserve de la fiche
    assert set(delais) == {"ContratLu", "FactureLue", "Interpretation"}
    assert all(d is not None and 0 < d <= plafond for d in delais.values())
    assert delais["FactureLue"] <= delais["ContratLu"]  # le temps restant ne remonte jamais


def test_la_coherence_part_des_l_arrivee_en_parallele_de_la_lecture() -> None:
    import time
    appeler = oracle()

    def lent(consigne: str, schema: type[BaseModel], image_png: Any = None, **kwargs: Any) -> Any:
        time.sleep(0.3)
        return appeler(consigne, schema, image_png)

    debut = time.perf_counter()
    resultat = traiter_dossier(DOSSIERS / "KAL-26-0101", lent)
    duree = time.perf_counter() - debut
    assert resultat["fiche"]["decision"] == "acceptee"
    assert duree < 0.8, duree  # contrat puis facture (0,6 s), la cohérence en même temps ; en série : 0,9 s


def test_un_appel_anticipe_non_utilise_reste_dans_la_trace_avec_son_cout() -> None:
    resultat = traiter_dossier(DOSSIERS / "KAL-26-0102", avec_jetons(oracle(), 400, 30))  # contrat résilié
    assert resultat["fiche"]["decision"] == "refusee"  # la règle 1 conclut avant la cohérence
    ligne = resultat["lecture"][-1]
    assert (ligne["agent"], ligne["statut"], ligne["appel_modele"], ligne["jetons_entree"]) == (
        "coherence", "non_utilise", True, 400)


def test_une_lecture_trop_lente_donne_une_escalade_technique_dans_le_budget() -> None:
    import time
    from kaldera.bornes import Bornes
    appeler = oracle()

    def lent(consigne: str, schema: type[BaseModel], image_png: bytes | None = None, *,
             delai_s: float | None = None) -> Any:
        time.sleep(0.25)
        return appeler(consigne, schema, image_png)

    debut = time.perf_counter()
    resultat = traiter_dossier(DOSSIERS / "KAL-26-0101", lent, bornes=Bornes(duree_max_s=0.3, reserve_fiche_s=0.1))
    duree = time.perf_counter() - debut
    doit_escalader(resultat, "délai")
    assert duree < 0.6, duree  # la facture n'est jamais lue : plus de temps


def test_la_coordination_continue_le_meme_budget_que_la_lecture() -> None:
    from kaldera.bornes import Bornes
    appeler = oracle()
    rapide = Bornes(duree_max_s=0.3, reserve_fiche_s=0.1)

    def lecture_qui_consomme_le_budget(consigne: str, schema: type[BaseModel], image_png: bytes | None = None, *,
                                       delai_s: float | None = None) -> Any:
        import time
        if schema is FactureLue:
            time.sleep(delai_s + 0.01 if delai_s else 0)  # la dernière lecture finit juste après la limite
        return appeler(consigne, schema, image_png)

    fiche = traiter_dossier(DOSSIERS / "KAL-26-0101", lecture_qui_consomme_le_budget, bornes=rapide)["fiche"]
    assert fiche["arret"] == {"borne": "duree_max_s"}  # la Coordination ne repart pas de zéro


# ---------------------------------------------------------------- la démonstration complète : pièces, partenaire, décision

def test_sans_option_le_chemin_des_pieces_garde_le_bouchon() -> None:
    from kaldera.agents.antifraude import partenaire_bouchon
    from kaldera.extraction.dossier import consulter_pour, options
    assert options(["dossiers/KAL-26-0201"]) == (Path("dossiers/KAL-26-0201"), None)
    assert consulter_pour(None) is partenaire_bouchon


def test_une_adresse_explicite_branche_le_vrai_client_a2a() -> None:
    from kaldera.agents.antifraude import partenaire_bouchon
    from kaldera.extraction.dossier import consulter_pour, options
    dossier, url = options(["dossiers/KAL-26-0201", "--partenaire", "http://127.0.0.1:8100"])
    assert url == "http://127.0.0.1:8100" and consulter_pour(url) is not partenaire_bouchon


def test_partenaire_seul_lit_adresse_et_jeton_dans_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from kaldera.extraction.dossier import options
    monkeypatch.delenv("PARTENAIRE_URL", raising=False)
    monkeypatch.delenv("PARTENAIRE_JETON", raising=False)
    env = tmp_path / ".env"
    env.write_text("PARTENAIRE_URL=http://localhost:8100\nPARTENAIRE_JETON=jeton-du-fichier\n", encoding="utf-8")
    # localhost devient 127.0.0.1 : sous Windows, localhost passe d'abord par IPv6 et coûte 2 s par appel (mesuré)
    assert options(["dossiers/KAL-26-0201", "--partenaire"], fichier_env=env)[1] == "http://127.0.0.1:8100"
    import os
    assert os.environ["PARTENAIRE_JETON"] == "jeton-du-fichier"


def test_l_environnement_l_emporte_sur_le_fichier_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from kaldera.extraction.dossier import options
    monkeypatch.setenv("PARTENAIRE_URL", "http://127.0.0.1:9999")
    monkeypatch.setenv("PARTENAIRE_JETON", "jeton-de-l-environnement")
    env = tmp_path / ".env"
    env.write_text("PARTENAIRE_URL=http://localhost:8100\nPARTENAIRE_JETON=autre\n", encoding="utf-8")
    assert options(["d", "--partenaire"], fichier_env=env)[1] == "http://127.0.0.1:9999"
    import os
    assert os.environ["PARTENAIRE_JETON"] == "jeton-de-l-environnement"


def test_des_dates_impossibles_dans_le_formulaire_donnent_une_escalade(tmp_path: Path) -> None:
    def dates(d: dict[str, Any]) -> None:
        d["sinistre"].update(date_survenance="2026-08-18", date_declaration="2026-08-14")

    fiche = traiter_dossier(formulaire_modifie(tmp_path, dates), oracle())["fiche"]
    assert (fiche["issue"], fiche["file"]) == ("escalade", "gestionnaire") and "incohérentes" in fiche["motif"]


# ---------------------------------------------------------------- cohérence des pièces avec la déclaration (§ 5)

def test_seules_les_pieces_lisibles_partent_au_controle_de_coherence_depots_compris() -> None:
    vues: list[str] = []
    appeler = oracle()

    def espion(consigne: str, schema: type[BaseModel], images: Any = None, **kwargs: Any) -> Any:
        if schema is Interpretation:
            vues.extend(re.findall(r"^\d+\. (\S+\.png)", consigne, flags=re.MULTILINE))
            assert isinstance(images, list) and len(images) == 2
        return appeler(consigne, schema, images, **kwargs)

    resultat = traiter_dossier(DOSSIERS / "KAL-26-0107", espion)  # NOM-07 : facture, puis photo déposée
    assert vues == ["piece-1-facture.png", "depots/1-photo.png"]
    assert resultat["fiche"]["decision"] == "acceptee"


def test_un_dossier_incoherent_va_a_un_gestionnaire_avec_la_piece_en_cause() -> None:
    appeler = oracle()

    def miroiterie(consigne: str, schema: type[BaseModel], images: Any = None, **kwargs: Any) -> Any:
        if schema is Interpretation:
            return interpretation(consigne, **{"piece-1-facture.png": "bris_de_glace"})
        if schema is FactureLue:  # facture construite pour l'évaluation : même montant que le dossier KAL-26-0101
            return FactureLue(lisible=True, montant_total_ttc=1850.0)
        return appeler(consigne, schema, images, **kwargs)

    resultat = traiter_dossier(RACINE / "evaluation" / "coherence" / "dossiers" / "KAL-26-0701", miroiterie)
    fiche = resultat["fiche"]
    assert (fiche["issue"], fiche["file"], fiche["decision"]) == ("escalade", "gestionnaire", None)
    assert "incohérentes" in fiche["motif"] and "piece-1-facture.png" in fiche["motif"]
    assert [ligne["agent"] for ligne in resultat["fiche"]["trace"]][-2:] == ["coherence", "coordination"]


def test_un_modele_en_panne_pendant_la_coherence_donne_une_escalade_technique() -> None:
    appeler = oracle()

    def panne(consigne: str, schema: type[BaseModel], images: Any = None, **kwargs: Any) -> Any:
        if schema is Interpretation:
            raise ConnectionError("Azure injoignable")
        return appeler(consigne, schema, images, **kwargs)

    resultat = traiter_dossier(DOSSIERS / "KAL-26-0101", panne)
    fiche = resultat["fiche"]
    assert (fiche["issue"], fiche["file"], fiche["decision"]) == ("escalade", "gestionnaire", None)
    assert "Contrôle de cohérence impossible (modele_indisponible)" in fiche["motif"]
    assert resultat["lecture"][-1]["statut"] == "echec"
