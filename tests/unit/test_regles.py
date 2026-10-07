"""Règles métier : chaque chiffre de regles.py comparé à specs_metier.md (version 3.2), puis les
seuils testés juste en dessous et juste au-dessus (tests de frontière)."""

from __future__ import annotations

import pytest

from kaldera import regles
from kaldera.agents.antifraude import evaluer_risque
from kaldera.agents.eligibilite import verifier_eligibilite


def test_les_constantes_sont_celles_de_la_spec() -> None:
    assert regles.VERSION_SPEC == "3.2"
    assert regles.FORMULES["essentiel"]["franchise"] == 300 and regles.FORMULES["essentiel"]["plafond"] == 3000
    assert regles.FORMULES["confort"]["franchise"] == 150 and regles.FORMULES["confort"]["plafond"] == 8000
    assert regles.FORMULES["premium"]["franchise"] == 0 and regles.FORMULES["premium"]["plafond"] == 20000
    assert regles.FORMULES["essentiel"]["garanties"] == {"degat_des_eaux", "incendie"}
    assert regles.PIECES_EXIGEES["vol"] == ("facture", "depot_plainte")  # § 5
    assert (regles.CARENCE_JOURS, regles.DELAI_DECLARATION_JOURS, regles.DELAI_DECLARATION_VOL_JOURS) == (30, 30, 5)
    assert regles.SEUIL_MONTANT_FRAUDE == 5000  # F1
    assert regles.ANCIENNETE_SENSIBLE_JOURS == 90  # F2
    assert regles.FREQUENCE_SENSIBLE == 3  # F3
    assert regles.ECART_DECLARATION_MAX == 0.20  # F4
    assert regles.SEUIL_DELEGATION == 10000  # § 8 et règle 5
    assert regles.SEUIL_MODE_DEGRADE == 1500  # § 9


# ---------------------------------------------------------------- indicateurs F1 à F4 (§ 7)

def _indicateurs(**changements: object) -> list[str]:
    donnees = dict(reference="KAL-TEST", type_sinistre="incendie", date_survenance="2026-08-14",
                   montant_declare=1000.0, date_souscription="2024-01-15", sinistres_12_mois=0,
                   code_postal="69003", montant_justifie=1000.0)
    donnees.update(changements)
    return evaluer_risque(**donnees).indicateurs


@pytest.mark.parametrize(("montant", "attendu"), [(4999.99, False), (5000.0, True)])
def test_f1_montant_declare_au_moins_5000(montant: float, attendu: bool) -> None:
    assert ("F1" in _indicateurs(montant_declare=montant, montant_justifie=montant)) is attendu


@pytest.mark.parametrize(("souscription", "attendu"), [("2026-05-17", True), ("2026-05-16", False)])
def test_f2_anciennete_inferieure_a_90_jours(souscription: str, attendu: bool) -> None:
    # du 17/05 au 14/08 : 89 jours ; du 16/05 au 14/08 : 90 jours
    assert ("F2" in _indicateurs(date_souscription=souscription)) is attendu


@pytest.mark.parametrize(("sinistres", "attendu"), [(2, False), (3, True)])
def test_f3_au_moins_3_sinistres_sur_12_mois(sinistres: int, attendu: bool) -> None:
    assert ("F3" in _indicateurs(sinistres_12_mois=sinistres)) is attendu


@pytest.mark.parametrize(("justifie", "declare"),
                         [(1250.0, 1500.0), (1000.0, 1200.0), (1234.5, 1481.4), (41.5, 49.8)])
def test_f4_un_ecart_de_20_pour_cent_pile_ne_declenche_pas(justifie: float, declare: float) -> None:
    assert "F4" not in _indicateurs(montant_declare=declare, montant_justifie=justifie)


@pytest.mark.parametrize(("justifie", "declare"), [(1250.0, 1500.01), (1234.5, 1481.41)])
def test_f4_un_centime_au_dela_de_20_pour_cent_declenche(justifie: float, declare: float) -> None:
    assert "F4" in _indicateurs(montant_declare=declare, montant_justifie=justifie)


# ---------------------------------------------------------------- éligibilité, délais (§ 4)

def _eligible(souscription: str, survenance: str, declaration: str, type_sinistre: str) -> bool:
    contrat = {"statut": "actif", "cotisations_a_jour": True, "date_souscription": souscription,
               "formule": "confort"}
    sinistre = {"type": type_sinistre, "date_survenance": survenance, "date_declaration": declaration}
    return verifier_eligibilite(contrat, sinistre).eligible


def test_e3_carence_30_jours_pile_est_eligible() -> None:
    assert _eligible("2026-07-01", "2026-07-31", "2026-07-31", "incendie")  # 30 jours
    assert not _eligible("2026-07-01", "2026-07-30", "2026-07-30", "incendie")  # 29 jours


def test_e4_declaration_30_jours_pile_et_5_jours_pour_un_vol() -> None:
    assert _eligible("2024-01-15", "2026-08-01", "2026-08-31", "incendie")  # 30 jours
    assert not _eligible("2024-01-15", "2026-08-01", "2026-09-01", "incendie")  # 31 jours
    assert _eligible("2024-01-15", "2026-08-01", "2026-08-06", "vol")  # 5 jours
    assert not _eligible("2024-01-15", "2026-08-01", "2026-08-07", "vol")  # 6 jours


# ---------------------------------------------------------------- seuils de décision (§ 8, § 9)

@pytest.mark.parametrize(("montant", "attendu"), [(10000.0, False), (10000.01, True)])
def test_seuil_de_delegation_strictement_au_dessus_de_10000(montant: float, attendu: bool) -> None:
    assert regles.depasse_seuil_delegation(montant) is attendu


@pytest.mark.parametrize(("montant", "attendu"), [(1500.0, True), (1500.01, False)])
def test_mode_degrade_continue_jusqu_a_1500_inclus(montant: float, attendu: bool) -> None:
    assert regles.continue_en_mode_degrade(montant) is attendu
