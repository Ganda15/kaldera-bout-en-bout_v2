"""Faux modèle de cohérence partagé par les tests : il rend, pour chaque image annoncée dans la consigne, une
interprétation qui concorde avec la déclaration, sauf pour les fichiers nommés dans `ecarts` (fichier -> sinistre
évoqué). Les 34 dossiers concordent par construction (evaluation/coherence/attendus.json)."""

from __future__ import annotations

import re

from kaldera.agents.coherence import DocumentInterprete, Interpretation


def interpretation(consigne: str, **ecarts: str) -> Interpretation:
    annonces = re.findall(r"^\d+\. (\S+\.png) \(déposé comme (\w+)\)$", consigne, flags=re.MULTILINE)
    return Interpretation(documents=[
        DocumentInterprete(fichier=f, nature=t, sinistre_evoque=ecarts.get(f, "indetermine"), date_document=None,
                           objet="pièce", concorde="non" if f in ecarts else "oui", justification="faux modèle")
        for f, t in annonces])
