"""traiter_lot : demandes traitées en concurrence, fiches dans l'ordre, métriques par agent calculées
depuis la trace (docs/interface.md ; specs_metier.md § 12)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

import kaldera
from kaldera.agents.antifraude import AvisFraude
from kaldera.metriques import calculer_metriques

SCENARIOS = Path(__file__).resolve().parents[2] / "eval" / "scenarios.jsonl"
DEMANDES = {
    d["reference"]: d
    for ligne in SCENARIOS.read_text(encoding="utf-8").splitlines() if ligne.strip()
    for d in json.loads(ligne)["demandes"]
}
NOMINALES = [f"KAL-26-01{n:02d}" for n in range(1, 12)]


def lent(secondes: float, appel_externe: bool = True) -> Any:
    def consulter(**_donnees: Any) -> AvisFraude:
        time.sleep(secondes)
        return AvisFraude(statut="avis", niveau="faible", score=0.1, appel_externe=appel_externe)
    return consulter


def test_un_lot_vide() -> None:
    assert kaldera.traiter_lot([]) == {"fiches": [], "metriques": {}}


def test_les_fiches_sont_rendues_dans_l_ordre_des_demandes() -> None:
    resultat = kaldera.traiter_lot([DEMANDES[r] for r in NOMINALES])
    assert [f["reference"] for f in resultat["fiches"]] == NOMINALES


def test_une_demande_lente_ne_retarde_pas_les_autres() -> None:
    # AF-01 et AF-02 attendent chacune 0,4 s le partenaire ; à la suite, le lot durerait 0,8 s au moins
    lot = [DEMANDES["KAL-26-0201"], DEMANDES["KAL-26-0202"], DEMANDES["KAL-26-0101"]]
    debut = time.perf_counter()
    resultat = kaldera.traiter_lot(lot, consulter=lent(0.4))
    duree = time.perf_counter() - debut
    assert duree < 0.7, f"lot en {duree:.2f} s : les demandes ne sont pas traitées en concurrence"
    assert [f["issue"] for f in resultat["fiches"]] == ["decision", "decision", "decision"]


def test_meme_reference_deux_fois_dans_un_lot_un_seul_appel() -> None:
    appels: list[str] = []

    def espion(**donnees: Any) -> AvisFraude:
        appels.append(donnees["reference"])
        return AvisFraude(statut="avis", niveau="faible", score=0.1, appel_externe=True)

    resultat = kaldera.traiter_lot([DEMANDES["KAL-26-0201"], DEMANDES["KAL-26-0201"]], consulter=espion)
    assert appels == ["KAL-26-0201"]
    assert sorted(f["mode_degrade"] for f in resultat["fiches"]) == [False, True]


def test_metriques_indexees_par_les_agents_presents_dans_les_traces() -> None:
    resultat = kaldera.traiter_lot([DEMANDES["KAL-26-0101"], DEMANDES["KAL-26-0102"]])  # NOM-01, NOM-02
    metriques = resultat["metriques"]
    assert set(metriques) == {"eligibilite", "pieces", "estimation", "antifraude", "coordination"}
    assert metriques["eligibilite"]["appels"] == 2 and metriques["coordination"]["appels"] == 2
    assert metriques["pieces"]["appels"] == 1  # NOM-02 s'arrête après l'éligibilité
    for valeurs in metriques.values():
        assert set(valeurs) >= {"appels", "echecs", "latence_ms", "appels_externes"}


def test_appels_externes_comptes_seulement_quand_le_partenaire_est_vraiment_appele() -> None:
    avec = kaldera.traiter_lot([DEMANDES["KAL-26-0201"]], consulter=lent(0, appel_externe=True))
    sans = kaldera.traiter_lot([DEMANDES["KAL-26-0201"]])  # bouchon : aucun appel réseau
    assert avec["metriques"]["antifraude"]["appels_externes"] == 1
    assert sans["metriques"]["antifraude"]["appels_externes"] == 0


def test_le_calcul_des_metriques_depuis_des_traces_connues() -> None:
    fiches = [
        {"trace": [{"agent": "antifraude", "ecrit": ["avis_fraude"], "duree_ms": 1.0, "statut": "ok",
                    "appel_externe": True},
                   {"agent": "coordination", "ecrit": ["issue"], "duree_ms": 0.0, "statut": "ok"}]},
        {"trace": [{"agent": "antifraude", "ecrit": ["avis_fraude"], "duree_ms": 3.0, "statut": "echec",
                    "appel_externe": True}]},
    ]
    metriques = calculer_metriques(fiches)
    assert metriques["antifraude"] == {"appels": 2, "echecs": 1, "latence_ms": 2.0, "appels_externes": 2}
    assert metriques["coordination"] == {"appels": 1, "echecs": 0, "latence_ms": 0.0, "appels_externes": 0}


# ---------------------------------------------------------------- l'adresse du partenaire est bien utilisée

def test_traiter_demande_utilise_l_adresse_du_partenaire(monkeypatch: pytest.MonkeyPatch) -> None:
    from kaldera.a2a import client
    adresses: list[str | None] = []

    def fabrique(url: str | None, **_options: Any) -> Any:
        adresses.append(url)
        return lambda **_donnees: AvisFraude(statut="avis", niveau="faible", score=0.1, appel_externe=True)

    monkeypatch.setattr(client, "partenaire_a2a", fabrique)
    fiche = kaldera.traiter_demande(DEMANDES["KAL-26-0201"], partenaire_url="http://partenaire.test")
    assert adresses == ["http://partenaire.test"] and fiche["avis_fraude"] == {"niveau": "faible", "score": 0.1}
    resultat = kaldera.traiter_lot([DEMANDES["KAL-26-0201"]], partenaire_url="http://partenaire.test")
    assert adresses == ["http://partenaire.test"] * 2 and resultat["fiches"][0]["decision"] == "acceptee"


def test_sans_adresse_ni_consulter_le_bouchon_reste_en_place() -> None:
    fiche = kaldera.traiter_demande(DEMANDES["KAL-26-0201"])
    assert fiche["mode_degrade"] is True  # chantier 1 : avis indisponible, aucun réseau
