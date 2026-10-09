"""Chemin public complet, contre le partenaire simulé fourni (`external_agent`), par le vrai réseau local.

Complète la suite d'acceptance sur ce qu'elle ne montre pas : aucune requête quand le filtre refuse, un doublon
(HTTP 200 portant une erreur JSON-RPC), le contenu écarté absent de la trace aussi, et un seul budget de 10 s qui
traverse la lecture des pièces, la Coordination et l'appel au partenaire.
"""

from __future__ import annotations

import copy
import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
import uvicorn

import kaldera
from kaldera.bornes import Bornes
from kaldera.extraction.dossier import traiter_dossier
from kaldera.agents.coherence import Interpretation
from kaldera.extraction.lecteurs import ContratLu, FactureLue
from tests.faux_coherence import interpretation

RACINE = Path(__file__).resolve().parents[2]
DEMANDES = {d["reference"]: d for ligne in (RACINE / "eval" / "scenarios.jsonl").read_text(encoding="utf-8").splitlines()
            if ligne.strip() for d in json.loads(ligne)["demandes"]}
JETON = "jeton-integration"


@pytest.fixture(scope="module")
def partenaire() -> Any:
    os.environ["PARTENAIRE_JETON"] = JETON
    from external_agent.app import app

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    serveur = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", ws="none"))
    threading.Thread(target=serveur.run, daemon=True).start()
    limite = time.monotonic() + 10
    while not serveur.started:
        assert time.monotonic() < limite, "le partenaire simulé n'a pas démarré"
        time.sleep(0.05)
    url = f"http://127.0.0.1:{port}"
    pilote = httpx.Client(base_url=url, timeout=10)
    yield url, pilote
    serveur.should_exit = True


def preparer(pilote: httpx.Client, **reglage: Any) -> None:
    pilote.post("/_sim/reset").raise_for_status()
    pilote.post("/_sim/mode", json=reglage).raise_for_status()


def journal(pilote: httpx.Client) -> list[dict[str, Any]]:
    return pilote.get("/_sim/journal").json()


def test_une_demande_valide_arrive_au_partenaire_par_le_filtre(partenaire: Any) -> None:
    url, pilote = partenaire
    preparer(pilote, mode="normal")
    fiche = kaldera.traiter_demande(DEMANDES["KAL-26-0201"], partenaire_url=url)  # AF-01
    (appel,) = journal(pilote)
    assert appel["conforme"] and appel["statut_http"] == 200 and len(appel["champs"]) == 7
    assert fiche["avis_fraude"]["score"] == appel["reponse"]["result"]["artifacts"][0]["parts"][0]["data"]["score"]


def test_une_requete_refusee_par_le_filtre_ne_fait_aucun_appel(partenaire: Any) -> None:
    url, pilote = partenaire
    preparer(pilote, mode="normal")
    demande = copy.deepcopy(DEMANDES["KAL-26-0502"])  # PAN-02 : un indicateur, 950 €
    demande["assure"]["code_postal"] = "6900"  # code postal mal formé : le filtre refuse
    fiche = kaldera.traiter_demande(demande, partenaire_url=url)
    assert journal(pilote) == []
    assert (fiche["decision"], fiche["mode_degrade"], fiche["avis_fraude"]) == ("acceptee", True, None)


def test_une_reponse_tardive_ne_change_pas_une_issue_deja_rendue(partenaire: Any) -> None:
    url, pilote = partenaire
    preparer(pilote, mode="lent", delai_s=4.0)
    debut = time.perf_counter()
    fiche = kaldera.traiter_demande(DEMANDES["KAL-26-0502"], partenaire_url=url)
    duree = time.perf_counter() - debut
    figee = json.dumps(fiche, ensure_ascii=False, sort_keys=True)
    assert 2.9 < duree < 3.5, duree  # abandon à 3 s (contrat § 5)
    assert (fiche["decision"], fiche["mode_degrade"], fiche["avis_fraude"]) == ("acceptee", True, None)
    time.sleep(1.5)  # la réponse du partenaire arrive pendant ce temps : personne ne la lit
    assert json.dumps(fiche, ensure_ascii=False, sort_keys=True) == figee


def test_un_http_200_portant_une_erreur_json_rpc_est_une_erreur(partenaire: Any) -> None:
    url, pilote = partenaire
    preparer(pilote, mode="normal")
    kaldera.traiter_demande(DEMANDES["KAL-26-0502"], partenaire_url=url)
    seconde = kaldera.traiter_demande(DEMANDES["KAL-26-0502"], partenaire_url=url)  # autre exécution : doublon
    appels = journal(pilote)
    assert len(appels) == 2 and appels[1]["doublon"] and appels[1]["statut_http"] == 200
    assert appels[1]["reponse"]["error"]["code"] == -32029
    assert (seconde["avis_fraude"], seconde["mode_degrade"]) == (None, True)


@pytest.mark.parametrize("variante", ["champ_hors_contrat", "score_hors_bornes", "reference_differente",
                                      "enveloppe_invalide"])
def test_le_contenu_ecarte_n_est_ni_dans_la_fiche_ni_dans_la_trace(partenaire: Any, variante: str) -> None:
    url, pilote = partenaire
    preparer(pilote, mode="invalide", variante=variante)
    fiche = kaldera.traiter_demande(DEMANDES["KAL-26-0502"], partenaire_url=url)
    tout = json.dumps(fiche, ensure_ascii=False)  # trace comprise
    for interdit in ("EVA-NC", "rembourser", "commentaire", "KAL-26-9999"):
        assert interdit not in tout, (variante, interdit)
    assert fiche["avis_fraude"] is None and fiche["mode_degrade"] is True


def test_un_seul_budget_traverse_lecture_coordination_et_partenaire(partenaire: Any) -> None:
    url, pilote = partenaire
    preparer(pilote, mode="lent", delai_s=5.0)
    verite = json.loads((RACINE / "dossiers" / "verite.json").read_text(encoding="utf-8"))["KAL-26-0502"]

    def lecture_lente(consigne: str, schema: type, image_png: bytes | None = None, *,
                      delai_s: float | None = None) -> Any:
        time.sleep(0.3)  # un appel au modèle qui prend du temps
        if schema is ContratLu:
            return ContratLu(**verite["contrat"])
        if schema is Interpretation:
            return interpretation(consigne)
        montant = next(f["montant"] for f in verite["fichiers"].values() if f["type"] == "facture")
        return FactureLue(lisible=True, montant_total_ttc=montant)

    budget = Bornes(duree_max_s=2.0, reserve_fiche_s=0.5)  # budget réduit pour un test rapide
    debut = time.perf_counter()
    resultat = traiter_dossier(RACINE / "dossiers" / "KAL-26-0502", lecture_lente,
                               consulter=kaldera.client_a2a.partenaire_a2a(url), bornes=budget)
    duree = time.perf_counter() - debut
    assert duree < budget.duree_max_s, duree  # le partenaire n'a reçu que le reste, pas 3 s de plus
    assert len(journal(pilote)) == 1
    assert (resultat["fiche"]["decision"], resultat["fiche"]["mode_degrade"]) == ("acceptee", True)
