"""Configuração do bot do YouTube: ambiente primeiro, depois o arquivo de chaves da raiz do youtube-squad.

Os nomes são próprios (TELEGRAM_YT_*), para o bot nunca pegar o token do bot do Instagram. Erro cita o nome
da variável, nunca o valor.
"""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_CHAVES = RAIZ / ".env"

CHAVES = ("TELEGRAM_YT_BOT_TOKEN", "TELEGRAM_YT_CHATID", "YT_SLOTS", "YT_TEMPO_PRODUCAO_MIN", "YT_ANTECEDENCIA_MIN",
          "YT_DISCO_MIN_GB", "YT_CANAL_ALIAS", "YT_CANAL_ID", "CURSOS_IA_DIR", "TELEGRAM_API_BASE",
          "YT_SHORTS_SLOTS", "YT_SHORTS_DIR", "YT_COTA_DIA")
RE_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ErroConfig(Exception):
    pass


@dataclass
class Config:
    token: str
    chat_id: int
    slots: list
    tempo_producao_min: int = 240
    antecedencia_min: int = 90
    disco_min_gb: int = 8
    canal_alias: str = "principal"
    canal_id: str = "UC_EXEMPLO_CONFIGURE_O_SEU"
    cursos_ia: Path = field(default_factory=lambda: RAIZ.parent / "cursos-ia")
    api_base: str = "https://api.telegram.org"


def ler_arquivo(arquivo):
    valores = {}
    if arquivo and Path(arquivo).is_file():
        for linha in Path(arquivo).read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            chave = chave.strip().removeprefix("export ").strip()
            if chave in CHAVES:
                valores[chave] = valor.strip().strip('"').strip("'")
    return valores


def _inteiro(valores, nome, padrao):
    bruto = valores.get(nome)
    if not bruto:
        return padrao
    try:
        return int(bruto)
    except ValueError:
        raise ErroConfig(f"{nome} precisa ser um número inteiro.") from None


def carregar_config(ambiente=None, arquivo=None):
    ambiente = os.environ if ambiente is None else ambiente
    do_arquivo = ler_arquivo(ARQUIVO_CHAVES if arquivo is None else arquivo)
    v = {k: (ambiente.get(k) or do_arquivo.get(k) or "").strip() for k in CHAVES}
    faltam = [k for k in ("TELEGRAM_YT_BOT_TOKEN", "TELEGRAM_YT_CHATID") if not v[k]]
    if faltam:
        raise ErroConfig(f"Falta {', '.join(faltam)} no ambiente ou no arquivo de chaves do youtube-squad.")
    try:
        chat = int(v["TELEGRAM_YT_CHATID"])
    except ValueError:
        raise ErroConfig("TELEGRAM_YT_CHATID precisa ser um número (o id do seu chat com o bot).") from None
    slots = [s.strip() for s in v["YT_SLOTS"].split(",") if s.strip()]
    if not slots:
        raise ErroConfig("Falta YT_SLOTS (horários do dia, ex.: YT_SLOTS=10:00,16:00,20:00).")
    ruins = [s for s in slots if not RE_HORA.match(s)]
    if ruins:
        raise ErroConfig(f"YT_SLOTS tem horário inválido: {', '.join(ruins)} (use HH:MM de 00:00 a 23:59).")
    cfg = Config(token=v["TELEGRAM_YT_BOT_TOKEN"], chat_id=chat, slots=sorted(set(slots)),
                 tempo_producao_min=_inteiro(v, "YT_TEMPO_PRODUCAO_MIN", 240),
                 antecedencia_min=_inteiro(v, "YT_ANTECEDENCIA_MIN", 90),
                 disco_min_gb=_inteiro(v, "YT_DISCO_MIN_GB", 8))
    if v["YT_CANAL_ALIAS"]:
        cfg.canal_alias = v["YT_CANAL_ALIAS"]
    if v["YT_CANAL_ID"]:
        cfg.canal_id = v["YT_CANAL_ID"]
    if v["CURSOS_IA_DIR"]:
        cfg.cursos_ia = Path(v["CURSOS_IA_DIR"]).expanduser()
    if v["TELEGRAM_API_BASE"]:
        cfg.api_base = v["TELEGRAM_API_BASE"].rstrip("/")
    return cfg
