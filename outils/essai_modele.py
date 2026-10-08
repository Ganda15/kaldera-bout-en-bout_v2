"""Essai de l'accès au modèle (étape E0) : un appel texte, puis un appel avec une image.

Lancement, depuis la racine du dépôt, une fois la clé renseignée dans .env :
    .venv\\Scripts\\python.exe outils\\essai_modele.py
N'affiche jamais la clé. Coût : deux petits appels.
"""

from __future__ import annotations

import base64
import io
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kaldera.extraction import modele  # noqa: E402


class Total(BaseModel):
    montant_total: float


def image_de_test() -> str:
    """Une petite facture dessinée, encodée en base64 (PNG)."""
    img = Image.new("RGB", (520, 220), "white")
    dessin = ImageDraw.Draw(img)
    dessin.text((20, 20), "FACTURE N. 2026-0042", fill="black")
    dessin.text((20, 70), "Plomberie Martin - remplacement de canalisation", fill="black")
    dessin.text((20, 140), "TOTAL TTC : 1 234,50 EUR", fill="black")
    tampon = io.BytesIO()
    img.save(tampon, format="PNG")
    return base64.b64encode(tampon.getvalue()).decode("ascii")


def main() -> None:
    config = modele.configuration()
    client = modele.client(config)
    print(f"point d'accès : {config.point_d_acces} | déploiement : {config.deploiement}")

    debut = time.perf_counter()
    reponse = client.responses.create(model=config.deploiement, input="Réponds seulement par le mot OK.")
    print(f"1. texte : {reponse.output_text!r} ({time.perf_counter() - debut:.1f} s)")

    debut = time.perf_counter()
    lu = client.responses.parse(
        model=config.deploiement,
        input=[{"role": "user", "content": [
            {"type": "input_text", "text": "Lis le montant total TTC de cette facture."},
            {"type": "input_image", "image_url": f"data:image/png;base64,{image_de_test()}"},
        ]}],
        text_format=Total,
    )
    print(f"2. image : {lu.output_parsed} ({time.perf_counter() - debut:.1f} s) ; attendu : montant_total=1234.5")


if __name__ == "__main__":
    main()
