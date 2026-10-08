"""Les 28 scénarios de eval/scenarios.jsonl rejoués par toute l'équipe, contre le partenaire simulé, par le réseau local.

La suite d'acceptance du formateur vérifie l'issue de chaque demande. Ces tests vérifient en plus ce qu'elle ne regarde
pas : la trace et les métriques disent la vérité sur ce que le partenaire a reçu, chaque avis indisponible porte la
bonne raison, aucune donnée personnelle ni aucun contenu écarté n'apparaît, même dans la trace, et le lot tient ses
délais.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

import kaldera
from simulation import demarrer_partenaire, journal, preparer

RACINE = Path(__file__).resolve().parents[2]
SCENARIOS = [json.loads(ligne) for ligne in (RACINE / "eval" / "scenarios.jsonl").read_text(encoding="utf-8").splitlines()
             if ligne.strip()]
BORNES = kaldera.bornes()

# La raison attendue dans la trace, selon le réglage du partenaire simulé (contrat § 3 et § 4).
RAISON_ATTENDUE = {"panne": "http_503", "lent": "delai_depasse", "score_hors_bornes": "schema",
                   "niveau_incoherent": "incoherence", "champ_hors_contrat": "schema",
                   "reference_differente": "incoherence", "champ_absent": "schema", "non_json": "reponse_non_json",
                   "enveloppe_invalide": "enveloppe_invalide"}
METRIQUES = ("appels", "echecs", "latence_ms", "appels_externes")


@pytest.fixture(scope="module")
def partenaire() -> Any:
    url, pilote, serveur = demarrer_partenaire()
    yield url, pilote
    serveur.should_exit = True


def valeurs_personnelles(demande: dict[str, Any]) -> list[str]:
    assure = demande["assure"]
    valeurs = [assure[c] for c in ("id_client", "nom", "prenom", "email", "telephone", "iban", "adresse", "code_postal")]
    valeurs += [demande["contrat"]["numero"], demande["sinistre"]["description"]]
    return [v for v in valeurs if isinstance(v, str) and v]


def verifier_issue(fiche: dict[str, Any], attendu: dict[str, Any]) -> None:
    ref = attendu["reference"]
    for champ in ("issue", "decision", "file"):
        if champ in attendu:
            assert fiche[champ] == attendu[champ], f"{ref} : {champ} = {fiche[champ]!r}, attendu {attendu[champ]!r}"
    if "montant_rembourse" in attendu:
        prevu, obtenu = attendu["montant_rembourse"], fiche["montant_rembourse"]
        assert (prevu is None and obtenu is None) or (prevu is not None and obtenu is not None
                                                       and abs(obtenu - prevu) < 0.01), f"{ref} : montant {obtenu!r}"
    if "mode_degrade" in attendu:
        assert bool(fiche["mode_degrade"]) is attendu["mode_degrade"], f"{ref} : mode_degrade {fiche['mode_degrade']!r}"
    if attendu.get("arret"):
        assert (fiche["arret"] or {}).get("borne"), f"{ref} : arrêt non signalé"
    assert fiche["motif"], f"{ref} : issue sans motif"


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_le_scenario_rejoue_par_toute_l_equipe(scenario: dict[str, Any], partenaire: Any) -> None:
    url, pilote = partenaire
    preparer(pilote, scenario["partenaire"])
    debut = time.perf_counter()
    resultat = kaldera.traiter_lot(scenario["demandes"], partenaire_url=url)
    duree = time.perf_counter() - debut
    recus = journal(pilote)
    fiches = {f["reference"]: f for f in resultat["fiches"]}

    # 1 · issue conforme au champ attendu, pour chaque demande
    for attendu in scenario["attendu"]:
        verifier_issue(fiches[attendu["reference"]], attendu)

    # 2 · un seul appel par dossier, et la trace dit exactement ce que le partenaire a reçu
    for reference in fiches:
        assert sum(1 for e in recus if e.get("reference") == reference) <= 1, f"{reference} : plus d'un appel"
    lignes_af = [x for f in fiches.values() for x in f["trace"] if x["agent"] == "antifraude"]
    assert sum(1 for x in lignes_af if x["appel_externe"]) == len(recus), "la trace ne compte pas les vrais appels"
    if scenario["partenaire"]["mode"] != "panne":  # en panne, le partenaire répond 503 sans lire la requête
        assert all(e["conforme"] for e in recus), "une requête refusée par le partenaire : le filtre a laissé passer"

    # 3 · chaque avis indisponible porte la raison attendue ; un avis obtenu n'en porte aucune
    attendue = RAISON_ATTENDUE.get(scenario["partenaire"].get("variante") or scenario["partenaire"]["mode"])
    for ligne in lignes_af:
        if ligne["statut"] == "echec":
            assert ligne["raison"] == attendue, f"raison {ligne['raison']!r}, attendue {attendue!r}"
        else:
            assert ligne["raison"] is None

    # 4 · métriques par agent : présentes pour chaque agent de la trace, cohérentes avec le partenaire
    metriques = resultat["metriques"]
    agents = {x["agent"] for f in fiches.values() for x in f["trace"]}
    for agent in agents:
        assert all(isinstance(metriques[agent][cle], (int, float)) for cle in METRIQUES), agent
    if "antifraude" in metriques:
        assert metriques["antifraude"]["appels_externes"] == len(recus)
        assert metriques["antifraude"]["echecs"] == sum(1 for x in lignes_af if x["statut"] == "echec")

    # 5 · bornes : jamais plus d'étapes que permis, le lot tient ses délais
    assert max(len(f["trace"]) for f in fiches.values()) <= BORNES["etapes_max"]
    assert duree < BORNES["duree_max_s"], f"lot en {duree:.2f} s"
    if scenario["partenaire"]["mode"] == "lent":
        assert duree < BORNES["delai_partenaire_s"] + 0.5, f"lot lent en {duree:.2f} s : le partenaire attendu trop longtemps"

    # 6 · rien de personnel, rien d'une réponse écartée, nulle part dans la fiche (trace comprise)
    for demande in scenario["demandes"]:
        texte = json.dumps(fiches[demande["reference"]], ensure_ascii=False)
        fuites = [v for v in valeurs_personnelles(demande) if v in texte]
        assert not fuites, f"{demande['reference']} : données personnelles dans la fiche : {fuites}"
        assert "EVA-NC" not in texte and "rembourser_integralement" not in texte
