"""chat.py: a conversa guarda o fio, executa pedidos com permissões explícitas e nunca vê os segredos."""
import subprocess
import sys

import pytest

import chat
import daily


@pytest.fixture
def claude(tmp_path, monkeypatch):
    monkeypatch.setattr(daily, "RAIZ", tmp_path)
    monkeypatch.setattr(chat, "RAIZ", tmp_path)
    chamadas, respostas = [], []

    def run(cmd, ao_responder=None, ao_progresso=None):
        chamadas.append(cmd)
        r = respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        if not isinstance(r, dict):
            raise chat.Erro("Failed to authenticate")
        return r

    monkeypatch.setattr(chat, "_executar_stream", run)
    return chamadas, respostas


def ok(texto, sid="sessao-1"):
    return {"result": texto, "session_id": sid, "is_error": False}


def test_primeira_mensagem_abre_a_sessao_com_o_retrato_e_a_segunda_so_retoma(claude):
    chamadas, respostas = claude
    respostas += [ok("@analista\nAs views caíram 12% na semana."), ok("@analista\nSobe se o Short de quarta pegar.")]
    falas = [{"quem": "analista", "texto": "Views do canal em 7 dias: 33.462."}]
    r1 = chat.dizer("c20260920-010101", "Por que as views caíram?", falas=falas, regras=[{"id": "d001", "tipo": "nao-fazer", "texto": "Não use clickbait"}])
    r2 = chat.dizer("c20260920-010101", "E quando sobe?")
    assert (r1["autor"], r1["texto"], r1["claude"]) == ("analista", "As views caíram 12% na semana.", "sessao-1")
    primeira, segunda = chamadas
    assert "--resume" not in primeira and "33.462" in primeira[2] and "Não use clickbait" in primeira[2] and "Por que as views caíram?" in primeira[2]
    assert segunda[segunda.index("--resume") + 1] == "sessao-1" and segunda[2] == "E quando sobe?"          # o fio é da sessão, não do prompt
    for cmd in chamadas:
        assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk"
        assert "bypassPermissions" not in " ".join(cmd)
        negadas = cmd[cmd.index("--disallowedTools") + 1]
        assert "tokens/" in negadas and "client_secret" in negadas and ".env" in negadas
        assert "--allowedTools" in cmd and cmd[cmd.index("--model") + 1] == chat.modelo()
    assert [m["autor"] for m in chat.mensagens("c20260920-010101")] == ["usuario", "analista", "usuario", "analista"] and r2["autor"] == "analista"


def test_quem_o_usuario_chamou_e_quem_responde_e_travessao_nao_passa(claude):
    chamadas, respostas = claude
    respostas += [ok("Começo pelo roteiro do Claude Code — o gancho já está pronto."), ok("@estagiario\nOi.")]
    r = chat.dizer("c1", "Qual vídeo sai primeiro?", para="roteirista")
    assert r["autor"] == "roteirista" and "—" not in r["texto"] and chamadas[0][2].endswith("[para @roteirista] Qual vídeo sai primeiro?")
    assert chat.dizer("c2", "oi")["autor"] == "planejador"                                   # @ que não é da equipe cai em quem toca a daily
    with pytest.raises(chat.Erro):
        chat.dizer("c1", "oi", para="estagiario")
    with pytest.raises(chat.Erro):
        chat.dizer("c1", "   ")


def test_sessao_do_claude_perdida_recomeca_com_a_conversa_colada(claude):
    chamadas, respostas = claude
    respostas += [ok("@planejador\nBom dia."), {"result": "No conversation found", "is_error": True}, ok("@planejador\nSeguimos.", "sessao-2")]
    chat.dizer("c1", "Bom dia, time")
    r = chat.dizer("c1", "Onde paramos?")
    assert r["texto"] == "Seguimos." and chat.sessao_do_claude("c1") == "sessao-2"
    assert "--resume" not in chamadas[2] and "Usuário: Bom dia, time" in chamadas[2][2] and "@planejador: Bom dia." in chamadas[2][2]


def test_sessao_antiga_reabre_com_historico_e_pedido_para_hoje(claude):
    chamadas, respostas = claude
    chat._gravar({"sessao": "c1", "autor": "usuario", "texto": "Quero trocar a pauta de hoje"})
    chat._gravar({"sessao": "c1", "autor": "planejador", "texto": "Leve para a daily amanhã.", "claude": "antiga"})
    respostas.append(ok("@planejador\nTroquei a pauta no plano de hoje.", "nova"))
    r = chat.dizer("c1", "Faça essa troca hoje")
    assert "--resume" not in chamadas[0]
    assert "Usuário: Quero trocar a pauta de hoje" in chamadas[0][2]
    assert "execute na mesma sessão" in chamadas[0][2]
    assert "sem adiar para a daily" in chamadas[0][2]
    assert chat.sessao_do_claude("c1") == "nova" and r["versao_execucao"] == chat.VERSAO_EXECUCAO


def test_falha_de_execucao_nao_repete_acao_ao_reabrir_sessao(claude):
    chamadas, respostas = claude
    respostas += [ok("@planejador\nPronto.", "s1"), {"result": "Coleta falhou no meio", "is_error": True}]
    chat.dizer("c1", "Prepare o plano")
    r = chat.dizer("c1", "Rode a coleta")
    assert r["erro"] and "Coleta falhou" in r["texto"]
    assert len(chamadas) == 2 and "--resume" in chamadas[1]


def test_permissao_negada_nao_vira_sucesso_nem_repete(claude):
    chamadas, respostas = claude
    respostas.append({"result": "Feito.", "is_error": False, "permission_denials": [{"tool_name": "Bash"}]})
    r = chat.dizer("c1", "Rode a coleta")
    assert r["erro"] and "permissão negada" in r["texto"]
    assert len(chamadas) == 1


def test_falha_do_claude_vira_aviso_no_chat_e_a_mensagem_dele_fica(claude):
    _, respostas = claude
    respostas += ["isso não é json", subprocess.TimeoutExpired("claude", 1)]
    r = chat.dizer("c1", "oi")
    assert r["erro"] and r["autor"] == "painel" and "Failed to authenticate" in r["texto"]
    assert "passou do tempo" in chat.dizer("c1", "e agora?")["texto"]
    assert [m["texto"] for m in chat.mensagens("c1") if m["autor"] == "usuario"] == ["oi", "e agora?"] and chat.sessao_do_claude("c1") is None


def test_chat_nao_cria_item_na_daily_automaticamente_e_lista_as_conversas(claude):
    _, respostas = claude
    respostas += [ok("@planejador\nRegistrei a orientação no harness."), ok("@curador\nTem 899 vídeos.", "s9")]
    chat.dizer("c20260920-010101", "Não fale mais de GLM")
    chat.dizer("c20260920-020202", "Quantos vídeos tem o cérebro?")
    assert daily.eventos() == [] and daily.regras() == []                                   # conversa não vira ordem sozinha
    assert [(s["sessao"], s["mensagens"], s["titulo"]) for s in chat.sessoes()] == [("c20260920-020202", 2, "Quantos vídeos tem o cérebro?"), ("c20260920-010101", 2, "Não fale mais de GLM")]


def test_canais_isolam_historico_e_pergunta_some_depois_da_resposta(claude):
    _, respostas = claude
    respostas += [ok("@analista\nQual período? [AGUARDA_USUARIO]", "analista-1"), ok("@roteirista\nO roteiro está pronto.", "copy-1"), ok("@analista\nVou considerar sete dias.", "analista-1")]
    analista, copy = chat.sessao_do_canal("analista"), chat.sessao_do_canal("roteirista")
    chat.dizer(analista, "Confira as views", para="analista")
    chat.dizer(copy, "Como está o roteiro?", para="roteirista")
    assert {c["id"] for c in chat.canais() if c["aguarda_usuario"]} == {"analista"}
    assert "AGUARDA_USUARIO" not in chat.mensagens(analista)[-1]["texto"]
    chat.dizer(analista, "Sete dias", para="analista")
    assert not any(c["aguarda_usuario"] for c in chat.canais())
    assert len(chat.mensagens(copy)) == 2 and chat.sessao_do_claude(analista) == "analista-1"
    assert chat.sessao_do_canal("todos") not in (analista, copy)
    with pytest.raises(chat.Erro):
        chat.sessao_do_canal("inexistente")


def test_conversa_individual_preserva_o_agente_escolhido(claude):
    _, respostas = claude
    respostas.append(ok("@planejador\nMinha revisão está pronta."))
    assert chat.dizer(chat.sessao_do_canal("reviewer"), "Revisou?", para="reviewer")["autor"] == "reviewer"


def test_stream_entrega_texto_antes_do_resultado_e_nao_espera_saida_do_processo(tmp_path, monkeypatch):
    import threading
    import time
    monkeypatch.setattr(chat, 'RAIZ', tmp_path)
    recebido, concluiu = threading.Event(), threading.Event()
    textos, resultados = [], []
    liberar = tmp_path / 'liberar'
    sair = tmp_path / 'sair'
    script = '''import json,time,pathlib
print(json.dumps({'type':'assistant','parent_tool_use_id':'subagente','message':{'content':[{'type':'text','text':'Privado'}]}}),flush=True)
print(json.dumps({'type':'assistant','message':{'content':[{'type':'thinking','thinking':'Privado'}]}}),flush=True)
print(json.dumps({'type':'assistant','message':{'content':[{'type':'text','text':'Vou ler'},{'type':'tool_use','name':'Read'}]}}),flush=True)
print(json.dumps({'type':'assistant','session_id':'s1','message':{'stop_reason':None,'content':[{'type':'text','text':'Resposta pronta'}]}}),flush=True)
while not pathlib.Path('liberar').exists():time.sleep(.01)
print(json.dumps({'type':'result','result':'Resposta pronta','session_id':'s1'}),flush=True)
while not pathlib.Path('sair').exists():time.sleep(.01)
'''
    def executar():
        resultados.append(chat._executar_stream([sys.executable, '-c', script],
                          lambda texto, sid: (textos.append((texto, sid)), recebido.set() if texto == 'Resposta pronta' else None)))
        concluiu.set()
    thread = threading.Thread(target=executar, daemon=True)
    thread.start()
    try:
        assert recebido.wait(5)
        assert textos == [('Vou ler', None), ('Resposta pronta', 's1')]
        assert not concluiu.is_set()
        liberar.touch()
        assert concluiu.wait(5), 'resultado não pode esperar o processo encerrar'
        assert resultados[0]['result'] == 'Resposta pronta'
    finally:
        liberar.touch(); sair.touch(); thread.join(5)


def test_stream_final_nao_duplica_mensagem_e_resultado_de_erro_fica_visivel(tmp_path, monkeypatch):
    monkeypatch.setattr(chat, 'RAIZ', tmp_path)
    def executar(cmd, ao_responder, ao_progresso=None):
        ao_responder('@analista\nRecebi os dados.', 's1')
        assert chat.mensagens('c1')[-1]['texto'] == 'Recebi os dados.'
        return ok('@analista\nRecebi os dados.', 's1')
    monkeypatch.setattr(chat, '_executar_stream', executar)
    chat.dizer('c1', 'Confira os dados')
    assert len(chat.mensagens('c1')) == 2
    def falhar(cmd, ao_responder, ao_progresso=None):
        ao_responder('@analista\nVou conferir.', 's1')
        return {'is_error': True, 'result': 'A ferramenta falhou'}
    monkeypatch.setattr(chat, '_executar_stream', falhar)
    chat.dizer('c1', 'Continue')
    assert chat.mensagens('c1')[-1]['erro']
    assert 'A ferramenta falhou' in chat.mensagens('c1')[-1]['texto']


def test_stream_timeout_e_saida_sem_resultado(tmp_path, monkeypatch):
    monkeypatch.setattr(chat, 'RAIZ', tmp_path)
    with pytest.raises(chat.Erro, match='sem entregar um resultado'):
        chat._executar_stream([sys.executable, '-c', 'print("invalido")'])
    monkeypatch.setattr(chat, 'TEMPO_MAXIMO', .15)
    with pytest.raises(subprocess.TimeoutExpired):
        chat._executar_stream([sys.executable, '-c', 'import time; time.sleep(10)'])


def test_resultado_vazio_anterior_nao_encerra_pergunta_e_ferramentas_informam_progresso(tmp_path, monkeypatch):
    monkeypatch.setattr(chat, 'RAIZ', tmp_path)
    script = '''import json
for e in [
 {'type':'result','is_error':False,'result':''},
 {'type':'assistant','message':{'content':[{'type':'thinking','thinking':'privado'},{'type':'tool_use','name':'Bash','input':{'command':'segredo'}}]}},
 {'type':'assistant','session_id':'s1','message':{'content':[{'type':'text','text':'Vou comparar os horários.'},{'type':'tool_use','name':'Read'}]}},
 {'type':'result','result':'Concluído','session_id':'s1'}
]:print(json.dumps(e),flush=True)
'''
    textos, etapas = [], []
    r = chat._executar_stream([sys.executable, '-c', script], lambda t, s: textos.append(t), etapas.append)
    assert r['result'] == 'Concluído'
    assert textos == ['Vou comparar os horários.']
    assert etapas == ['Consultando dados e executando comandos', 'Lendo os dados do projeto']
    assert 'segredo' not in str(etapas) and 'privado' not in str(textos)


def test_erro_sem_result_traz_motivo_do_harness(claude):
    _, respostas = claude
    respostas.append({'type': 'result', 'is_error': True, 'errors': ['Limite da sessão atingido']})
    r = chat.dizer('c1', 'Oi')
    assert r['erro'] and 'Limite da sessão atingido' in r['texto']


def test_equipe_na_ordem_fixa_e_mesmos_destinatarios_da_daily():
    assert list(chat.EQUIPE) == ["planejador", "analista", "roteirista", "curador", "bibliotecario", "reviewer", "apresentador", "validador"]
    assert tuple(chat.EQUIPE) == daily.EQUIPE and "validador" in daily.PARA
    assert chat.sessao_do_canal("todos") == "c20000101-000000" and chat.sessao_do_canal("reviewer") == "c20000101-000006"
    assert chat.sessao_do_canal("apresentador") == "c20000101-000007" and chat.sessao_do_canal("validador") == "c20000101-000008"
    assert "apresentacao.py" in chat.abertura("") and "/apresentacao" in chat.abertura("")


def test_abertura_fala_do_youtube_e_proibe_publicar(claude):
    chamadas, respostas = claude
    respostas.append(ok("@planejador\nOi."))
    chat.dizer("c1", "oi")
    abertura = chamadas[0][2]
    assert "YouTube" in abertura and "Instagram" not in abertura
    assert "nunca suba vídeo" in abertura.lower() and "comentário" in abertura


def test_modelo_e_binario_configuraveis(monkeypatch):
    assert chat.comando("oi")[chat.comando("oi").index("--model") + 1] == "sonnet"
    monkeypatch.setenv("YT_CHAT_MODELO", "opus")
    monkeypatch.setenv("CLAUDE_BIN", "/opt/claude")
    cmd = chat.comando("oi")
    assert cmd[0] == "/opt/claude" and cmd[cmd.index("--model") + 1] == "opus"
