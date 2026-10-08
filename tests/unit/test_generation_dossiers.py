"""Étape E1 : les pièces non structurées générées depuis les 34 demandes des scénarios.

Le JSON des scénarios est la vérité. Le générateur en tire ce qu'un assureur reçoit vraiment :
un contrat en PDF, des factures et des photos en image, les dépôts de l'espace assuré.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pymupdf
import pytest
from PIL import Image, ImageFilter, ImageStat

from outils import generer_dossiers as g

DEMANDES = g.demandes_des_scenarios()


@pytest.fixture(scope="module")
def dossiers(tmp_path_factory: pytest.TempPathFactory) -> Path:
    destination = tmp_path_factory.mktemp("dossiers")
    g.generer(destination)
    return destination


def nettete(image: Path) -> float:
    """Moyenne des contours : forte pour un texte net, faible pour une image floue."""
    with Image.open(image) as img:
        return ImageStat.Stat(img.convert("L").filter(ImageFilter.FIND_EDGES)).mean[0]


def test_un_dossier_par_demande(dossiers: Path) -> None:
    assert len(DEMANDES) == 34
    assert sorted(p.name for p in dossiers.iterdir() if p.is_dir()) == sorted(DEMANDES)


def test_le_contrat_est_un_pdf_dont_le_texte_porte_les_donnees_sans_le_format_json(dossiers: Path) -> None:
    for reference, demande in DEMANDES.items():
        texte = pymupdf.open(dossiers / reference / "contrat.pdf")[0].get_text()
        contrat = demande["contrat"]
        assert contrat["numero"] in texte
        assert contrat["formule"].lower() in texte.lower()
        assert contrat["date_souscription"] not in texte  # la date est écrite comme sur un vrai contrat


def test_une_image_par_piece_et_par_depot(dossiers: Path) -> None:
    for reference, demande in DEMANDES.items():
        dossier = dossiers / reference
        assert len(list(dossier.glob("piece-*.png"))) == len(demande["pieces"])
        depots = demande.get("espace_assure", {}).get("depots", [])
        assert len(list((dossier / "depots").glob("*.png"))) == len(depots)


def test_une_facture_illisible_est_floue_et_une_facture_lisible_est_nette(dossiers: Path) -> None:
    illisible = dossiers / "KAL-26-0601" / "piece-1-facture.png"  # BCL-01 : facture illisible
    lisible = dossiers / "KAL-26-0101" / "piece-1-facture.png"  # NOM-01 : facture lisible
    assert nettete(lisible) > 3 * nettete(illisible)


def test_la_declaration_ne_contient_ni_contrat_ni_pieces(dossiers: Path) -> None:
    declaration = json.loads((dossiers / "KAL-26-0101" / "declaration.json").read_text(encoding="utf-8"))
    assert set(declaration) == {"reference", "assure", "numero_contrat", "sinistre", "historique"}


def test_la_verite_est_rangee_a_part_et_correspond_aux_scenarios(dossiers: Path) -> None:
    verite = json.loads((dossiers / "verite.json").read_text(encoding="utf-8"))
    assert set(verite) == set(DEMANDES)
    assert verite["KAL-26-0101"]["contrat"] == DEMANDES["KAL-26-0101"]["contrat"]
    assert verite["KAL-26-0101"]["fichiers"]["piece-1-facture.png"] == {"type": "facture", "lisible": True,
                                                                         "montant": 1850.0}


def test_la_generation_est_reproductible(dossiers: Path, tmp_path: Path) -> None:
    g.generer(tmp_path)

    def empreintes(racine: Path) -> dict[str, str]:
        return {str(p.relative_to(racine)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(racine.rglob("*")) if p.is_file()}

    assert empreintes(tmp_path) == empreintes(dossiers)
