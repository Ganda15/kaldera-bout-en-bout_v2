# Kaldera

Plateforme de traitement des demandes de remboursement d'assurance habitation :
contrôle d'éligibilité, vérification des pièces justificatives, estimation du
montant et consultation d'un service anti-fraude partenaire selon le protocole
agent-à-agent (A2A).

## Conception

Le dossier de conception (équipe d'agents, orchestration, mémoire partagée, liaison A2A, mode dégradé et plan d'épreuve) est dans [`conception/`](conception/README.md).

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
- LangChain 0.3.x, langchain-azure-ai 0.1.x (Kimi-K2.6), LangGraph 0.2.x
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

## Layout

- `src/kaldera/` — traitement des demandes (orchestrateur, agent, client partenaire, espace assuré, règles)
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
| Étapes | 1. récupération du code ; 2. installation : `pip install -e . --group dev` ; 3. style : `ruff check .` ; 4. tests unitaires : `pytest tests/unit` ; 5. tests d'acceptance du chantier 1 : `pytest tests/acceptance/test_equipe_orchestration.py` |
| Résultat | une coche verte ou une croix rouge sur chaque commit, détail dans l'onglet Actions du dépôt |

Les tests du chantier 2 (`tests/acceptance/test_collaboration_a2a.py`) rejoindront la chaîne quand le client A2A sera branché : aujourd'hui ils échouent par construction, le partenaire étant un bouchon.

Reproduire la chaîne en local (Windows, PowerShell, depuis la racine du dépôt) :

```powershell
py -V:Astral/CPython3.11.15 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e . --group dev
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m pytest tests/unit tests/acceptance/test_equipe_orchestration.py -q
```

Tester la chaîne elle-même : pousser un commit sur `main`, ou lancer « Run workflow » dans l'onglet Actions, puis vérifier que les cinq étapes sont vertes.

## Known issues

- Les échanges avec le service anti-fraude n'ont pas été revalidés depuis la
  version 2.0 de son contrat.
- Le comportement face à un partenaire lent ou indisponible n'a pas encore été
  éprouvé en conditions réelles.

## License

Usage interne — tous droits réservés.
