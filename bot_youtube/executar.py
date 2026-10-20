"""Processos externos (claude, yt-dlp, whisper, ffmpeg, scripts): (código, saída), 124 no timeout, 127 sem binário.
O processo roda num grupo próprio; no timeout o grupo inteiro morre."""
import os
import signal
import subprocess


def rodar(cmd, timeout=None, cwd=None, env=None, limite_saida=4000):
    try:
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             stdin=subprocess.DEVNULL, start_new_session=True)
    except FileNotFoundError:
        return 127, f"{cmd[0]} não está no PATH"
    try:
        saida, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGTERM)
            try:
                p.wait(5)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        p.communicate()
        return 124, f"{os.path.basename(cmd[0])} passou do limite de {timeout} s"
    return p.returncode, (saida or "")[-limite_saida:]
