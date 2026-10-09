"""Poste du gestionnaire (prototype) : ce que le serveur garantit, quel que soit le navigateur."""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from kaldera.agents.antifraude import AvisFraude
from kaldera.bornes import Bornes
from kaldera.web.app import appel_reference, creer_app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(creer_app(partenaire_url=None))  # bouchon : aucun réseau


def lire(client: TestClient, dossier: str = "KAL-26-0101") -> dict[str, Any]:
    reponse = client.post("/api/lire", json={"dossier": dossier, "mode": "reference"})
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


def confirmer(lu: dict[str, Any], **changements: Any) -> dict[str, Any]:
    corps = {"session": lu["session"], "contrat": dict(lu["contrat"]),
             "pieces": [{"lisible": p["lisible"], "montant": p.get("montant")} for p in lu["pieces"]],
             "depots": [{"lisible": p["lisible"], "montant": p.get("montant")} for p in lu["depots"]]}
    corps.update(changements)
    return corps


def test_la_page_et_la_liste_des_34_dossiers(client: TestClient) -> None:
    assert "poste du gestionnaire" in client.get("/").text
    assert len([d for d in client.get("/api/dossiers").json() if d["jeu"] == "scenarios"]) == 34


def test_un_dossier_hors_de_la_liste_est_refuse(client: TestClient) -> None:
    for nom in ("../src", "KAL-26-9999", "..\\..\\Windows"):
        assert client.post("/api/lire", json={"dossier": nom, "mode": "reference"}).status_code == 404


def test_lire_rend_ce_qui_a_ete_lu_sans_decider(client: TestClient) -> None:
    lu = lire(client)
    assert lu["contrat"]["numero"] == "CTR-778801" and len(lu["pieces"]) == 2
    assert [ligne["appel_modele"] for ligne in lu["lecture"]] == [True, True, False]
    assert "description" not in lu["declaration"]["sinistre"]


def test_confirmer_sans_correction_donne_la_meme_decision_que_le_moteur(client: TestClient) -> None:
    r = client.post("/api/decider", json=confirmer(lire(client))).json()
    assert (r["fiche"]["decision"], r["fiche"]["montant_rembourse"], r["corrections"]) == ("acceptee", 1700.0, [])


def test_une_correction_est_gardee_pour_l_audit_et_change_la_decision(client: TestClient) -> None:
    lu = lire(client)
    pieces = [{"lisible": True, "montant": 1000.0}, {"lisible": True, "montant": None}]
    r = client.post("/api/decider", json=confirmer(lu, pieces=pieces)).json()
    assert r["fiche"]["montant_rembourse"] == 850.0  # 1 000 € moins 150 € de franchise
    (correction,) = r["corrections"]
    assert correction["lu"]["montant"] == 1850.0 and correction["retenu"]["montant"] == 1000.0


@pytest.mark.parametrize("champ, valeur", [("formule", "luxe"), ("statut", "peut-etre"), ("numero", "12"),
                                           ("date_souscription", "hier")])
def test_une_correction_hors_schema_est_refusee(client: TestClient, champ: str, valeur: str) -> None:
    lu = lire(client)
    reponse = client.post("/api/decider", json=confirmer(lu, contrat={**lu["contrat"], champ: valeur}))
    assert reponse.status_code == 422


def test_une_facture_lisible_sans_montant_positif_est_refusee(client: TestClient) -> None:
    lu = lire(client)
    for montant in (None, -5, 0):
        corps = confirmer(lu, pieces=[{"lisible": True, "montant": montant}, {"lisible": True, "montant": None}])
        assert client.post("/api/decider", json=corps).status_code == 422


def test_le_navigateur_ne_peut_pas_ajouter_de_piece(client: TestClient) -> None:
    lu = lire(client)
    corps = confirmer(lu, pieces=[{"lisible": True, "montant": 1850.0}, {"lisible": True}, {"lisible": True}])
    assert client.post("/api/decider", json=corps).status_code == 422


def test_un_numero_de_contrat_corrige_different_du_declare_part_en_escalade(client: TestClient) -> None:
    lu = lire(client)
    r = client.post("/api/decider", json=confirmer(lu, contrat={**lu["contrat"], "numero": "CTR-000001"})).json()
    assert (r["fiche"]["issue"], r["fiche"]["file"]) == ("escalade", "gestionnaire")


def test_une_session_inconnue_est_refusee(client: TestClient) -> None:
    corps = confirmer(lire(client))
    corps["session"] = "inexistante"
    assert client.post("/api/decider", json=corps).status_code == 404


def test_sans_partenaire_configure_l_etat_le_dit(client: TestClient) -> None:
    assert client.get("/api/partenaire").json() == {"adresse": None, "joignable": False}


# ---------------------------------------------------------------- revue du prototype (08/10, nuit)

def compteur() -> tuple[list[int], Any]:
    appels = [0]

    def consulter(**_donnees: Any) -> AvisFraude:
        appels[0] += 1
        return AvisFraude(statut="avis", niveau="faible", score=0.1, appel_externe=True)
    return appels, consulter


def test_confirmer_deux_fois_ne_rappelle_jamais_le_partenaire() -> None:
    appels, consulter = compteur()
    client = TestClient(creer_app(partenaire_url=None, consulter=consulter))
    lu = lire(client, "KAL-26-0201")  # AF-01 : un indicateur, donc un appel
    premiere = client.post("/api/decider", json=confirmer(lu)).json()
    seconde = client.post("/api/decider", json=confirmer(lu)).json()
    assert appels == [1] and seconde["deja_decide"] is True and premiere["deja_decide"] is False
    assert seconde["fiche"] == premiere["fiche"]


def test_la_decision_n_a_que_le_temps_automatique_restant_apres_la_lecture() -> None:
    reference = appel_reference()

    def lecture_qui_consomme_tout(consigne: str, schema: type, image_png: bytes | None = None, *,
                                  delai_s: float | None = None) -> Any:
        if image_png is not None:
            time.sleep((delai_s or 0) + 0.02)  # la dernière lecture finit après l'échéance
        return reference(consigne, schema, image_png)

    client = TestClient(creer_app(partenaire_url=None, bornes=Bornes(duree_max_s=0.5, reserve_fiche_s=0.1),
                                  lecteurs={"reference": lambda: lecture_qui_consomme_tout}))
    r = client.post("/api/decider", json=confirmer(lire(client))).json()
    assert r["fiche"]["arret"] == {"borne": "duree_max_s"}  # pas de nouveau budget de 10 s


def test_la_pause_de_la_personne_ne_compte_pas_dans_le_budget() -> None:
    client = TestClient(creer_app(partenaire_url=None, bornes=Bornes(duree_max_s=0.5, reserve_fiche_s=0.1)))
    lu = lire(client)
    time.sleep(0.6)  # la personne réfléchit plus longtemps que tout le budget
    assert client.post("/api/decider", json=confirmer(lu)).json()["fiche"]["decision"] == "acceptee"


@pytest.mark.parametrize("piece", [{"lisible": "false", "montant": 1850.0}, {"lisible": True, "montant": True},
                                   {"lisible": True, "montant": "1850"}, {"lisible": True, "montant": 0.001},
                                   {"lisible": True, "montant": 12.345}, {"lisible": 1, "montant": 1850.0}])
def test_une_valeur_de_mauvais_type_ou_hors_centime_est_refusee(client: TestClient, piece: dict[str, Any]) -> None:
    lu = lire(client)
    corps = confirmer(lu, pieces=[piece, {"lisible": True, "montant": None}])
    assert client.post("/api/decider", json=corps).status_code == 422


def test_un_montant_entier_ou_au_centime_est_accepte(client: TestClient) -> None:
    for montant, accorde in ((1850, 1700.0), (1000.5, 850.5)):
        lu = lire(client)
        corps = confirmer(lu, pieces=[{"lisible": True, "montant": montant}, {"lisible": True, "montant": None}])
        assert client.post("/api/decider", json=corps).json()["fiche"]["montant_rembourse"] == accorde


def test_cotisations_en_texte_refusees(client: TestClient) -> None:
    lu = lire(client)
    corps = confirmer(lu, contrat={**lu["contrat"], "cotisations_a_jour": "true"})
    assert client.post("/api/decider", json=corps).status_code == 422


def test_le_document_source_est_servi_et_rien_d_autre(client: TestClient) -> None:
    lu = lire(client)
    pdf = client.get(f"/api/document/{lu['session']}", params={"fichier": "contrat.pdf"})
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    image = client.get(f"/api/document/{lu['session']}", params={"fichier": "piece-1-facture.png"})
    assert image.status_code == 200 and image.headers["content-type"] == "image/png"
    for fichier in ("declaration.json", "../../.env", r"..\..\pyproject.toml", "inconnu.png"):
        assert client.get(f"/api/document/{lu['session']}", params={"fichier": fichier}).status_code == 404


def test_le_message_au_partenaire_est_capture_a_l_entree_du_client() -> None:
    appels, consulter = compteur()
    client = TestClient(creer_app(partenaire_url=None, consulter=consulter))
    r = client.post("/api/decider", json=confirmer(lire(client, "KAL-26-0201"))).json()
    assert set(r["message_partenaire"]) == {"reference_dossier", "type_sinistre", "montant_declare", "date_survenance",
                                            "anciennete_contrat_jours", "sinistres_12_mois", "departement"}
    sans = client.post("/api/decider", json=confirmer(lire(client, "KAL-26-0101"))).json()  # aucun indicateur
    assert sans["message_partenaire"] is None and appels == [1]


def test_nouvel_essai_de_simulation_oublie_les_sessions(client: TestClient) -> None:
    lu = lire(client)
    assert client.post("/api/simulation/nouvel-essai").status_code == 200
    assert client.post("/api/decider", json=confirmer(lu)).status_code == 404


# ---------------------------------------------------------------- l'agent Documents et cohérence dans le poste

def faux_modele_coherence(**ecarts: str) -> Any:
    """Un faux modèle pour le mode « modele » : contrat d'après son numéro, facture à 1 850 €, cohérence d'après
    `ecarts` (fichier -> sinistre évoqué ; les autres pièces concordent)."""
    import json
    import re
    from pathlib import Path

    from kaldera.agents.coherence import Interpretation
    from kaldera.extraction.lecteurs import ContratLu, FactureLue
    from tests.faux_coherence import interpretation

    verite = json.loads((Path(__file__).resolve().parents[2] / "dossiers" / "verite.json").read_text(encoding="utf-8"))
    contrats = {v["contrat"]["numero"]: v["contrat"] for v in verite.values()}

    def fabrique() -> Any:
        def appeler(consigne: str, schema: type, images: Any = None, *, delai_s: float | None = None) -> Any:
            if schema is ContratLu:
                return ContratLu(**contrats[re.search(r"CTR-\d{6}", consigne).group(0)])
            if schema is Interpretation:
                return interpretation(consigne, **ecarts)
            return FactureLue(lisible=True, montant_total_ttc=1850.0)
        return appeler
    return fabrique


def test_la_decision_du_poste_passe_par_la_coherence(client: TestClient) -> None:
    r = client.post("/api/decider", json=confirmer(lire(client))).json()
    etapes = [(ligne["agent"], ligne["raison"]) for ligne in r["fiche"]["trace"]]
    assert ("coherence", "coherent") in etapes  # la Coordination a délégué la cohérence avant l'Estimation
    assert r["coherence"]["verdict"] == "coherent" and r["fiche"]["decision"] == "acceptee"


def test_les_dossiers_du_jeu_de_coherence_sont_listes_et_lus_par_le_modele_seulement(client: TestClient) -> None:
    liste = client.get("/api/dossiers").json()
    assert sum(d["jeu"] == "scenarios" for d in liste) == 34 and sum(d["jeu"] == "coherence" for d in liste) == 8
    reponse = client.post("/api/lire", json={"dossier": "KAL-26-0701", "mode": "reference"})
    assert reponse.status_code == 422 and "modèle" in reponse.json()["detail"]


def test_une_facture_de_miroiterie_va_a_un_gestionnaire_dans_le_poste() -> None:
    app = creer_app(partenaire_url=None,
                    lecteurs={"modele": faux_modele_coherence(**{"piece-1-facture.png": "bris_de_glace"})})
    client = TestClient(app)
    lu = client.post("/api/lire", json={"dossier": "KAL-26-0701", "mode": "modele"}).json()
    r = client.post("/api/decider", json=confirmer(lu)).json()
    assert (r["fiche"]["issue"], r["fiche"]["file"], r["fiche"]["decision"]) == ("escalade", "gestionnaire", None)
    assert "incohérentes" in r["fiche"]["motif"] and "piece-1-facture.png" in r["fiche"]["motif"]
    assert r["coherence"]["verdict"] == "contradiction"


# ---------------------------------------------------------------- le temps du modèle, du partenaire et du code (09/10)

def avec_jetons(fabrique: Any) -> Any:
    """Le faux modèle, mais chaque réponse porte ses jetons, comme l'appel réel (lecteurs.Reponse)."""
    from kaldera.agents.coherence import Interpretation
    from kaldera.extraction.lecteurs import ContratLu, FactureLue, Reponse

    jetons = {ContratLu: (300, 40), FactureLue: (600, 20), Interpretation: (900, 30)}

    def nouvelle() -> Any:
        appeler = fabrique()

        def compte(consigne: str, schema: type, images: Any = None, *, delai_s: float | None = None) -> Any:
            return Reponse(appeler(consigne, schema, images, delai_s=delai_s), *jetons[schema])
        return compte
    return nouvelle


def test_le_poste_separe_le_temps_du_modele_celui_du_partenaire_et_celui_du_code() -> None:
    appels, consulter = compteur()
    client = TestClient(creer_app(partenaire_url=None, consulter=consulter,
                                  lecteurs={"modele": avec_jetons(faux_modele_coherence())}))
    lu = client.post("/api/lire", json={"dossier": "KAL-26-0201", "mode": "modele"}).json()
    durees = client.post("/api/decider", json=confirmer(lu)).json()["durees"]
    # contrat, facture et cohérence : trois appels au modèle ; la photo est jugée par le code (netteté)
    assert (durees["modele"]["appels"], durees["modele"]["jetons_entree"], durees["modele"]["jetons_sortie"]) == (3, 1800, 90)
    assert durees["partenaire"]["appels"] == 1 and appels == [1]  # F2 : contrat de 71 jours
    assert durees["code"]["etapes"] == 4  # éligibilité, pièces, estimation, coordination
    assert all(durees[k]["ms"] >= 0 for k in ("modele", "partenaire", "code"))


def test_en_valeurs_de_reference_aucun_appel_au_modele_n_est_compte(client: TestClient) -> None:
    durees = client.post("/api/decider", json=confirmer(lire(client, "KAL-26-0201"))).json()["durees"]
    assert (durees["modele"]["appels"], durees["modele"]["jetons_entree"], durees["modele"]["ms"]) == (0, 0, 0)
