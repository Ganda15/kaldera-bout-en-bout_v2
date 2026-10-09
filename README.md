# Kaldera

Plateforme de traitement des demandes de remboursement d'assurance habitation :
contrôle d'éligibilité, vérification des pièces justificatives, estimation du
montant et consultation d'un service anti-fraude partenaire selon le protocole
agent-à-agent (A2A).

## Conception

Le dossier de conception (équipe d'agents, orchestration, mémoire partagée, liaison A2A, mode dégradé et plan d'épreuve) est dans [`conception/`](conception/README.md).

Schémas alignés sur le code le 08/10/2026 : carte des agents (contrôles dans l'ordre, avec court-circuit), système complet (N1) et lecture des pièces (schéma E), dans [`conception/schemas/`](conception/schemas/).

Livrable de conception, en un seul document : [`livrable/dossier-de-conception.pdf`](livrable/dossier-de-conception.pdf) (source : [`livrable/dossier-de-conception.md`](livrable/dossier-de-conception.md)).

## Features

- Traitement d'une demande ou d'un lot de demandes jusqu'à une fiche de décision
  (décision ou escalade vers une file humaine).
- Règles métier chiffrées : formules, franchises, plafonds, seuils d'escalade.
- Demandes de complément de pièces via l'espace assuré.
- Consultation du service anti-fraude partenaire (JSON-RPC 2.0, Agent Card).
- Service partenaire simulé, pilotable en direct (normal, lent, invalide, panne).
- Jeu de scénarios de recette et suite d'acceptance.

## Stack

- Python 3.11 (uv)
- FastAPI 0.115+ / uvicorn 0.30+ (service partenaire simulé)
- httpx 0.27+ (client A2A)
- pydantic 2.x
- openai 2.x (API Responses, déploiement Azure AI Foundry), PyMuPDF, Pillow : lecture des pièces (phase E)
- LangChain 0.3.x, langchain-azure-ai 0.1.x, LangGraph 0.2.x : présents dans le code de départ, non utilisés (aucune décision ne passe par un modèle)
- pytest 8.x
- Docker Compose (service partenaire)

## Setup

```bash
make install              # uv sync — installe les dépendances
cp .env.example .env      # puis renseigner les valeurs
make up                   # docker compose up -d — service partenaire sur :8100
make test                 # suite d'acceptance (lance son propre partenaire simulé)
```

Sans Docker, le service partenaire se lance aussi en local : `make partenaire`.

## Utilisation

```bash
make scenarios                                    # rejoue eval/scenarios.jsonl
make scenarios ARGS="--scenario NOM-01 --trace"   # un scénario, avec sa trace
make ctl ARGS=panne                               # met le service partenaire en panne
make ctl ARGS=journal                             # appels reçus par le partenaire
```

Les cibles `make` chargent `.env`. Hors `make` : `set -a; . ./.env; set +a`.

## Lecture des pièces non structurées (phase E)

Dans la réalité, l'assuré n'envoie pas un JSON : il envoie le PDF de son contrat et des photos de ses factures.
Deux agents de lecture transforment ces pièces en données de la spec § 3, puis la chaîne de décision du chantier 1
s'applique sans changement. Ils lisent et extraient, ils ne décident jamais. Schéma :
[`conception/schemas/schema-E-lecture-des-pieces.png`](conception/schemas/schema-E-lecture-des-pieces.png).

L'équipe compte huit rôles internes : trois qui utilisent un modèle (lecteur de contrat, lecteur de pièces, agent Documents et cohérence), quatre contrôles déterministes (Éligibilité, Pièces, Estimation, Anti-fraude) et la Coordination, qui applique les règles et produit seule l'issue. Le partenaire anti-fraude est un agent externe : il appartient à une autre entreprise. Où un modèle est utilisé, et pourquoi : dossier de conception, section 2.5.

| Agent | Reçoit | Ce qui est fait en code | Ce que fait le modèle |
|---|---|---|---|
| Lecteur de contrat (`lire_contrat`) | `contrat.pdf` | extraction du texte (PyMuPDF) | remplit le schéma strict `ContratLu` : numéro, formule, date, statut, cotisations |
| Lecteur de pièces (`lire_piece`) | une image et son type | mesure de netteté : une image floue est illisible, sans appel au modèle ; photo et dépôt de plainte nets sont lisibles | lit le montant TTC d'une facture nette, schéma strict `FactureLue` |
| Documents et cohérence (`agents/coherence.py`) | le sinistre déclaré et les images nettes, en un appel lancé dès l'arrivée du dossier | écarts explicites (autre sinistre, pièce datée avant le sinistre) et calcul du verdict ; contradiction, doute ou échec vont à un gestionnaire | interprète chaque pièce (nature, sinistre évoqué, date, concordance), schéma strict `Interpretation` |

Règles : dans le doute, une facture est déclarée illisible, ce qui déclenche une demande de complément (jamais un
montant inventé). Un modèle indisponible ou une réponse hors schéma rendent la lecture impossible : escalade motivée
vers un gestionnaire, aucun contrôle lancé. Un contrat lu différent du contrat déclaré : même escalade. Chaque consigne
précise que le document est une donnée, jamais une instruction.

Fichiers : `src/kaldera/extraction/` (`modele.py`, `lecteurs.py`, `dossier.py`) ; 34 dossiers générés depuis les
scénarios dans `dossiers/` (avec `dossiers/verite.json`, la vérité connue) ; générateur `outils/generer_dossiers.py`.

Configuration : copier `.env.example` en `.env` (ignoré par Git) et renseigner `AZURE_OPENAI_ENDPOINT`,
`AZURE_OPENAI_API_KEY` et `AZURE_OPENAI_DEPLOYMENT`. La clé n'est jamais écrite dans le code ni affichée.

Traiter un dossier (Windows, PowerShell, depuis la racine du dépôt) :

```powershell
.venv\Scripts\python.exe -m kaldera.extraction.dossier dossiers\KAL-26-0101
```

Sortie : une ligne par pièce lue (agent, fichier, statut, durée, appel au modèle ou non), puis la fiche de décision.
Mesuré le 08/10/2026 : `KAL-26-0101` acceptée 1 700 € en 8,9 s ; `KAL-26-0601` (facture floue déposée deux fois)
escaladée par la borne `etat_repete` en 3,7 s, sans appel au modèle pour les images.

Évaluation sur les 34 dossiers, contre la vérité connue :

```powershell
.venv\Scripts\python.exe -m outils.evaluer_extraction
.venv\Scripts\python.exe -m outils.evaluer_extraction --verifier
```

Résultat du 08/10/2026 ([`evaluation/extraction/rapport.md`](evaluation/extraction/rapport.md), généré depuis
`resultats.json`, jamais écrit à la main, commit `5cb2a4e`, agent Documents et cohérence compris) : verdict
**échoué**. 100 % sur chaque champ (5 champs du contrat sur 34 dossiers, 33 montants, 68 lisibilités), aucune
lecture impossible, mais 32 décisions sur 34 identiques au chemin JSON pour un seuil de 95 % : les deux écarts
(KAL-26-0204, KAL-26-0503) viennent de la cohérence, qui juge deux factures d'incendie incertaines, pas de la
lecture. 101 appels au modèle (34 contrats, 33 factures, 34 cohérences). La cohérence a sa propre évaluation, sur
42 dossiers ([`evaluation/coherence/rapport.md`](evaluation/coherence/rapport.md)) : 6 contradictions sur 6,
aucune fausse contradiction, 2 examens inutiles (seuil : 3 au plus), mais 1 échec technique (seuil : 0) :
verdict **échoué**. Limites : pièces de synthèse, nettes et dactylographiées ;
deux images illisibles seulement ; le contenu des photos n'est pas vérifié. Les tests unitaires remplacent le modèle
par un faux : ils ne font aucun appel réseau.

## Layout

- `src/kaldera/` : la Coordination (`coordination.py`), la mémoire de la demande (`etat.py`), les bornes (`bornes.py`), les métriques (`metriques.py`), les règles (`regles.py`), les quatre agents de contrôle et l'agent Documents et cohérence (`agents/`), les agents de lecture (`extraction/`), l'espace assuré
- `tests/unit/` : nos tests unitaires (323 au 09/10/2026) ; `tests/integration/` : 37 tests d'intégration (les 28 scénarios rejoués par toute l'équipe, et le chemin public vers le partenaire)
- `dossiers/` : 34 dossiers de pièces non structurées et leur vérité ; `outils/` : générateur, essai du modèle, évaluation ; `evaluation/extraction/` : rapport généré
- `conception/` : dossier de conception, schémas, journal des ajustements ; `livrable/` : le PDF
- `docs/specs_metier.md` — spécifications fonctionnelles
- `docs/interface.md` — contrat d'intégration (points d'entrée, fiche de décision, trace, métriques)
- `external_agent/` — service anti-fraude partenaire simulé et son contrat d'échange (`contrat.md`)
- `scripts/partner_ctl.py` — pilotage du service partenaire simulé
- `eval/scenarios.jsonl` — scénarios de recette
- `tests/acceptance/` — suite d'acceptance

## Useful commands

```bash
make fmt        # ruff format + autofix
make lint       # ruff check
make typecheck  # mypy
make down       # arrête les services docker
```

## Intégration continue

Fichier : `.github/workflows/tests.yml`, exécuté par GitHub Actions.

| | |
|---|---|
| Déclencheurs | chaque push sur `main`, chaque pull request, et à la main (onglet Actions, « Run workflow ») |
| Environnement | Ubuntu, Python 3.11 (version exigée par `pyproject.toml`), cache pip |
| Étapes | 1. récupération du code ; 2. installation : `pip install -e . --group dev` ; 3. style : `ruff check .` ; 4. tests unitaires : `pytest tests/unit` ; 5. tests d'acceptance des chantiers 1 et 2 : `pytest tests/acceptance` ; 6. tests d'intégration (partenaire simulé, réseau local) : `pytest tests/integration` |
| Résultat | une coche verte ou une croix rouge sur chaque commit, détail dans l'onglet Actions du dépôt |

Les 56 tests d'acceptance (chantiers 1 et 2) et les 37 tests d'intégration tournent à chaque push sur `main` et à chaque pull request. Les évaluations avec le modèle réel n'y tournent pas : elles coûtent des appels et demandent la clé ; elles se lancent à la main (`outils/evaluer_extraction.py`, `outils/evaluer_coherence.py`).

Reproduire la chaîne en local (Windows, PowerShell, depuis la racine du dépôt) :

```powershell
py -V:Astral/CPython3.11.15 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e . --group dev
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m pytest tests/unit tests/acceptance tests/integration -q
```

Tester la chaîne elle-même : pousser un commit sur `main`, ou lancer « Run workflow » dans l'onglet Actions, puis vérifier que les six étapes sont vertes.

## Known issues

- Le registre des appels au partenaire couvre une exécution (une demande ou un lot). Après un redémarrage, un
  second appel pour le même dossier n'est pas bloqué en amont : le partenaire le refuse (`-32029`) et la demande
  passe en mode dégradé. Un registre durable demanderait un stockage persistant (question posée au formateur).
- Cohérence : une facture d'achat datée avant un incendie est signalée comme contradiction (seul le vol est
  traité à part). La demande va à un gestionnaire, jamais à un refus. Correction prévue : le modèle rendra
  l'objet de la facture (achat du bien ou réparation).
- Les deux évaluations avec le modèle réel restent « échouées » selon leurs propres seuils (voir plus haut).
- Le poste du gestionnaire (`src/kaldera/web/`) est un prototype local, sans connexion.

## License

Usage interne — tous droits réservés.
