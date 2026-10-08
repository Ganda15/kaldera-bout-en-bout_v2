"""La Coordination : routage, terminaison garantie, bornes, règle 4 et mode dégradé, filet de sécurité.

Le partenaire est remplacé par des faux qui rendent l'avis voulu : la règle de décision est testée
sans réseau. Le vrai client A2A arrive au chantier 2.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from kaldera import coordination
from kaldera.agents.antifraude import AvisFraude
from kaldera.bornes import Bornes
from kaldera.coordination import RegistreAppels, traiter

SCENARIOS = Path(__file__).resolve().parents[2] / "eval" / "scenarios.jsonl"
DEMANDES = {
    d["reference"]: d
    for ligne in SCENARIOS.read_text(encoding="utf-8").splitlines() if ligne.strip()
    for d in json.loads(ligne)["demandes"]
}
CHAMPS_FICHE = {"reference", "issue", "decision", "montant_rembourse", "motif", "file",
                "avis_fraude", "mode_degrade", "trace", "arret"}


def partenaire(niveau: str | None, score: float = 0.2) -> Any:
    """Faux partenaire : rend un avis du niveau voulu, ou « indisponible » si niveau est None."""
    def consulter(**_donnees: Any) -> AvisFraude:
        if niveau is None:
            return AvisFraude(statut="indisponible", raison="service_indisponible")
        return AvisFraude(statut="avis", niveau=niveau, score=score)
    return consulter


def agents(fiche: dict[str, Any]) -> list[str]:
    return [ligne["agent"] for ligne in fiche["trace"]]


# ---------------------------------------------------------------- routage et compléments

def test_toute_fiche_porte_les_champs_du_paragraphe_11_et_de_l_interface() -> None:
    assert set(traiter(DEMANDES["KAL-26-0101"])) == CHAMPS_FICHE


def test_nom02_non_eligible_est_refusee_en_deux_etapes() -> None:
    fiche = traiter(DEMANDES["KAL-26-0102"])
    assert (fiche["decision"], fiche["montant_rembourse"]) == ("refusee", 0.0)
    assert agents(fiche) == ["eligibilite", "coordination"]


def test_nom07_photo_deposee_apres_complement_puis_acceptee() -> None:
    fiche = traiter(DEMANDES["KAL-26-0107"])
    assert (fiche["decision"], fiche["montant_rembourse"]) == ("acceptee", 2300.0)
    assert agents(fiche) == ["eligibilite", "pieces", "pieces", "estimation", "antifraude", "coordination"]


def test_nom09_aucun_depot_donne_une_escalade_pieces_manquantes() -> None:
    fiche = traiter(DEMANDES["KAL-26-0109"])
    assert (fiche["issue"], fiche["file"], fiche["arret"]) == ("escalade", "gestionnaire", None)
    assert "Pièces manquantes" in fiche["motif"]


def test_bcl01_meme_etat_vu_deux_fois_arrete_la_demande_en_quatre_etapes() -> None:
    fiche = traiter(DEMANDES["KAL-26-0601"])
    assert (fiche["issue"], fiche["file"]) == ("escalade", "gestionnaire")
    assert fiche["arret"] == {"borne": "etat_repete"}
    assert agents(fiche) == ["eligibilite", "pieces", "pieces", "coordination"]


# ---------------------------------------------------------------- règle 4 et mode dégradé (§ 9, § 10)

@pytest.mark.parametrize(("niveau", "issue", "file"), [
    ("faible", "decision", None),
    ("modere", "escalade", "gestionnaire"),
    ("eleve", "escalade", "cellule_fraude"),
])
def test_regle_4_selon_le_niveau_de_l_avis(niveau: str, issue: str, file: str | None) -> None:
    fiche = traiter(DEMANDES["KAL-26-0201"], consulter=partenaire(niveau, 0.3))  # AF-01, F2
    assert (fiche["issue"], fiche["file"]) == (issue, file)
    assert fiche["avis_fraude"] == {"niveau": niveau, "score": 0.3}
    assert fiche["mode_degrade"] is False


def test_sans_avis_950_euros_continue_en_mode_degrade() -> None:  # PAN-02, KAL-26-0502
    fiche = traiter(DEMANDES["KAL-26-0502"], consulter=partenaire(None))
    assert (fiche["decision"], fiche["montant_rembourse"]) == ("acceptee", 950.0)
    assert fiche["mode_degrade"] is True and fiche["avis_fraude"] is None


def test_sans_avis_6900_euros_part_en_cellule_fraude() -> None:  # PAN-02, KAL-26-0503
    fiche = traiter(DEMANDES["KAL-26-0503"], consulter=partenaire(None))
    assert (fiche["issue"], fiche["file"], fiche["mode_degrade"]) == ("escalade", "cellule_fraude", True)


def test_avis_faible_au_dela_de_10000_reste_une_escalade_gestionnaire() -> None:  # AF-03
    fiche = traiter(DEMANDES["KAL-26-0203"], consulter=partenaire("faible"))
    assert (fiche["issue"], fiche["file"]) == ("escalade", "gestionnaire")


def test_sans_avis_au_dela_de_10000_la_regle_4_passe_avant_la_regle_5() -> None:  # AF-03
    fiche = traiter(DEMANDES["KAL-26-0203"], consulter=partenaire(None))
    assert (fiche["file"], fiche["mode_degrade"]) == ("cellule_fraude", True)


def test_l_etape_anti_fraude_sans_avis_est_tracee_en_echec() -> None:
    fiche = traiter(DEMANDES["KAL-26-0502"], consulter=partenaire(None))
    (ligne,) = [t for t in fiche["trace"] if t["agent"] == "antifraude"]
    assert ligne["statut"] == "echec"


# ---------------------------------------------------------------- un seul appel par dossier

def test_meme_reference_deux_fois_dans_le_meme_registre_un_seul_appel() -> None:
    appels: list[str] = []

    def espion(**donnees: Any) -> AvisFraude:
        appels.append(donnees["reference"])
        return AvisFraude(statut="avis", niveau="faible", score=0.1)

    registre = RegistreAppels()
    traiter(DEMANDES["KAL-26-0201"], consulter=espion, registre=registre)
    seconde = traiter(DEMANDES["KAL-26-0201"], consulter=espion, registre=registre)
    assert appels == ["KAL-26-0201"]
    assert seconde["mode_degrade"] is True  # second passage : aucun nouvel appel, avis indisponible


# ---------------------------------------------------------------- bornes et filet de sécurité

def test_la_borne_d_etapes_arrete_la_demande_et_garde_la_derniere_etape_pour_l_issue() -> None:
    fiche = traiter(DEMANDES["KAL-26-0101"], bornes=Bornes(etapes_max=3))
    assert fiche["arret"] == {"borne": "etapes_max"} and fiche["issue"] == "escalade"
    assert len(fiche["trace"]) <= 3 and agents(fiche)[-1] == "coordination"


def test_la_borne_de_duree_arrete_la_demande() -> None:
    fiche = traiter(DEMANDES["KAL-26-0101"], bornes=Bornes(duree_max_s=0, reserve_fiche_s=0.5))
    assert fiche["arret"] == {"borne": "duree_max_s"} and fiche["issue"] == "escalade"


def test_une_erreur_imprevue_donne_une_escalade_motivee_avec_la_trace_partielle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def estimation_en_panne(**_entrees: Any) -> None:
        raise ZeroDivisionError("panne simulée")

    monkeypatch.setattr(coordination, "estimer", estimation_en_panne)
    fiche = traiter(DEMANDES["KAL-26-0101"])
    assert (fiche["issue"], fiche["file"]) == ("escalade", "gestionnaire")
    assert "erreur interne" in fiche["motif"].lower()
    assert {"agent": "estimation", "ecrit": [], "statut": "echec"}.items() <= fiche["trace"][-2].items()


# ---------------------------------------------------------------- le partenaire dans le budget de la demande (§ 12)

def espion_du_delai(vus: list[float | None]) -> Any:
    def consulter(*, delai_s: float | None = None, **_donnees: Any) -> AvisFraude:
        vus.append(delai_s)
        return AvisFraude(statut="avis", niveau="faible", score=0.1, appel_externe=True)
    return consulter


def test_le_partenaire_recoit_au_plus_3_s() -> None:
    vus: list[float | None] = []
    traiter(DEMANDES["KAL-26-0201"], consulter=espion_du_delai(vus))  # AF-01 : un indicateur
    assert len(vus) == 1 and vus[0] is not None and 2.9 < vus[0] <= 3.0


def test_le_partenaire_ne_recoit_que_le_temps_restant_de_la_demande() -> None:
    from time import monotonic
    vus: list[float | None] = []
    traiter(DEMANDES["KAL-26-0201"], consulter=espion_du_delai(vus), limite=monotonic() + 1.0)
    assert len(vus) == 1 and vus[0] is not None and vus[0] <= 1.0


@pytest.mark.parametrize("reference, issue, file, montant", [
    ("KAL-26-0502", "decision", None, 950.0),            # 1 500 € ou moins : continue, marquée mode dégradé
    ("KAL-26-0503", "escalade", "cellule_fraude", None),  # au-delà : contrôle anti-fraude manuel
])
def test_sans_temps_pour_le_partenaire_aucun_appel_et_la_branche_indisponible(
        reference: str, issue: str, file: str | None, montant: float | None) -> None:
    from time import monotonic
    vus: list[float | None] = []
    fiche = traiter(DEMANDES[reference], consulter=espion_du_delai(vus), limite=monotonic() + 0.05)
    assert vus == []  # aucun appel : le contrat ne permet qu'un appel, inutile de le gâcher
    assert (fiche["issue"], fiche["file"], fiche["montant_rembourse"], fiche["mode_degrade"]) == (
        issue, file, montant, True)
    assert fiche["avis_fraude"] is None


def test_la_regle_des_1500_euros_ne_saute_jamais_les_controles_precedents() -> None:
    from time import monotonic
    vus: list[float | None] = []
    fiche = traiter(DEMANDES["KAL-26-0502"], consulter=espion_du_delai(vus), limite=monotonic() - 1)
    assert vus == [] and fiche["arret"] == {"borne": "duree_max_s"}
    assert (fiche["issue"], fiche["file"], fiche["decision"], fiche["mode_degrade"]) == (
        "escalade", "gestionnaire", None, False)


def test_sans_indicateur_la_demande_n_est_jamais_marquee_degradee() -> None:
    vus: list[float | None] = []
    fiche = traiter(DEMANDES["KAL-26-0101"], consulter=partenaire(None))  # NOM-01 : aucun indicateur
    assert (fiche["decision"], fiche["mode_degrade"], vus) == ("acceptee", False, [])


def test_la_trace_garde_la_raison_d_un_avis_indisponible_jamais_le_contenu() -> None:
    def ecarte(**_donnees: Any) -> AvisFraude:
        return AvisFraude(statut="indisponible", raison="schema", appel_externe=True)

    fiche = traiter(DEMANDES["KAL-26-0502"], consulter=ecarte)
    (ligne,) = [x for x in fiche["trace"] if x["agent"] == "antifraude"]
    assert (ligne["statut"], ligne["raison"], ligne["appel_externe"]) == ("echec", "schema", True)
    autres = [x for x in fiche["trace"] if x["agent"] != "antifraude"]
    assert all(x.get("raison") is None for x in autres)
