"""Serviço do bot: laço de long polling, trabalhador de produção, enviador e sonda do HeyGen na subida.

LaunchAgent próprio `com.canal.telegram-bot-youtube` (o do Instagram é `com.canal.telegram-bot`), uma instância só
(estado/bot-youtube/bot.lock), log em estado/bot-youtube/bot.log. O plist não leva token nem chave: o processo lê
o arquivo de chaves do squad na subida."""
import fcntl
import logging
import os
import plistlib
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import pedidos

RAIZ = Path(__file__).resolve().parent.parent
ROTULO = "com.canal.telegram-bot-youtube"
log = logging.getLogger("bot_youtube")


def trava_de_instancia():
    caminho = pedidos.ESTADO / "bot.lock"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    f = open(caminho, "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        return None
    return f


def _trabalhador(cfg, cliente_fn):
    from . import producao
    while True:
        pid = producao.proximo_trabalho()
        if not pid:
            return
        try:
            try:
                cliente = cliente_fn()
            except Exception:  # noqa: BLE001 - sem canal, a produção segue; o envio trata o login
                cliente = None
            if producao.produzir(pid, cfg, cliente=cliente) == "ocupado":
                return
        except Exception as e:  # noqa: BLE001
            log.exception("produção %s", pid)
            pedidos.registrar_evento(pid, "falhou", avisar=True, nota=f"erro ao produzir: {str(e)[:300]}")


def rodar():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    trava = trava_de_instancia()
    if not trava:
        print("o bot do YouTube já está rodando (estado/bot-youtube/bot.lock)")
        return 1
    from . import bot as botmod
    from . import canal, enviador, sonda_heygen, telegram
    from .config import carregar_config
    from .producao import proximo_trabalho
    cfg = carregar_config()
    tg = telegram.Telegram(cfg.token, api_base=cfg.api_base)
    cliente_fn = lambda: canal.conectar(cfg.canal_alias)  # noqa: E731
    threading.Thread(target=lambda: sonda_heygen.sondar(cfg.cursos_ia), name="sonda-heygen", daemon=True).start()
    fio = {}

    def despachar():
        if proximo_trabalho() and not (fio.get("t") and fio["t"].is_alive()):
            fio["t"] = threading.Thread(target=_trabalhador, args=(cfg, cliente_fn), name="producao", daemon=True)
            fio["t"].start()
    parar, acordar = threading.Event(), threading.Event()
    threading.Thread(target=enviador.laco, args=(parar, acordar, cfg), name="enviador", daemon=True).start()
    b = botmod.Bot(tg, cfg.chat_id, despachar=despachar, acordar_envio=acordar.set, cliente_fn=cliente_fn)
    log.info("bot do YouTube no ar: @%s", tg.chamar("getMe").get("username"))
    despachar()
    espera = 5
    while True:
        try:
            b.passo()
            despachar()
            espera = 5
        except telegram.ErroTelegram as e:
            log.warning("%s", e)
            time.sleep(30 if e.codigo == 409 else espera)
            espera = min(espera * 2, 300)
        except KeyboardInterrupt:
            parar.set()
            return 0
        except Exception:  # noqa: BLE001
            log.exception("passo")
            time.sleep(espera)
            espera = min(espera * 2, 300)


def plist():
    caminhos = [Path(sys.executable).parent, Path.home() / ".local" / "bin", Path("/opt/homebrew/bin"), Path("/usr/local/bin"),
                Path("/Library/Frameworks/Python.framework/Versions/3.11/bin")]
    for binario in ("claude", "node", "yt-dlp", "whisper", "ffmpeg"):
        achado = shutil.which(binario)
        if achado:
            caminhos.insert(0, Path(achado).parent)
    path = ":".join(dict.fromkeys(str(c) for c in caminhos)) + ":/usr/bin:/bin:/usr/sbin:/sbin"
    log_arq = str(pedidos.ESTADO / "bot.log")
    return {"Label": ROTULO, "ProgramArguments": [sys.executable, str(RAIZ / "bot_youtube.py"), "rodar"],
            "WorkingDirectory": str(RAIZ), "RunAtLoad": True, "KeepAlive": True, "ThrottleInterval": 30,
            "StandardOutPath": log_arq, "StandardErrorPath": log_arq, "ProcessType": "Background",
            "EnvironmentVariables": {"PATH": path, "HOME": str(Path.home()), "USER": os.environ.get("USER") or Path.home().name,
                                     "TZ": "America/Sao_Paulo", "LANG": "pt_BR.UTF-8", "PYTHONUNBUFFERED": "1"}}


def _launchctl(cmd):
    return subprocess.run(cmd, capture_output=True).returncode


def instalar(pasta=None, launchctl=None):
    pasta = Path(pasta or Path.home() / "Library" / "LaunchAgents")
    launchctl = launchctl or _launchctl
    pasta.mkdir(parents=True, exist_ok=True)
    pedidos.ESTADO.mkdir(parents=True, exist_ok=True)
    arq = pasta / f"{ROTULO}.plist"
    arq.write_bytes(plistlib.dumps(plist()))
    dominio = f"gui/{os.getuid()}"
    launchctl(["launchctl", "bootout", f"{dominio}/{ROTULO}"])
    launchctl(["launchctl", "bootstrap", dominio, str(arq)])
    return arq


def desinstalar(pasta=None, launchctl=None):
    pasta = Path(pasta or Path.home() / "Library" / "LaunchAgents")
    (launchctl or _launchctl)(["launchctl", "bootout", f"gui/{os.getuid()}/{ROTULO}"])
    (pasta / f"{ROTULO}.plist").unlink(missing_ok=True)
