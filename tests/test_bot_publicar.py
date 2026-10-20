"""bot_youtube.publicar: plano do publicacao.py a partir do recriacao.json, envio com journal por pedido."""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from bot_youtube import config, fluxo, pedidos, publicar
from comum import SP
from tests.falsos_bot import FIX, CanalFalso

RAIZ = Path(__file__).resolve().parents[1]
VALIDAR_THUMB = RAIZ / ".claude/skills/thumbs-youtube/scripts/validar.py"


@pytest.fixture
def amb(tmp_path, monkeypatch):
    monkeypatch.setattr(pedidos, "ESTADO", tmp_path / "estado")
    cfg = config.Config(token="1:x", chat_id=1, slots=["10:00", "16:00"], cursos_ia=tmp_path / "cursos-ia")
    return {"tmp": tmp_path, "cfg": cfg}


def _aula(tmp_path):
    """Aula de fixture: mp4 16:9 720p com áudio (30 s), SRT, descrição com capítulos e thumbs.json de 1 variante revisado."""
    aula = tmp_path / "cursos-ia/series/recriacoes-youtube/01-agentes"
    (aula / "out").mkdir(parents=True)
    (aula / "youtube").mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=10:duration=30", "-f", "lavfi",
                    "-i", "sine=duration=30", "-shortest", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", str(aula / "out/aula.mp4")], check=True)
    (aula / "out/aula.srt").write_text((FIX / "recriacao/aula.srt").read_text())
    (aula / "youtube/descricao-final.txt").write_text((FIX / "recriacao/descricao-final.txt").read_text())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x101830:s=1280x720", "-frames:v", "1",
                    str(aula / "youtube/thumb-01.png")], check=True)
    doc = {"version": 1, "expected_variants": 1, "count_reason": "D-10 do bot-telegram-youtube: bot gera 1 par por pedido", "tool": "Agentes",
           "brand": {"source": "https://www.anthropic.com", "colors": ["#101830"], "logo_note": "sem logo"},
           "identity": {"method": "sem rosto (aula motion)", "reference": None},
           "variants": [{"id": "01", "title": "Agentes de IA em 3 passos", "headline": "Agentes em 3 passos", "concept": "c", "evidence": "e", "file": "thumb-01.png"}]}
    (aula / "youtube/thumbs.json").write_text(json.dumps(doc))
    fp = json.loads(subprocess.run([sys.executable, str(VALIDAR_THUMB), "fingerprints", str(aula / "youtube/thumbs.json")],
                                   capture_output=True, text=True, check=True).stdout)["01"]
    doc["variants"][0]["review"] = {"fingerprint": fp, "reviewer": "teste", "notes": "fixture", "face": True, "text": True, "brand": True,
                                    "composition": True, "feed": True}
    (aula / "youtube/thumbs.json").write_text(json.dumps(doc))
    return aula


def _pedido_pronto(amb, horario="2026-09-29T16:00:00-03:00"):
    aula = _aula(amb["tmp"])
    pid = pedidos.novo_pedido(url="https://youtu.be/x", etapa="aguardando_escolha")
    fluxo.escolher_modo(pid, "motion")
    rec = {"pedido": pid, "aula": "series/recriacoes-youtube/01-agentes", "modo": "motion", "video": str(aula / "out/aula.mp4"),
           "srt": str(aula / "out/aula.srt"), "thumbs": str(aula / "youtube/thumbs.json"), "thumb": str(aula / "youtube/thumb-01.png"),
           "descricao": str(aula / "youtube/descricao-final.txt"), "titulo": "Agentes de IA em 3 passos",
           "playlist": {"title": "Agentes de IA", "description": "Aulas sobre agentes de IA."}}
    (pedidos.pasta_pedido(pid) / "recriacao.json").write_text(json.dumps(rec))
    pedidos.registrar_evento(pid, "aguardando_envio", avisar=True, horario=horario, envio_em="2026-09-29T15:00:00-03:00", aula=rec["aula"])
    return pid, aula


# --- T-04.01 plano ---------------------------------------------------------------------------------

def test_plano_montado_passa_no_validar_do_publicacao(amb):
    pid, _ = _pedido_pronto(amb)
    arq = publicar.gravar_plano(pedidos.estado_pedido(pid), amb["cfg"], motivo="aprovado no Telegram")
    p = subprocess.run([sys.executable, str(RAIZ / "publicacao.py"), "validar", str(arq)], capture_output=True, text=True, cwd=RAIZ)
    assert p.returncode == 0, p.stdout
    assert json.loads(p.stdout)["publish_at"] == "2026-09-29T19:00:00Z"


def test_campos_do_plano(amb):
    pid, _ = _pedido_pronto(amb)
    plano = publicar.plano(pedidos.estado_pedido(pid), amb["cfg"], motivo="prazo sem resposta")
    assert plano["publish_local"] == "2026-09-29T16:00:00-03:00" and plano["timezone"] == "America/Sao_Paulo"
    assert plano["alias"] == "principal" and plano["channel_id"] == "UC_EXEMPLO_CONFIGURE_O_SEU"
    assert (plano["made_for_kids"], plano["contains_synthetic_media"], plano["language"], plano["category_id"]) == (False, True, "pt-BR", 27)
    assert pid in plano["authorization"] and "prazo sem resposta" in plano["authorization"]
    assert plano["playlist"] == {"title": "Agentes de IA", "description": "Aulas sobre agentes de IA."}


# --- T-04.02 enviar --------------------------------------------------------------------------------

class Rodar:
    """Executor falso: responde por script chamado e grava o journal quando `enviar` roda."""

    def __init__(self, journal=None, codigo_enviar=0):
        self.chamadas, self.journal, self.codigo_enviar = [], journal, codigo_enviar

    def __call__(self, cmd, timeout=None, cwd=None, env=None):
        self.chamadas.append(cmd)
        if "enviar" in cmd and self.journal is not None:
            estado = Path(cmd[cmd.index("--state") + 1])
            estado.write_text(json.dumps(self.journal))
            return self.codigo_enviar, "{}"
        return 0, "{}"


JOURNAL = {"done": {"video_id": "vid9", "scheduled": {"privacyStatus": "private", "publishAt": "2026-09-29T19:00:00Z"}}}


def test_enviar_registra_video_id_e_publish_at(amb):
    pid, _ = _pedido_pronto(amb)
    rodar = Rodar(JOURNAL)
    assert publicar.enviar(pid, amb["cfg"], executar=rodar, motivo="aprovado") == "enviado"
    e = pedidos.estado_pedido(pid)
    assert e["etapa"] == "enviado" and e["video_id"] == "vid9" and e["publish_at"] == "2026-09-29T19:00:00Z"
    nomes = [next((x for x in c if x in ("revisar", "validar", "enviar")), None) for c in rodar.chamadas]
    assert nomes == ["revisar", "validar", "enviar"]
    revisar = rodar.chamadas[0]
    assert revisar[revisar.index("--etapa") + 1] == "entrega" and revisar[revisar.index("--revisor") + 1] == "telegram"


def test_journal_ja_agendado_nao_reenvia(amb):
    pid, _ = _pedido_pronto(amb)
    (pedidos.pasta_pedido(pid) / "publicacao-estado.json").write_text(json.dumps(JOURNAL))
    rodar = Rodar()
    assert publicar.enviar(pid, amb["cfg"], executar=rodar) == "enviado"
    assert not any("enviar" in c for c in rodar.chamadas)


def test_journal_pendente_vira_falhou_pedindo_reconciliacao(amb):
    pid, _ = _pedido_pronto(amb)
    rodar = Rodar({"done": {}, "pending": "upload"}, codigo_enviar=1)
    assert publicar.enviar(pid, amb["cfg"], executar=rodar) == "falhou"
    assert "reconcili" in pedidos.estado_pedido(pid)["nota"]


def test_credencial_expirada_vira_bloqueado(amb):
    pid, _ = _pedido_pronto(amb)

    def rodar(cmd, timeout=None, cwd=None, env=None):
        if "enviar" in cmd:
            return 1, '{"ok": false, "error": "credencial expirada; refaça o login: .venv/bin/python auth.py principal"}'
        return 0, "{}"
    assert publicar.enviar(pid, amb["cfg"], executar=rodar) == "bloqueado"
    assert "auth.py" in pedidos.estado_pedido(pid)["nota"]


# --- T-04.03 cancelar depois do upload ---------------------------------------------------------------

def test_cancelar_enviado_desagenda_e_libera_o_slot(amb):
    from bot_youtube import slots
    pid, _ = _pedido_pronto(amb)
    pedidos.registrar_evento(pid, "enviado", avisar=True, video_id="v9", publish_at="2026-09-29T19:00:00Z")
    falso = CanalFalso(videos={"v9": {"privacyStatus": "private", "publishAt": "2026-09-29T19:00:00Z", "embeddable": True}})
    ok, texto = fluxo.cancelar(pid, cliente_fn=lambda: falso.cliente(amb["tmp"]))
    assert ok and pedidos.estado_pedido(pid)["etapa"] == "cancelado" and "privado" in texto
    assert falso.atualizacoes[-1]["body"]["id"] == "v9" and "publishAt" not in falso.atualizacoes[-1]["body"]["status"]
    assert slots.ocupados("2026-09-29", []) == []


def test_cancelar_enviado_sem_canal_recusa(amb):
    pid, _ = _pedido_pronto(amb)
    pedidos.registrar_evento(pid, "enviado", video_id="v9")
    assert fluxo.cancelar(pid)[0] is False



# --- "recriação" nunca vai para o YouTube (Usuário, 28/09/2026) ----------------------------------------

def test_termo_proibido_em_qualquer_texto_publico_nao_sobe(amb):
    pid, aula = _pedido_pronto(amb)
    (aula / "src").mkdir(exist_ok=True)
    (aula / "src/aula.json").write_text(json.dumps({"serie": "Recriações", "numero": 1}))
    rodar = Rodar(JOURNAL)
    assert publicar.enviar(pid, amb["cfg"], executar=rodar) == "falhou"
    nota = pedidos.estado_pedido(pid)["nota"]
    assert "recria" in nota.lower() and "aula.json" in nota
    assert rodar.chamadas == []


def test_textos_publicos_conferidos(amb):
    pid, aula = _pedido_pronto(amb)
    rec = publicar.recriacao(pid)
    assert publicar.termos_proibidos(rec, amb["cfg"]) == []
    (aula / "out/aula.srt").write_text((aula / "out/aula.srt").read_text().replace("terceiro", "recriado"))
    assert any("aula.srt" in x for x in publicar.termos_proibidos(rec, amb["cfg"]))
    for campo, valor in (("titulo", "Recriação: agentes"), ("playlist", {"title": "Aulas recriadas", "description": "x"})):
        assert publicar.termos_proibidos({**rec, campo: valor}, amb["cfg"])
