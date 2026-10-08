"""Étape E1 : génère, depuis les 34 demandes de eval/scenarios.jsonl, les pièces non structurées qu'un assureur
reçoit vraiment. Le JSON des scénarios reste la vérité ; les agents de lecture ne la voient jamais.

Pour chaque demande, dans dossiers/<référence>/ :
- contrat.pdf : conditions particulières, rédigées comme un vrai contrat (3 mises en page, dates en toutes lettres) ;
- piece-<n>-<type>.png : chaque pièce jointe (facture, photo, dépôt de plainte), floutée si elle est illisible ;
- depots/<n>-<type>.png : les dépôts de l'espace assuré, dans l'ordre ;
- declaration.json : le formulaire en ligne rempli par l'assuré (sans contrat ni pièces), et l'historique tenu par
  l'assureur.
dossiers/verite.json : les valeurs attendues de chaque fichier, pour l'évaluation de l'extraction (étape E4).

Reproductible : mêmes entrées, mêmes octets. Lancement depuis la racine du dépôt :
    .venv\\Scripts\\python.exe -m outils.generer_dossiers
"""

from __future__ import annotations

import io
import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pymupdf
from PIL import Image, ImageFilter

RACINE = Path(__file__).resolve().parents[1]
SCENARIOS = RACINE / "eval" / "scenarios.jsonl"
SORTIE = RACINE / "dossiers"
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre"]
FLOU_ILLISIBLE = 7
ARTISANS = {"degat_des_eaux": "Plomberie Durand SARL", "incendie": "Rénov'Habitat SAS",
            "bris_de_glace": "Miroiterie du Centre", "vol": "Électroménager Bonprix"}
TRAVAUX = {"degat_des_eaux": ("Recherche et réparation de fuite", "Remplacement du parquet"),
           "incendie": ("Déblaiement et nettoyage", "Remise en état des murs et plafonds"),
           "bris_de_glace": ("Dépose du vitrage endommagé", "Fourniture et pose d'un double vitrage"),
           "vol": ("Remplacement d'un téléviseur", "Remplacement d'un ordinateur portable")}
STATUTS = {"actif": "en vigueur", "suspendu": "suspendu", "resilie": "résilié"}


def demandes_des_scenarios() -> dict[str, dict[str, Any]]:
    return {d["reference"]: d for ligne in SCENARIOS.read_text(encoding="utf-8").splitlines() if ligne.strip()
            for d in json.loads(ligne)["demandes"]}


def _en_lettres(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {MOIS[d.month - 1]} {d.year}"


def _euros(montant: float) -> str:
    entier, centimes = f"{montant:,.2f}".split(".")
    return f"{entier.replace(',', ' ')},{centimes} EUR"


def _contrat_pdf(demande: dict[str, Any], destination: Path, alea: random.Random) -> None:
    contrat, assure = demande["contrat"], demande["assure"]
    souscription = date.fromisoformat(contrat["date_souscription"])
    variantes = [
        ["KALDERA ASSURANCES", "Conditions particulières de votre contrat habitation", "",
         f"Contrat n° {contrat['numero']}", f"Souscripteur : {assure['prenom']} {assure['nom']}",
         f"Adresse du bien assuré : {assure['adresse']}", "",
         f"Formule souscrite : {contrat['formule'].capitalize()}",
         f"Date d'effet : {_en_lettres(contrat['date_souscription'])}",
         f"Statut du contrat : {STATUTS[contrat['statut']]}",
         f"Cotisations : {'à jour' if contrat['cotisations_a_jour'] else 'impayées à ce jour'}"],
        ["Kaldera Assurances - Habitation", "", f"Référence contrat : {contrat['numero']}",
         f"Assuré : M. ou Mme {assure['nom'].upper()} {assure['prenom']}",
         f"Votre formule : {contrat['formule'].upper()}",
         f"Souscrit le {souscription:%d/%m/%Y}", "",
         f"Situation : contrat {STATUTS[contrat['statut']]}",
         f"Échéancier : {'aucun impayé' if contrat['cotisations_a_jour'] else 'cotisations impayées'}"],
        ["CONDITIONS PARTICULIÈRES", "Assurance multirisque habitation", "",
         f"N° de police : {contrat['numero']}", f"Titulaire : {assure['prenom']} {assure['nom']}",
         f"Niveau de garantie : formule {contrat['formule']}",
         f"Prise d'effet au {souscription:%d.%m.%Y}",
         f"État du contrat : {STATUTS[contrat['statut']]}",
         f"Paiement des primes : {'régulier' if contrat['cotisations_a_jour'] else 'en retard'}"],
    ]
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for ligne in variantes[alea.randrange(len(variantes))]:
        if ligne:
            page.insert_text((60, y), ligne, fontname="helv", fontsize=11)
        y += 20
    doc.set_metadata({"producer": "Kaldera", "creator": "Kaldera", "creationDate": "D:20260101000000",
                      "modDate": "D:20260101000000"})
    destination.write_bytes(doc.tobytes(garbage=3, deflate=True, no_new_id=True))


def _image(lignes: list[str], destination: Path, lisible: bool, taille: tuple[int, int] = (800, 520),
           dessin_supplementaire: Any = None) -> None:
    """Dessine avec le moteur PDF (police intégrée, accents compris, identique sur toutes les machines),
    puis convertit en PNG ; floute la pièce si elle est illisible."""
    doc = pymupdf.open()
    page = doc.new_page(width=taille[0], height=taille[1])
    y = 50
    for i, ligne in enumerate(lignes):
        page.insert_text((40, y), ligne, fontname="helv", fontsize=26 if i == 0 else 20)
        y += 46 if i == 0 else 34
    if dessin_supplementaire:
        dessin_supplementaire(page)
    png = page.get_pixmap(dpi=72).tobytes("png")
    img = Image.open(io.BytesIO(png)).convert("RGB")
    if not lisible:
        img = img.filter(ImageFilter.GaussianBlur(FLOU_ILLISIBLE))
    img.save(destination, format="PNG", optimize=False)


def _piece(piece: dict[str, Any], demande: dict[str, Any], numero: int, destination: Path) -> None:
    sinistre = demande["sinistre"]
    jour = date.fromisoformat(sinistre["date_survenance"]) + timedelta(days=3 + numero)
    if piece["type"] == "facture":
        ttc = float(piece["montant"])
        ht = round(ttc / 1.2, 2)
        travaux = TRAVAUX[sinistre["type"]]
        moitie = round(ht / 2, 2)
        _image([f"FACTURE N° F{jour:%y%m}-{numero:03d}", ARTISANS[sinistre["type"]],
                f"Date : {_en_lettres(jour.isoformat())}", "",
                f"{travaux[0]} ........ {_euros(moitie)} HT", f"{travaux[1]} ........ {_euros(ht - moitie)} HT",
                f"TVA 20 % ........ {_euros(round(ttc - ht, 2))}", f"TOTAL TTC À PAYER : {_euros(ttc)}"],
               destination, piece["lisible"])
    elif piece["type"] == "photo":
        def degat(page: pymupdf.Page) -> None:
            page.draw_rect(pymupdf.Rect(40, 120, 760, 480), color=(0.5, 0.5, 0.5), width=4)
            couleur = {"degat_des_eaux": (0.27, 0.51, 0.71), "incendie": (0.1, 0.1, 0.1),
                       "bris_de_glace": (0.68, 0.85, 0.9), "vol": (0.83, 0.83, 0.83)}[sinistre["type"]]
            page.draw_oval(pymupdf.Rect(260, 200, 560, 420), color=couleur, fill=couleur)
        _image([f"Photo du sinistre : {sinistre['type'].replace('_', ' ')}"], destination, piece["lisible"],
               dessin_supplementaire=degat)
    else:
        _image(["RÉCÉPISSÉ DE DÉPÔT DE PLAINTE", "Commissariat de police",
                f"Plainte enregistrée le {_en_lettres(jour.isoformat())}", "Objet : vol au domicile"],
               destination, piece["lisible"])


def generer(destination: Path = SORTIE) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    verite: dict[str, Any] = {}
    for reference, demande in sorted(demandes_des_scenarios().items()):
        alea = random.Random(reference)  # même référence, mêmes choix : reproductible
        dossier = destination / reference
        (dossier / "depots").mkdir(parents=True, exist_ok=True)
        _contrat_pdf(demande, dossier / "contrat.pdf", alea)
        fichiers: dict[str, Any] = {}
        for n, piece in enumerate(demande["pieces"], start=1):
            nom = f"piece-{n}-{piece['type']}.png"
            _piece(piece, demande, n, dossier / nom)
            fichiers[nom] = piece
        for n, depot in enumerate(demande.get("espace_assure", {}).get("depots", []), start=1):
            nom = f"depots/{n}-{depot['type']}.png"
            _piece(depot, demande, 10 + n, dossier / nom)
            fichiers[nom] = depot
        declaration = {"reference": reference, "assure": demande["assure"],
                       "numero_contrat": demande["contrat"]["numero"], "sinistre": demande["sinistre"],
                       "historique": demande["historique"]}
        (dossier / "declaration.json").write_text(json.dumps(declaration, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
        verite[reference] = {"contrat": demande["contrat"], "fichiers": fichiers}
    (destination / "verite.json").write_text(json.dumps(verite, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8")
    return destination


if __name__ == "__main__":
    print("dossiers générés dans", generer())
