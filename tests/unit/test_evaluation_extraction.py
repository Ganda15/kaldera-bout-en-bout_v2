"""Étape E4 : l'évaluation de l'extraction, testée avec des faux modèles (aucun réseau).

Le rapport est généré depuis les mesures, jamais écrit à la main, et `verifier` prouve qu'il correspond aux données.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from kaldera.agents.coherence import Interpretation
from kaldera.extraction.lecteurs import ContratLu, FactureLue, Reponse
from outils import evaluer_extraction as ev
from tests.faux_coherence import interpretation

RACINE = Path(__file__).resolve().parents[2]
DOSSIERS = RACINE / "dossiers"
VERITE = json.loads((DOSSIERS / "verite.json").read_text(encoding="utf-8"))


def faux_modele(erreur_formule: str | None = None, panne: bool = False, jetons: tuple[int, int] | None = None) -> Any:
    contrats = {v["contrat"]["numero"]: v["contrat"] for v in VERITE.values()}
    factures = {hashlib.sha256((DOSSIERS / ref / nom).read_bytes()).hexdigest(): f
                for ref, v in VERITE.items() for nom, f in v["fichiers"].items() if f["type"] == "facture"}

    def appeler(consigne: str, schema: type[BaseModel], image_png: bytes | None = None, *,
                delai_s: float | None = None) -> Any:
        if panne:
            raise ConnectionError("modèle injoignable")
        if schema is Interpretation:
            return interpretation(consigne)
        if schema is ContratLu:
            vrai = dict(contrats[re.search(r"CTR-\d{6}", consigne).group(0)])
            if erreur_formule and vrai["numero"] == erreur_formule:
                vrai["formule"] = "premium" if vrai["formule"] != "premium" else "confort"
            lu: Any = ContratLu(**vrai)
        else:
            lu = FactureLue(lisible=True, montant_total_ttc=factures[hashlib.sha256(image_png).hexdigest()]["montant"])
        return Reponse(lu, *jetons) if jetons else lu
    return appeler


def test_avec_un_modele_parfait_tout_est_juste_et_le_verdict_est_reussi() -> None:
    resultats = ev.evaluer(DOSSIERS, faux_modele())
    synthese = resultats["synthese"]
    assert synthese["dossiers"] == 34
    assert all(champ["justes"] == champ["total"] for champ in synthese["champs"].values())
    assert synthese["decisions_identiques"] == {"justes": 34, "total": 34}
    assert synthese["extractions_impossibles"] == 0
    assert synthese["verdict"] == "réussi"


def test_une_erreur_de_lecture_est_comptee_sur_le_bon_champ() -> None:
    resultats = ev.evaluer(DOSSIERS, faux_modele(erreur_formule="CTR-778805"))  # NOM-05, formule essentiel
    champs = resultats["synthese"]["champs"]
    assert champs["contrat.formule"] == {"justes": 33, "total": 34, "taux": round(33 / 34, 4)}
    assert champs["contrat.numero"]["justes"] == 34
    erreurs = [e for e in resultats["details"] if e["erreurs"]]
    assert [e["reference"] for e in erreurs] == ["KAL-26-0105"]


def test_un_modele_en_panne_donne_un_verdict_echoue() -> None:
    synthese = ev.evaluer(DOSSIERS, faux_modele(panne=True))["synthese"]
    assert synthese["extractions_impossibles"] == 34
    assert synthese["verdict"] == "échoué"


def test_le_rapport_est_genere_et_verifie(tmp_path: Path) -> None:
    resultats = ev.evaluer(DOSSIERS, faux_modele(erreur_formule="CTR-778805"))
    ev.ecrire_rapport(resultats, tmp_path)
    rapport = (tmp_path / "rapport.md").read_text(encoding="utf-8")
    assert "33/34" in rapport and "KAL-26-0105" in rapport
    assert ev.verifier(tmp_path) == []


def test_un_rapport_retouche_a_la_main_est_detecte(tmp_path: Path) -> None:
    ev.ecrire_rapport(ev.evaluer(DOSSIERS, faux_modele(erreur_formule="CTR-778805")), tmp_path)
    rapport = tmp_path / "rapport.md"
    rapport.write_text(rapport.read_text(encoding="utf-8").replace("33/34", "34/34"), encoding="utf-8")
    assert ev.verifier(tmp_path) != []


def test_la_consommation_de_jetons_et_les_metriques_de_lecture_sont_mesurees(tmp_path: Path) -> None:
    resultats = ev.evaluer(DOSSIERS, faux_modele(jetons=(400, 30)))
    synthese = resultats["synthese"]
    assert synthese["jetons"] == {"entree": 67 * 400, "sortie": 67 * 30}  # 34 contrats et 33 factures nettes
    lecture = synthese["metriques_lecture"]
    assert lecture["lecteur_contrat"]["appels_externes"] == 34 and lecture["lecteur_pieces"]["appels_externes"] == 33
    ev.ecrire_rapport(resultats, tmp_path)
    assert "Jetons" in (tmp_path / "rapport.md").read_text(encoding="utf-8")
    assert ev.verifier(tmp_path) == []
