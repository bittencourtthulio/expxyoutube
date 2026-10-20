"""O ambiente da .venv tem as dependências declaradas e acha os módulos da raiz."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def test_dependencias_importam():
    import googleapiclient  # noqa: F401
    import google_auth_oauthlib  # noqa: F401
    import pytest  # noqa: F401
    import yt_dlp  # noqa: F401


def test_requirements_lista_as_dependencias():
    texto = (RAIZ / "requirements.txt").read_text(encoding="utf-8").lower()
    for dep in ("google-api-python-client", "google-auth-oauthlib", "yt-dlp", "pytest"):
        assert dep in texto


def test_modulo_da_raiz_importa():
    import auth
    assert auth.TOKENS_DIR.name == "tokens"
