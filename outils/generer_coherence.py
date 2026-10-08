"""Jeu d'évaluation du contrôle de cohérence des pièces (spec § 5) : étiquettes des 34 dossiers et 8 dossiers construits.

Étiquettes des 34 dossiers : « coherent ». Le générateur (outils/generer_dossiers.py) tire l'artisan, les travaux,
la photo et la plainte du type de sinistre déclaré, et date chaque pièce après la survenance. Vérifié à la main le
08/10 sur les quatre types : c'est ce contrôle qui a trouvé que les factures de vol remplaçaient un téléviseur jamais
déclaré (la déclaration cite un ordinateur portable et un appareil photo) ; le générateur a été corrigé.

Huit dossiers construits à partir de dossiers qui atteignent le contrôle des pièces (même contrat, même montant de
facture, référence KAL-26-07xx) :
- six contradictions franches (« non_coherent ») : une personne doit regarder la demande ;
- deux cas ambigus (« ambigu ») où crier à la contradiction serait une fausse alerte : la bonne réponse est
  « insuffisant » (une personne vérifie) ou « coherent », jamais « contradiction ».

Lancement, depuis la racine du dépôt :
    .venv\\Scripts\\python.exe -m outils.generer_coherence
Sorties : evaluation/coherence/dossiers/KAL-26-07xx/ et evaluation/coherence/attendus.json.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pymupdf

from outils.generer_dossiers import _en_lettres, _euros, _image

RACINE = Path(__file__).resolve().parents[1]
DOSSIERS = RACINE / "dossiers"
SORTIE = RACINE / "evaluation" / "coherence"
VERITE = json.loads((DOSSIERS / "verite.json").read_text(encoding="utf-8"))
PLOMBIER = ("Plomberie Durand SARL", ("Recherche et réparation de fuite", "Remplacement du parquet"))
VITRIER = ("Miroiterie du Centre", ("Dépose du vitrage endommagé", "Fourniture et pose d'un double vitrage"))


def _facture(destination: Path, artisan: str, travaux: tuple[str, str], jour: date, ttc: float) -> None:
    ht = round(ttc / 1.2, 2)
    moitie = round(ht / 2, 2)
    _image([f"FACTURE N° F{jour:%y%m}-777", artisan, f"Date : {_en_lettres(jour.isoformat())}", "",
            f"{travaux[0]} ........ {_euros(moitie)} HT", f"{travaux[1]} ........ {_euros(ht - moitie)} HT",
            f"TVA 20 % ........ {_euros(round(ttc - ht, 2))}", f"TOTAL TTC À PAYER : {_euros(ttc)}"], destination, True)


def _photo_incendie(destination: Path) -> None:
    def dessin(page: pymupdf.Page) -> None:
        page.draw_rect(pymupdf.Rect(40, 120, 760, 480), color=(0.5, 0.5, 0.5), width=4)
        page.draw_oval(pymupdf.Rect(260, 200, 560, 420), color=(0.1, 0.1, 0.1), fill=(0.1, 0.1, 0.1))
    _image(["Photo du sinistre : incendie"], destination, True, dessin_supplementaire=dessin)


def _plainte_vehicule(destination: Path, jour: date) -> None:
    _image(["RÉCÉPISSÉ DE DÉPÔT DE PLAINTE", "Commissariat de police", f"Plainte enregistrée le {_en_lettres(jour.isoformat())}",
            "Objet : vol de véhicule sur la voie publique"], destination, True)


Modifier = Callable[[Path, date, float], None]

# référence, dossier de départ (il atteint le contrôle des pièces), attendu, raison, modification des pièces
CAS: list[tuple[str, str, str, str, Modifier]] = [
    ("KAL-26-0701", "KAL-26-0101", "non_coherent", "facture de miroiterie (double vitrage) pour un dégât des eaux",
     lambda c, s, m: _facture(c / "piece-1-facture.png", VITRIER[0], VITRIER[1], s + timedelta(days=4), m)),
    ("KAL-26-0702", "KAL-26-0101", "non_coherent", "réparation de fuite facturée 20 jours avant le sinistre",
     lambda c, s, m: _facture(c / "piece-1-facture.png", PLOMBIER[0], PLOMBIER[1], s - timedelta(days=20), m)),
    ("KAL-26-0703", "KAL-26-0101", "non_coherent", "photo d'un incendie pour un dégât des eaux",
     lambda c, s, m: _photo_incendie(c / "piece-2-photo.png")),
    ("KAL-26-0704", "KAL-26-0403", "non_coherent", "facture de plomberie (fuite) pour un incendie de cuisine",
     lambda c, s, m: _facture(c / "piece-1-facture.png", PLOMBIER[0], PLOMBIER[1], s + timedelta(days=4), m)),
    ("KAL-26-0705", "KAL-26-0108", "non_coherent", "plainte pour un vol de véhicule, déclaré : cambriolage",
     lambda c, s, m: _plainte_vehicule(c / "piece-2-depot_plainte.png", s + timedelta(days=1))),
    ("KAL-26-0706", "KAL-26-0206", "non_coherent", "facture de plomberie pour une baie vitrée brisée",
     lambda c, s, m: _facture(c / "piece-1-facture.png", PLOMBIER[0], PLOMBIER[1], s + timedelta(days=4), m)),
    ("KAL-26-0707", "KAL-26-0108", "ambigu", "facture d'achat des biens volés, datée six mois avant le vol",
     lambda c, s, m: _facture(c / "piece-1-facture.png", "Informatique Plus",
                              ("Achat d'un ordinateur portable", "Achat d'un appareil photo"), s - timedelta(days=180), m)),
    ("KAL-26-0708", "KAL-26-0101", "ambigu", "facture vague de fournitures, sans détail des travaux",
     lambda c, s, m: _facture(c / "piece-1-facture.png", "Bricolage Express",
                              ("Fournitures diverses", "Fournitures diverses"), s + timedelta(days=4), m)),
]


def _copier(base: str, reference: str) -> tuple[Path, dict[str, Any]]:
    cible = SORTIE / "dossiers" / reference
    if cible.exists():
        shutil.rmtree(cible)
    shutil.copytree(DOSSIERS / base, cible)
    declaration = json.loads((cible / "declaration.json").read_text(encoding="utf-8"))
    declaration["reference"] = reference
    (cible / "declaration.json").write_text(json.dumps(declaration, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8")
    return cible, declaration


def construire() -> dict[str, dict[str, str]]:
    attendus = {reference: {"attendu": "coherent", "raison": "artisan, travaux, photo et plainte du sinistre déclaré, "
                                                            "pièces datées après la survenance"}
                for reference in sorted(VERITE)}
    for reference, base, attendu, raison, modifier in CAS:
        cible, declaration = _copier(base, reference)
        survenance = date.fromisoformat(declaration["sinistre"]["date_survenance"])
        modifier(cible, survenance, VERITE[base]["fichiers"]["piece-1-facture.png"]["montant"])
        attendus[reference] = {"attendu": attendu, "raison": raison, "base": base}
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / "attendus.json").write_text(json.dumps(attendus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return attendus


if __name__ == "__main__":
    compte: dict[str, int] = {}
    for valeur in construire().values():
        compte[valeur["attendu"]] = compte.get(valeur["attendu"], 0) + 1
    print(json.dumps(compte, ensure_ascii=False))
