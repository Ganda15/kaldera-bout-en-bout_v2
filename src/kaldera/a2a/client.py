"""Client A2A du partenaire anti-fraude (contrat § 1, § 5 et § 6).

Un appel = le filtre (sept champs, schéma strict), puis un seul `message/send` en JSON-RPC 2.0 avec le jeton, abandonné
au bout du délai donné par la Coordination (au plus 3 s, moins s'il reste moins de temps à la demande). Aucune relance,
quelle que soit l'issue. Une réponse arrivée après le délai n'est jamais lue. La réponse passe ensuite les cinq niveaux
de `validation.valider_reponse`. Rien n'est journalisé ici : ni le message, ni le jeton.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from time import monotonic
from typing import Any

import httpx

from ..agents.antifraude import AvisFraude
from .filtre import RequeteNonConforme, construire_donnees
from .validation import valider_reponse

DELAI_CONTRAT_S = 3.0  # contrat § 5 : abandon au plus tard 3 s après l'envoi


def _indisponible(raison: str, appel_externe: bool) -> AvisFraude:
    return AvisFraude(statut="indisponible", raison=raison, appel_externe=appel_externe)


def partenaire_a2a(url: str | None, *, transport: httpx.BaseTransport | None = None) -> Callable[..., AvisFraude]:
    """Rend la fonction `consulter` que l'agent Anti-fraude appelle avec les sept données (et le délai)."""
    adresse = (url or "").rstrip("/")

    def consulter(*, delai_s: float = DELAI_CONTRAT_S, **donnees: Any) -> AvisFraude:
        if not adresse:
            return _indisponible("partenaire_non_configure", False)
        try:
            data = construire_donnees(**donnees)
        except RequeteNonConforme:  # défaut de notre côté : rien ne part
            return _indisponible("requete_non_conforme", False)
        delai = min(delai_s, DELAI_CONTRAT_S)
        id_requete = str(uuid.uuid4())
        requete = {"jsonrpc": "2.0", "id": id_requete, "method": "message/send",
                   "params": {"message": {"role": "user", "messageId": str(uuid.uuid4()),
                                          "parts": [{"kind": "data", "data": data}]}}}
        entetes = {"Authorization": f"Bearer {os.environ.get('PARTENAIRE_JETON', '')}"}
        fin = monotonic() + delai
        try:
            with httpx.Client(transport=transport, timeout=delai) as client:
                reponse = client.post(f"{adresse}/a2a", json=requete, headers=entetes)
        except httpx.TimeoutException:
            return _indisponible("delai_depasse", True)
        except httpx.HTTPError:
            return _indisponible("erreur_transport", True)
        if monotonic() > fin:  # arrivée trop tard : jamais lue
            return _indisponible("delai_depasse", True)
        return valider_reponse(reponse, id_requete=id_requete, reference=data["reference_dossier"])

    return consulter
