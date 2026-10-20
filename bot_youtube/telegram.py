"""Cliente mínimo da Bot API do Telegram. A função HTTP é trocável no teste; o token nunca sai numa mensagem."""
import time
from pathlib import Path


class ErroTelegram(Exception):
    def __init__(self, codigo, descricao):
        super().__init__(f"Telegram {codigo}: {descricao}")
        self.codigo, self.descricao = codigo, descricao


def _http_requests(url, dados=None, arquivos=None, timeout=None):
    import requests
    abertos = {}
    try:
        for campo, caminho in (arquivos or {}).items():
            abertos[campo] = (Path(caminho).name, open(caminho, "rb"))
        r = requests.post(url, data=dados or None, files=abertos or None, timeout=timeout)
        try:
            corpo = r.json()
        except ValueError:
            corpo = {"ok": False, "error_code": r.status_code, "description": r.text[:300]}
        return r.status_code, corpo
    finally:
        for _, f in abertos.values():
            f.close()


def _http_get(url, timeout=None):
    import requests
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.content


class Telegram:
    def __init__(self, token, http=None, dormir=time.sleep, http_get=None, api_base="https://api.telegram.org"):
        self.token, self.http, self.dormir = token, http or _http_requests, dormir
        self.http_get = http_get or _http_get
        self.api_base = api_base.rstrip("/")

    def _limpo(self, texto):
        return str(texto).replace(self.token, "<token>")

    def chamar(self, metodo, dados=None, arquivos=None, timeout=60):
        url = f"{self.api_base}/bot{self.token}/{metodo}"
        for tentativa in range(2):
            try:
                status, corpo = self.http(url, dados=dados, arquivos=arquivos, timeout=timeout)
            except Exception as e:  # noqa: BLE001 - requests põe a URL (com o token) na mensagem
                raise ErroTelegram("rede", self._limpo(e)) from None
            if corpo.get("ok"):
                return corpo.get("result")
            codigo = corpo.get("error_code", status)
            espera = (corpo.get("parameters") or {}).get("retry_after")
            if codigo == 429 and espera and tentativa == 0:
                self.dormir(espera)
                continue
            raise ErroTelegram(codigo, self._limpo(corpo.get("description", "")))
        raise ErroTelegram(429, "limite de taxa")

    def baixar_arquivo(self, file_id, destino):
        caminho = self.chamar("getFile", {"file_id": file_id})["file_path"]
        try:
            dados = self.http_get(f"{self.api_base}/file/bot{self.token}/{caminho}", timeout=60)
        except Exception as e:  # noqa: BLE001
            raise ErroTelegram("rede", self._limpo(e)) from None
        Path(destino).parent.mkdir(parents=True, exist_ok=True)
        Path(destino).write_bytes(dados)
        return Path(destino)
