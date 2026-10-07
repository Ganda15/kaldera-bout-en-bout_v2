"""Mémoire partagée de la demande : accès maîtrisé (brief, chantier 1 ; docs/interface.md, § Trace).

Les tests d'acceptance ne vérifient les rôles qu'à travers la trace. Ces tests prouvent la règle
elle-même : un agent, une section ; une section, un agent ; un résultat du bon type ; une trace
en ajout seul.
"""

from __future__ import annotations

import pytest

from kaldera.agents.antifraude import AvisFraude
from kaldera.agents.eligibilite import ResultatEligibilite
from kaldera.agents.estimation import ResultatEstimation
from kaldera.agents.pieces import ResultatPieces
from kaldera.etat import SECTION_DE, ErreurDeDroits, EtatDemande

SECTIONS_METIER = {"eligibilite", "pieces", "estimation", "avis_fraude", "issue"}


def nouvel_etat() -> EtatDemande:
    return EtatDemande({"reference": "KAL-TEST"})


def test_une_section_par_agent_et_un_agent_par_section() -> None:
    assert set(SECTION_DE.values()) == SECTIONS_METIER
    assert len(set(SECTION_DE.values())) == len(SECTION_DE)


def test_le_resultat_va_dans_la_section_de_son_agent_avec_une_ligne_de_trace() -> None:
    etat = nouvel_etat()
    etat.ranger("antifraude", AvisFraude(statut="non_requis"), "evaluer_risque", 0.4)
    assert etat.sections == {"avis_fraude": AvisFraude(statut="non_requis")}
    assert etat.trace == [{"agent": "antifraude", "ecrit": ["avis_fraude"], "action": "evaluer_risque",
                           "duree_ms": 0.4, "statut": "ok", "appel_externe": False}]


def test_un_agent_inconnu_est_refuse() -> None:
    with pytest.raises(ErreurDeDroits):
        nouvel_etat().ranger("generaliste", {}, "tout", 0.0)


def test_un_resultat_du_mauvais_type_est_refuse() -> None:
    # le résultat de l'Éligibilité présenté sous le nom de l'Estimation
    with pytest.raises(ErreurDeDroits):
        nouvel_etat().ranger("estimation", ResultatEligibilite(eligible=True), "estimer", 0.0)


@pytest.mark.parametrize(("agent", "resultat"), [
    ("eligibilite", ResultatEligibilite(eligible=True)),
    ("estimation", ResultatEstimation(100.0, 100.0, 0.0)),
    ("antifraude", AvisFraude(statut="non_requis")),
    ("coordination", {"issue": "decision", "motif": "test"}),
])
def test_une_section_ne_s_ecrit_qu_une_fois(agent: str, resultat: object) -> None:
    etat = nouvel_etat()
    etat.ranger(agent, resultat, "premiere", 0.0)
    with pytest.raises(ErreurDeDroits):
        etat.ranger(agent, resultat, "seconde", 0.0)
    assert len(etat.trace) == 1


def test_seule_la_section_pieces_se_reecrit_apres_un_complement() -> None:
    etat = nouvel_etat()
    etat.ranger("pieces", ResultatPieces(complet=False, manquantes=["photo"]), "verifier_pieces", 0.0)
    etat.ranger("pieces", ResultatPieces(complet=True), "demander_complement", 0.0)
    assert etat.sections["pieces"].complet
    assert [ligne["action"] for ligne in etat.trace] == ["verifier_pieces", "demander_complement"]


def test_le_statut_d_une_etape_en_echec_est_trace() -> None:
    etat = nouvel_etat()
    etat.ranger("antifraude", AvisFraude(statut="indisponible", raison="delai_depasse"),
                "evaluer_risque", 3000.0, statut="echec")
    assert etat.trace[-1]["statut"] == "echec"


def test_deux_demandes_ne_partagent_pas_leur_memoire() -> None:
    premiere, seconde = nouvel_etat(), nouvel_etat()
    premiere.ranger("eligibilite", ResultatEligibilite(eligible=True), "verifier_eligibilite", 0.0)
    assert seconde.sections == {} and seconde.trace == []


def test_les_resultats_rangés_ne_peuvent_pas_etre_modifies() -> None:
    etat = nouvel_etat()
    etat.ranger("estimation", ResultatEstimation(100.0, 100.0, 0.0), "estimer", 0.0)
    with pytest.raises(AttributeError):
        etat.sections["estimation"].montant_estime = 999.0  # type: ignore[misc]
