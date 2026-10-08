"""Démarre le partenaire simulé fourni (`external_agent`) sur un port libre du réseau local, pour les tests d'intégration."""

from __future__ import annotations

import os
import socket
import threading
import time
from typing import Any

import httpx
import uvicorn

JETON = "jeton-integration"


def demarrer_partenaire() -> tuple[str, httpx.Client, Any]:
    """Rend (adresse, client de pilotage /_sim/*, serveur). Arrêt : serveur.should_exit = True."""
    os.environ["PARTENAIRE_JETON"] = JETON
    from external_agent.app import app

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    serveur = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", ws="none"))
    threading.Thread(target=serveur.run, daemon=True).start()
    limite = time.monotonic() + 10
    while not serveur.started:
        if time.monotonic() > limite:
            raise RuntimeError("le partenaire simulé n'a pas démarré")
        time.sleep(0.05)
    url = f"http://127.0.0.1:{port}"
    return url, httpx.Client(base_url=url, timeout=15), serveur


def preparer(pilote: httpx.Client, reglage: dict[str, Any]) -> None:
    pilote.post("/_sim/reset").raise_for_status()
    pilote.post("/_sim/mode", json=reglage).raise_for_status()


def journal(pilote: httpx.Client) -> list[dict[str, Any]]:
    return pilote.get("/_sim/journal").json()
