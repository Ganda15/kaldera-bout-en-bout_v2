"""Filtre des données sortantes (contrat partenaire § 2) : sept champs exactement, rien d'autre ne part."""

from __future__ import annotations

import pytest

from kaldera.a2a.filtre import RequeteNonConforme, construire_donnees, departement

CHAMPS_CONTRAT = {"reference_dossier", "type_sinistre", "montant_declare", "date_survenance",
                  "anciennete_contrat_jours", "sinistres_12_mois", "departement"}

ENTREE = {"reference": "KAL-26-0042", "type_sinistre": "degat_des_eaux", "date_survenance": "2026-08-14",
          "montant_declare": 1850.0, "anciennete_contrat_jours": 942, "sinistres_12_mois": 0,
          "code_postal": "69003"}


def test_le_message_porte_exactement_les_sept_champs_du_contrat():
    donnees = construire_donnees(**ENTREE)
    assert donnees == {"reference_dossier": "KAL-26-0042", "type_sinistre": "degat_des_eaux",
                       "montant_declare": 1850.0, "date_survenance": "2026-08-14",
                       "anciennete_contrat_jours": 942, "sinistres_12_mois": 0, "departement": "69"}
    assert set(donnees) == CHAMPS_CONTRAT


def test_le_code_postal_complet_ne_part_jamais():
    assert "69003" not in str(construire_donnees(**ENTREE))


def test_une_donnee_en_plus_est_refusee_avant_tout_envoi():
    """Liste blanche : une donnée non prévue (ici le nom) ne peut pas entrer dans le message."""
    with pytest.raises(TypeError):
        construire_donnees(**ENTREE, nom="Durand")


@pytest.mark.parametrize("code_postal, attendu", [
    ("69003", "69"), ("01000", "01"), ("20000", "2A"), ("20190", "2A"), ("20200", "2B"), ("20600", "2B"),
    ("97400", "974"), ("98800", "988"),
])
def test_departement_depuis_le_code_postal(code_postal, attendu):
    assert departement(code_postal) == attendu


@pytest.mark.parametrize("champ, valeur", [
    ("reference", "KAL-2026-42"),          # forme KAL-AA-NNNN
    ("type_sinistre", "tempete"),          # hors des quatre valeurs du contrat
    ("type_sinistre", "vol Jean Durand"),  # valeur détournée dans un champ texte
    ("montant_declare", 0),                # strictement positif
    ("montant_declare", float("nan")),
    ("montant_declare", "1850"),           # un nombre, pas une chaîne
    ("date_survenance", "14/08/2026"),     # AAAA-MM-JJ
    ("date_survenance", "2026-02-30"),     # date qui n'existe pas
    ("anciennete_contrat_jours", -1),      # >= 0
    ("anciennete_contrat_jours", True),    # un entier, pas un booléen
    ("sinistres_12_mois", 1.5),            # un entier
    ("code_postal", "6900"),               # cinq chiffres
    ("code_postal", "69003 Lyon"),         # adresse glissée dans le code postal
])
def test_une_valeur_non_conforme_est_refusee_et_rien_ne_part(champ, valeur):
    with pytest.raises(RequeteNonConforme):
        construire_donnees(**{**ENTREE, champ: valeur})
