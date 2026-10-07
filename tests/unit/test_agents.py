"""Les quatre agents, testés seuls sur les demandes des scénarios du client (eval/scenarios.jsonl)."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from kaldera.agents.antifraude import evaluer_risque
from kaldera.agents.eligibilite import verifier_eligibilite
from kaldera.agents.estimation import estimer
from kaldera.agents.pieces import demander_complement, verifier_pieces

SCENARIOS = Path(__file__).resolve().parents[2] / "eval" / "scenarios.jsonl"
DEMANDES = {
    d["reference"]: d
    for ligne in SCENARIOS.read_text(encoding="utf-8").splitlines() if ligne.strip()
    for d in json.loads(ligne)["demandes"]
}


def demande(reference: str) -> dict[str, Any]:
    return DEMANDES[reference]


# ---------------------------------------------------------------- frontières (E2, E3)

DONNEES_PERSONNELLES = {"assure", "nom", "prenom", "email", "telephone", "iban", "adresse",
                        "id_client", "numero", "description", "demande"}


@pytest.mark.parametrize("agent", [verifier_eligibilite, verifier_pieces, demander_complement,
                                   estimer, evaluer_risque])
def test_aucun_agent_ne_recoit_de_donnee_personnelle_ni_la_demande_entiere(agent: Any) -> None:
    assert not set(inspect.signature(agent).parameters) & DONNEES_PERSONNELLES


def test_l_antifraude_recoit_exactement_huit_donnees() -> None:
    parametres = set(inspect.signature(evaluer_risque).parameters) - {"consulter"}
    assert parametres == {"reference", "type_sinistre", "date_survenance", "montant_declare",
                          "date_souscription", "sinistres_12_mois", "code_postal", "montant_justifie"}


# ---------------------------------------------------------------- Éligibilité (§ 4)

@pytest.mark.parametrize(("reference", "condition"), [
    ("KAL-26-0102", "E1"),  # NOM-02 : contrat résilié
    ("KAL-26-0111", "E2"),  # NOM-11 : cotisations impayées
    ("KAL-26-0104", "E3"),  # NOM-04 : sinistre 16 jours après la souscription
    ("KAL-26-0110", "E4"),  # NOM-10 : déclaré 44 jours après
    ("KAL-26-0103", "E5"),  # NOM-03 : vol sur une formule essentiel
])
def test_eligibilite_cite_la_condition_non_remplie(reference: str, condition: str) -> None:
    d = demande(reference)
    resultat = verifier_eligibilite(d["contrat"], d["sinistre"])
    assert not resultat.eligible
    assert [c[:2] for c in resultat.conditions_non_remplies] == [condition]


def test_eligibilite_nominale() -> None:
    d = demande("KAL-26-0101")
    assert verifier_eligibilite(d["contrat"], d["sinistre"]).eligible


# ---------------------------------------------------------------- Pièces et complément (§ 5)

def test_pieces_completes_et_factures_lisibles() -> None:
    resultat = verifier_pieces("degat_des_eaux", demande("KAL-26-0101")["pieces"])
    assert resultat.complet and resultat.factures_lisibles == [1850.0]


@pytest.mark.parametrize(("reference", "manquante"), [("KAL-26-0109", "photo"),  # NOM-09 : absente
                                                       ("KAL-26-0601", "facture")])  # BCL-01 : illisible
def test_piece_absente_ou_illisible_est_manquante(reference: str, manquante: str) -> None:
    d = demande(reference)
    assert verifier_pieces(d["sinistre"]["type"], d["pieces"]).manquantes == [manquante]


def _complement(reference: str) -> Any:
    d = demande(reference)
    return demander_complement(d["sinistre"]["type"], d["pieces"], d["espace_assure"]["depots"], 0)


@pytest.mark.parametrize("reference", ["KAL-26-0107", "KAL-26-0405"])  # NOM-07, PAN-01 : photo déposée
def test_le_complement_depose_rend_les_pieces_completes(reference: str) -> None:
    resultat = _complement(reference)
    assert resultat.complet and resultat.sans_depot == []


def test_sans_aucun_depot_du_type_demande_le_complement_le_signale() -> None:  # NOM-09
    resultat = _complement("KAL-26-0109")
    assert not resultat.complet and resultat.sans_depot == ["photo"]


def test_un_depot_illisible_laisse_la_meme_piece_manquante() -> None:  # BCL-01, piège à boucle
    d = demande("KAL-26-0601")
    avant = verifier_pieces(d["sinistre"]["type"], d["pieces"])
    apres = _complement("KAL-26-0601")
    assert apres.sans_depot == [] and apres.manquantes == avant.manquantes == ["facture"]


def test_le_complement_ne_modifie_pas_la_demande_recue() -> None:
    d = demande("KAL-26-0107")
    pieces_avant = list(d["pieces"])
    _complement("KAL-26-0107")
    assert d["pieces"] == pieces_avant


# ---------------------------------------------------------------- Estimation (§ 6)

@pytest.mark.parametrize(("reference", "attendu"), [
    ("KAL-26-0101", 1700.0),  # NOM-01 : 1 850 - 150
    ("KAL-26-0105", 3000.0),  # NOM-05 : plafonné, point ambigu
    ("KAL-26-0106", 0.0),  # NOM-06 : 140 € sous la franchise de 150 €
    ("KAL-26-0108", 1650.0),  # NOM-08 : facture 1 800 < déclaré 1 900, retenu 1 800 - 150
])
def test_estimation_des_scenarios(reference: str, attendu: float) -> None:
    d = demande(reference)
    factures = verifier_pieces(d["sinistre"]["type"], d["pieces"]).factures_lisibles
    assert estimer(d["sinistre"]["montant_declare"], d["contrat"]["formule"], factures).montant_estime == attendu


# ---------------------------------------------------------------- Anti-fraude (§ 7)

def _avis(reference: str) -> Any:
    d = demande(reference)
    justifie = verifier_pieces(d["sinistre"]["type"], d["pieces"]).factures_lisibles
    return evaluer_risque(reference=reference, type_sinistre=d["sinistre"]["type"],
                          date_survenance=d["sinistre"]["date_survenance"],
                          montant_declare=d["sinistre"]["montant_declare"],
                          date_souscription=d["contrat"]["date_souscription"],
                          sinistres_12_mois=d["historique"]["sinistres_12_mois"],
                          code_postal=d["assure"]["code_postal"], montant_justifie=sum(justifie))


def test_sans_indicateur_le_partenaire_n_est_pas_sollicite() -> None:
    assert _avis("KAL-26-0101").statut == "non_requis"


def test_af06_ecart_de_declaration_donne_f4_puis_le_bouchon_rend_indisponible() -> None:
    avis = _avis("KAL-26-0206")  # 2 000 € déclarés, 1 500 € justifiés
    assert avis.indicateurs == ["F4"]
    assert avis.statut == "indisponible" and avis.raison == "partenaire_non_branche"
