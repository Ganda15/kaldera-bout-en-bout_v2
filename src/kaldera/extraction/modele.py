"""Accès au modèle de langage : un déploiement Azure AI Foundry, appelé par l'API Responses compatible OpenAI.

La configuration vient de l'environnement, ou à défaut du fichier `.env` à la racine du dépôt (ignoré par Git).
La clé n'est jamais écrite dans le code, jamais affichée, jamais tracée.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from openai import OpenAI

RACINE = Path(__file__).resolve().parents[3]
DEPLOIEMENT_PAR_DEFAUT = "gpt-5.4-2"


class ConfigurationManquante(Exception):
    """Une variable nécessaire à l'accès au modèle est absente."""


@dataclass(frozen=True)
class Configuration:
    point_d_acces: str
    deploiement: str
    cle: str = field(repr=False)  # jamais affichée


def _lire_env(fichier: Path) -> dict[str, str]:
    """Lit les lignes `CLE=valeur` d'un fichier .env ; ignore les lignes vides et les commentaires."""
    valeurs: dict[str, str] = {}
    if not fichier.exists():
        return valeurs
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith("#") and "=" in ligne:
            cle, valeur = ligne.split("=", 1)
            valeurs[cle.strip()] = valeur.strip().strip('"').strip("'")
    return valeurs


def configuration(fichier_env: Path = RACINE / ".env") -> Configuration:
    """L'environnement l'emporte sur le fichier .env ; une variable manquante arrête tout, sans révéler de secret."""
    fichier = _lire_env(fichier_env)

    def valeur(nom: str, defaut: str | None = None) -> str:
        trouvee = os.environ.get(nom) or fichier.get(nom) or defaut
        if not trouvee:
            raise ConfigurationManquante(f"variable {nom} absente : à renseigner dans .env (voir .env.example)")
        return trouvee

    return Configuration(point_d_acces=valeur("AZURE_OPENAI_ENDPOINT"),
                         deploiement=valeur("AZURE_OPENAI_DEPLOYMENT", DEPLOIEMENT_PAR_DEFAUT),
                         cle=valeur("AZURE_OPENAI_API_KEY"))


def client(config: Configuration | None = None) -> OpenAI:
    config = config or configuration()
    return OpenAI(base_url=config.point_d_acces, api_key=config.cle, timeout=60.0, max_retries=0)
