import pytest
from pydantic import ValidationError

from app.config.settings import Settings


def make_settings(**overrides):
    values = {
        "APP_NAME": "test-app",
        "APP_VERSION": "0.1.0",
        "DEBUG": False,
        "HOST": "0.0.0.0",
        "PORT": 8000,
    }

    values.update(overrides)

    return Settings(_env_file=None, **values)


def test_production_rejects_inmemory_qdrant():
    with pytest.raises(ValidationError):
        make_settings(QDRANT_URL=":memory:")


def test_production_rejects_empty_qdrant_url():
    with pytest.raises(ValidationError):
        make_settings(QDRANT_URL="")


def test_production_allows_persistent_qdrant_url():
    settings = make_settings(
        QDRANT_URL="https://qdrant.example.com",
    )

    assert settings.QDRANT_URL == "https://qdrant.example.com"


def test_production_allows_local_disk_qdrant():
    settings = make_settings(QDRANT_URL="/var/lib/qdrant")

    assert settings.QDRANT_URL == "/var/lib/qdrant"


def test_debug_allows_inmemory_qdrant():
    settings = make_settings(DEBUG=True, QDRANT_URL=":memory:")

    assert settings.DEBUG is True
    assert settings.QDRANT_URL == ":memory:"
