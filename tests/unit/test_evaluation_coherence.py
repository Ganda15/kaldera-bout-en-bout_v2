"""outils/evaluer_coherence.py : le verdict de l'évaluation se calcule depuis les mesures, jamais à la main."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from kaldera.agents.coherence import Interpretation
from kaldera.extraction.lecteurs import ContratLu, FactureLue
from outils import evaluer_coherence as ev
from tests.faux_coherence import interpretation


def detail(reference: str, attendu: str, verdict: str, **autres: Any) -> dict[str, Any]:
    return {"reference": reference, "attendu": attendu, "verdict": verdict, "constats": [],
            "duree_coherence_s": 1.0, "duree_dossier_s": 5.0, "jetons_entree": 900, "jetons_sortie": 120,
            "fiche": {"issue": "decision", "file": None, "decision": "acceptee"}, "decision_attendue": True, **autres}


def test_un_agent_parfait_passe_toutes_les_portes() -> None:
    details = ([detail(f"C{i}", "coherent", "coherent") for i in range(34)]
               + [detail(f"N{i}", "non_coherent", "contradiction") for i in range(6)]
               + [detail("A1", "ambigu", "insuffisant"), detail("A2", "ambigu", "coherent")])
    s = ev.synthetiser(details)
    assert (s["detections"], s["fausses_alertes"], s["examens_inutiles"], s["echecs_techniques"]) == (
        {"justes": 6, "total": 6}, 0, 0, 0)
    assert s["verdict"] == "réussi"


def test_une_contradiction_sur_un_cas_ambigu_est_une_fausse_alerte() -> None:
    details = ([detail(f"C{i}", "coherent", "coherent") for i in range(34)]
               + [detail(f"N{i}", "non_coherent", "contradiction") for i in range(6)]
               + [detail("A1", "ambigu", "contradiction"), detail("A2", "ambigu", "coherent")])
    s = ev.synthetiser(details)
    assert s["fausses_alertes"] == 1 and s["verdict"] == "échoué"


def test_un_dossier_au_dela_de_10_s_ou_un_echec_technique_fait_echouer() -> None:
    base = ([detail(f"C{i}", "coherent", "coherent") for i in range(33)]
            + [detail(f"N{i}", "non_coherent", "contradiction") for i in range(6)]
            + [detail("A1", "ambigu", "insuffisant"), detail("A2", "ambigu", "coherent")])
    lent = ev.synthetiser(base + [detail("C33", "coherent", "coherent", duree_dossier_s=10.4)])
    panne = ev.synthetiser(base + [detail("C33", "coherent", "non_effectue")])
    assert lent["au_dela_du_budget"] == 1 and lent["verdict"] == "échoué"
    assert panne["echecs_techniques"] == 1 and panne["verdict"] == "échoué"


def faux(consigne: str, schema: type[BaseModel], images: Any = None, **_: Any) -> Any:
    """Un modèle qui dit « tout concorde » : il ne détecte rien."""
    if schema is Interpretation:
        return interpretation(consigne)
    if schema is ContratLu:
        import re
        from tests.unit.test_dossier import VERITE
        numero = re.search(r"CTR-\d{6}", consigne).group(0)
        return ContratLu(**next(v["contrat"] for v in VERITE.values() if v["contrat"]["numero"] == numero))
    return FactureLue(lisible=True, montant_total_ttc=1850.0)


def test_un_agent_qui_ne_voit_rien_echoue_et_le_rapport_se_verifie(tmp_path: Path) -> None:
    resultats = ev.evaluer(faux, paralleles=4)
    s = resultats["synthese"]
    assert s["dossiers"] == 42 and s["detections"]["justes"] == 0 and s["verdict"] == "échoué"
    ev.ecrire_rapport(resultats, tmp_path)
    assert ev.verifier(tmp_path) == []
    rapport = tmp_path / "rapport.md"
    rapport.write_text(rapport.read_text(encoding="utf-8").replace("échoué", "réussi"), encoding="utf-8")
    assert ev.verifier(tmp_path) != []
