"""Lance le poste du gestionnaire : python -m kaldera.web, puis ouvrir http://127.0.0.1:8200 (adresse locale seulement)."""

from __future__ import annotations

import uvicorn

from .app import creer_app

if __name__ == "__main__":
    uvicorn.run(creer_app(), host="127.0.0.1", port=8200, log_level="info")
