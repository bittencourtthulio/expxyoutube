"""Login OAuth no YouTube e listagem dos canais autorizados.

Uso: .venv/bin/python auth.py <apelido-do-canal>
Abre o navegador na primeira vez e salva tokens/<apelido>.json para os próximos acessos.
"""
import argparse
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

ROOT = Path(__file__).parent
CLIENT_SECRET = ROOT / "client_secret.json"
TOKENS_DIR = ROOT / "tokens"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]


def get_credentials(alias: str) -> Credentials:
    TOKENS_DIR.mkdir(exist_ok=True)
    TOKEN = TOKENS_DIR / f"{alias}.json"
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
        creds = flow.run_local_server(port=0, prompt="select_account consent")
    TOKEN.write_text(creds.to_json())
    TOKEN.chmod(0o600)
    return creds


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Login OAuth no YouTube de um canal e listagem do canal autorizado.")
    ap.add_argument("apelido", nargs="?", default="principal", help="apelido do canal; o token fica guardado com esse nome (padrão: principal)")
    alias = ap.parse_args(argv).apelido
    youtube = build("youtube", "v3", credentials=get_credentials(alias))
    resp = youtube.channels().list(part="snippet,statistics", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        print("Nenhum canal encontrado para a conta autorizada.")
        return
    for ch in items:
        s, st = ch["snippet"], ch["statistics"]
        print(f"Canal: {s['title']}")
        print(f"  ID: {ch['id']}")
        print(f"  Handle: {s.get('customUrl', '-')}")
        print(f"  Inscritos: {st.get('subscriberCount', 'oculto')}")
        print(f"  Vídeos: {st.get('videoCount')}")
        print(f"  Views: {st.get('viewCount')}")


if __name__ == "__main__":
    main()
