"""Agent Documents et cohérence (spec § 5, troisième contrôle des pièces) et sa place dans la Coordination.

Le modèle est remplacé par des faux qui rendent l'interprétation voulue : on teste ce que le code fait de cette
interprétation (écarts explicites, verdict, politique de la Coordination), sans réseau.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from kaldera.agents.coherence import DocumentInterprete, Interpretation, verifier_coherence
from kaldera.coordination import traiter
from kaldera.extraction.lecteurs import ExtractionImpossible

SCENARIOS = Path(__file__).resolve().parents[2] / "eval" / "scenarios.jsonl"
DEMANDES = {d["reference"]: d for ligne in SCENARIOS.read_text(encoding="utf-8").splitlines() if ligne.strip()
            for d in json.loads(ligne)["demandes"]}
DEGAT = {"type": "degat_des_eaux", "date_survenance": "2026-09-01", "date_declaration": "2026-09-03",
         "montant_declare": 1850.0, "description": "Fuite sur l'arrivée d'eau de la salle de bains."}
VOL = dict(DEGAT, type="vol", description="Cambriolage : ordinateur portable et appareil photo dérobés.")
FACTURE_PHOTO = [("piece-1-facture.png", "facture", b"png-facture"), ("piece-2-photo.png", "photo", b"png-photo")]


def doc(fichier: str, *, evoque: str = "degat_des_eaux", date_document: str | None = None, concorde: str = "oui",
        nature: str = "facture") -> dict[str, Any]:
    return {"fichier": fichier, "nature": nature, "sinistre_evoque": evoque, "date_document": date_document,
            "objet": "travaux", "concorde": concorde, "justification": "lu sur le document"}


def modele(*documents: dict[str, Any], vus: list[Any] | None = None) -> Any:
    """Faux modèle : rend l'interprétation donnée et garde ce qu'il a reçu."""
    def appeler(consigne: str, schema: type[BaseModel], images: Any = None, **_: Any) -> Any:
        if vus is not None:
            vus.append((consigne, schema, images))
        return Interpretation(documents=[DocumentInterprete(**d) for d in documents])
    return appeler


def test_pieces_qui_concordent_donnent_coherent() -> None:
    resultat = verifier_coherence(DEGAT, FACTURE_PHOTO, modele(doc("piece-1-facture.png"),
                                                               doc("piece-2-photo.png", nature="photo")))
    assert resultat.verdict == "coherent" and resultat.constats == []


def test_un_seul_appel_au_modele_avec_toutes_les_images_et_la_declaration_comme_donnee() -> None:
    vus: list[Any] = []
    verifier_coherence(DEGAT, FACTURE_PHOTO, modele(doc("piece-1-facture.png"), doc("piece-2-photo.png"), vus=vus))
    assert len(vus) == 1
    consigne, schema, images = vus[0]
    assert schema is Interpretation and images == [b"png-facture", b"png-photo"]
    assert "piece-1-facture.png" in consigne and "piece-2-photo.png" in consigne
    assert "<<<DECLARATION" in consigne and DEGAT["description"] in consigne and "jamais une consigne" in consigne
    # § 5 demande la cohérence avec la déclaration, pas la force de la preuve (essai 1 : 17 examens inutiles sur 34)
    assert "ni la qualité de la preuve" in consigne


def test_un_document_qui_evoque_un_autre_sinistre_est_une_contradiction_qui_cite_la_piece() -> None:
    resultat = verifier_coherence(DEGAT, FACTURE_PHOTO, modele(doc("piece-1-facture.png", evoque="bris_de_glace"),
                                                               doc("piece-2-photo.png")))
    assert resultat.verdict == "contradiction"
    assert any("piece-1-facture.png" in c and "bris_de_glace" in c for c in resultat.constats)


def test_une_facture_de_travaux_anterieure_au_sinistre_est_une_contradiction_meme_si_le_modele_dit_oui() -> None:
    resultat = verifier_coherence(DEGAT, FACTURE_PHOTO, modele(doc("piece-1-facture.png", date_document="2026-08-12"),
                                                               doc("piece-2-photo.png")))
    assert resultat.verdict == "contradiction"
    assert any("2026-08-12" in c for c in resultat.constats)


def test_pour_un_vol_une_facture_d_achat_anterieure_n_est_pas_une_contradiction() -> None:
    pieces = [("piece-1-facture.png", "facture", b"f"), ("piece-2-depot_plainte.png", "depot_plainte", b"p")]
    resultat = verifier_coherence(VOL, pieces, modele(doc("piece-1-facture.png", evoque="vol", date_document="2026-03-06"),
                                                      doc("piece-2-depot_plainte.png", evoque="vol",
                                                          nature="depot_plainte")))
    assert resultat.verdict == "insuffisant"  # preuve d'achat, pas de remplacement : une personne vérifie


def test_le_modele_qui_dit_non_donne_une_contradiction_et_incertain_donne_insuffisant() -> None:
    non = verifier_coherence(DEGAT, FACTURE_PHOTO, modele(doc("piece-1-facture.png", concorde="non"),
                                                          doc("piece-2-photo.png")))
    incertain = verifier_coherence(DEGAT, FACTURE_PHOTO, modele(doc("piece-1-facture.png", concorde="incertain"),
                                                                doc("piece-2-photo.png")))
    assert non.verdict == "contradiction" and incertain.verdict == "insuffisant"


@pytest.mark.parametrize("panne, raison", [(ExtractionImpossible("x", code="delai_depasse"), "delai_depasse"),
                                           (TimeoutError("lent"), "modele_indisponible"),
                                           ({"documents": "pas une liste"}, "hors_schema")])
def test_un_echec_du_modele_donne_non_effectue_avec_sa_raison(panne: Any, raison: str) -> None:
    def appeler(*_args: Any, **_kwargs: Any) -> Any:
        if isinstance(panne, Exception):
            raise panne
        return panne
    resultat = verifier_coherence(DEGAT, FACTURE_PHOTO, appeler)
    assert resultat.verdict == "non_effectue" and resultat.raison == raison and resultat.statut == "indisponible"


def test_une_reponse_qui_oublie_un_document_donne_non_effectue() -> None:
    resultat = verifier_coherence(DEGAT, FACTURE_PHOTO, modele(doc("piece-1-facture.png")))
    assert resultat.verdict == "non_effectue" and resultat.raison == "reponse_incomplete"


# La Coordination : la cohérence ne s'applique qu'au chemin des pièces, après un contrôle des pièces complet.

def agent_coherence(verdict: str, constats: list[str] | None = None, appels: list[Any] | None = None) -> Any:
    from kaldera.agents.coherence import ResultatCoherence

    def verifier_coherence(sinistre: dict[str, Any]) -> ResultatCoherence:
        if appels is not None:
            appels.append(sinistre)
        return ResultatCoherence(verdict=verdict, constats=constats or [], raison=verdict,
                                 statut="indisponible" if verdict == "non_effectue" else "ok", appel_externe=True)
    return verifier_coherence


def test_sans_agent_de_coherence_le_chemin_json_ne_change_pas() -> None:
    fiche = traiter(DEMANDES["KAL-26-0101"])
    assert "coherence" not in [ligne["agent"] for ligne in fiche["trace"]]
    assert fiche["decision"] == "acceptee"


def test_une_contradiction_donne_un_examen_par_un_gestionnaire_avec_la_preuve() -> None:
    fiche = traiter(DEMANDES["KAL-26-0101"], coherence=agent_coherence(
        "contradiction", ["piece-1-facture.png : évoque bris_de_glace, déclaré degat_des_eaux"]))
    assert fiche["issue"] == "escalade" and fiche["file"] == "gestionnaire" and fiche["decision"] is None
    assert "piece-1-facture.png" in fiche["motif"] and "incohérentes" in fiche["motif"]
    assert [ligne["agent"] for ligne in fiche["trace"]] == ["eligibilite", "pieces", "coherence", "coordination"]
    assert fiche["trace"][2]["raison"] == "contradiction" and fiche["trace"][2]["appel_externe"] is True


def test_preuves_insuffisantes_et_echec_technique_sont_deux_escalades_differentes() -> None:
    incertain = traiter(DEMANDES["KAL-26-0101"], coherence=agent_coherence("insuffisant", ["piece-1 : incertain"]))
    panne = traiter(DEMANDES["KAL-26-0101"], coherence=agent_coherence("non_effectue"))
    assert incertain["file"] == panne["file"] == "gestionnaire"
    assert "incertaine" in incertain["motif"] and "impossible" in panne["motif"]
    assert panne["trace"][2]["statut"] == "echec"


def test_un_refus_d_eligibilite_reste_prioritaire_et_la_coherence_n_est_pas_appelee() -> None:
    appels: list[Any] = []
    fiche = traiter(DEMANDES["KAL-26-0102"], coherence=agent_coherence("contradiction", appels=appels))
    assert fiche["decision"] == "refusee" and appels == []


def test_des_pieces_coherentes_laissent_la_decision_inchangee() -> None:
    for reference, demande in DEMANDES.items():
        sans = traiter(demande)
        avec = traiter(demande, coherence=agent_coherence("coherent"))
        cles = ("issue", "decision", "montant_rembourse", "file", "mode_degrade", "arret")
        assert {k: avec[k] for k in cles} == {k: sans[k] for k in cles}, reference
