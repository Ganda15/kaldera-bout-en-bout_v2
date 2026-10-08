"""Accès au modèle de langage (phase E) : configuration lue dans l'environnement ou dans `.env`, jamais dans le code.

Aucun appel réseau dans ces tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kaldera.extraction import modele

CLE_FACTICE = "cle-factice-ne-pas-utiliser-0123456789"


def test_sans_cle_le_client_refuse_de_demarrer_sans_reveler_de_secret(monkeypatch: pytest.MonkeyPatch,
                                                                       tmp_path: Path) -> None:
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://exemple.services.ai.azure.com/openai/v1")
    with pytest.raises(modele.ConfigurationManquante) as erreur:
        modele.configuration(fichier_env=tmp_path / "absent.env")
    assert "AZURE_OPENAI_API_KEY" in str(erreur.value)


def test_la_configuration_vient_de_l_environnement(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://exemple.services.ai.azure.com/openai/v1")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", CLE_FACTICE)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    config = modele.configuration(fichier_env=tmp_path / "absent.env")
    assert config.point_d_acces == "https://exemple.services.ai.azure.com/openai/v1"
    assert config.deploiement == "gpt-5.4-2"  # valeur par défaut
    assert CLE_FACTICE not in repr(config)  # la clé ne s'affiche jamais


def test_le_fichier_env_est_lu_sans_ecraser_l_environnement(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "# commentaire\n"
        "AZURE_OPENAI_ENDPOINT=https://depuis-le-fichier/openai/v1\n"
        f"AZURE_OPENAI_API_KEY={CLE_FACTICE}\n"
        "AZURE_OPENAI_DEPLOYMENT=autre-deploiement\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://depuis-l-environnement/openai/v1")
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    config = modele.configuration(fichier_env=env)
    assert config.point_d_acces == "https://depuis-l-environnement/openai/v1"  # l'environnement l'emporte
    assert config.deploiement == "autre-deploiement"


def test_le_client_pointe_vers_le_point_d_acces_azure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://exemple.services.ai.azure.com/openai/v1")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", CLE_FACTICE)
    client = modele.client(modele.configuration(fichier_env=tmp_path / "absent.env"))
    assert str(client.base_url).startswith("https://exemple.services.ai.azure.com/openai/v1")
