"""Fixtures das apresentações: o schema do deck.json (D-46), o DECK_OK canônico, um diagnóstico mínimo e PNGs válidos.

Schema do deck.json (contrato entre apresentacao.py e apresentacoes/motion; espelho do ORQUESTRADOR):

    {
      "slug": "AAAA-MM-DD-<slug>", "titulo": str, "pauta_id": "12 hex" | null,
      "criado_em": "AAAA-MM-DD", "gerado_por": "apresentador",
      "pauta": {"origem": str, "tema": str|null, "angulo": str|null},
      "marca": {"nome": str, "cor": "#RRGGBB", "cor_2": "#RRGGBB"|null, "logo": "logo.png"|null,
                "site": str|null, "origem": "tabela|site|canal"},
      "slides": [6 a 10; o primeiro tipo "titulo", o último tipo "cta"]
    }
    Tipos e limites em palavras (<b>palavra</b> só no titulo dos tipos titulo/declaracao):
      titulo       {kicker <=4, titulo <=10, subtitulo <=20}
      declaracao   {texto <=20, autor <=4 | null}
      grade        {titulo <=8, itens 3-6 x {titulo <=5, texto <=14}}
      comparacao   {titulo <=8, esquerda {titulo <=4, itens <=5 x <=8}, direita idem}
      etapas       {titulo <=8, itens 3-5 x {titulo <=4, texto <=10}}
      estatisticas {titulo <=8, numeros 1-4 x {valor number, sufixo str, rotulo <=4, fonte str não vazia}}
                   (número do TEMA da aula com fonte externa; métrica do nosso canal, do diagnóstico, nunca entra num slide)
      fluxo        {titulo <=8, nos 3-6 x {titulo <=4, texto <=8 | null}}  (diagrama: setas se desenham entre os nós)
      screenshot   {titulo <=6, imagem "<arquivo em ativos/>" | null, legenda <=12}
      cta          {titulo <=10, texto <=16, url "example.com", imagem "cta.png" | null}
    Proibido: travessão, meia-risca e "\\n" em qualquer texto. Imagem é nome de arquivo dentro de ativos/, sem barra.
"""
import copy
import struct
import zlib

DECK_OK = {
    "slug": "2026-09-23-supabase-para-software-house", "titulo": "Supabase para software house",
    "pauta_id": "0123456789ab", "criado_em": "2026-09-23", "gerado_por": "apresentador",
    "pauta": {"origem": "tema", "tema": "Supabase", "angulo": "Quando trocar o backend próprio pelo Supabase"},
    "marca": {"nome": "Supabase", "cor": "#3ECF8E", "cor_2": None, "logo": "logo.png", "site": "https://supabase.com", "origem": "tabela"},
    "slides": [
        {"tipo": "titulo", "kicker": "Backend em minutos", "titulo": "Supabase no lugar do <b>backend</b> próprio", "subtitulo": "O que muda para uma software house que entrega sistema para cliente"},
        {"tipo": "declaracao", "texto": "Toda hora que você escreve CRUD de novo é hora que o cliente não paga", "autor": "Usuário"},
        {"tipo": "grade", "titulo": "O que vem pronto", "itens": [
            {"titulo": "Postgres gerenciado", "texto": "Banco de verdade com backup e réplica sem operar servidor"},
            {"titulo": "Auth", "texto": "Login com email, OAuth e magic link em uma chamada"},
            {"titulo": "Storage", "texto": "Arquivos com permissão por linha, direto do banco"},
            {"titulo": "Realtime", "texto": "Mudança no banco vira evento no front"}]},
        {"tipo": "comparacao", "titulo": "Backend próprio contra Supabase", "esquerda": {"titulo": "Backend próprio", "itens": ["Semanas de CRUD", "Deploy e monitoramento seus", "Auth escrita na mão"]},
         "direita": {"titulo": "Supabase", "itens": ["Tabela vira API na hora", "Deploy do fornecedor", "Auth pronta e testada"]}},
        {"tipo": "etapas", "titulo": "Como começar sem quebrar o que existe", "itens": [
            {"titulo": "Escolha um módulo", "texto": "Um cadastro novo, não o sistema inteiro"},
            {"titulo": "Modele no Postgres", "texto": "Tabela, política de linha e índice"},
            {"titulo": "Ligue o front", "texto": "Cliente JS com a chave pública"},
            {"titulo": "Meça", "texto": "Tempo de entrega antes e depois"}]},
        {"tipo": "estatisticas", "titulo": "Os números do Supabase", "numeros": [
            {"valor": 100, "sufixo": "%", "rotulo": "Postgres puro", "fonte": "supabase.com/docs, 2026-09-23"},
            {"valor": 2, "sufixo": " projetos", "rotulo": "grátis no plano free", "fonte": "supabase.com/pricing, 2026-09-23"}]},
        {"tipo": "fluxo", "titulo": "Como o dado anda", "nos": [
            {"titulo": "Front do cliente", "texto": "React com o cliente JS"},
            {"titulo": "API automática", "texto": "PostgREST em cima da tabela"},
            {"titulo": "Política de linha", "texto": "Quem vê o quê"},
            {"titulo": "Postgres", "texto": "Backup e réplica gerenciados"},
            {"titulo": "Realtime", "texto": "Mudança vira evento no front"}]},
        {"tipo": "screenshot", "titulo": "O painel do Supabase", "imagem": "print.png", "legenda": "Tabela criada e API pronta na mesma tela"},
        {"tipo": "cta", "titulo": "Quer o método inteiro?", "texto": "O ecossistema da seu canal está no Seu Site, grátis", "url": "example.com", "imagem": "cta.png"},
    ],
}

TITULOS = ["ADEUS, Claude Code! Descubra a Melhor Alternativa GRÁTIS", "Cursor ou Claude Code: qual usar na software house",
           "Agentes de IA fazendo code review sozinhos", "n8n para automatizar o onboarding do cliente", "Supabase substitui o backend?",
           "OpenCode: o agente open source que roda local", "Como cobrar por projeto com IA", "Short: prompt que economiza 2 horas",
           "Short: Claude Code em 60 segundos", "Postgres na software house: 5 erros", "Vercel para entregar mais rápido", "Short: n8n em 1 minuto"]


def diagnostico_mini():
    videos = []
    for i, t in enumerate(TITULOS):
        views = 6724 - i * 500
        short = t.startswith("Short")
        videos.append({"id": f"v{i:02d}", "titulo": t, "formato": "SHORTS" if short else "VIDEO_ON_DEMAND",
                       "link": f"https://www.youtube.com/watch?v=v{i:02d}", "publicado_em": f"2026-0{1 + i % 9}-1{i % 9}",
                       "duracao_seg": 45 if short else 900 + i * 30, "views": views, "minutos": views * 3,
                       "duracao_media": 300 - i * 10, "pct_assistido": 40.0 - i, "curtidas": 200 - i * 10, "comentarios": 20 - i,
                       "compartilhamentos": 100 - i * 5, "inscritos": 130 - i * 10, "interacoes": 320 - i * 16,
                       "taxa_engajamento": 5.0 - i * 0.2, "inscritos_por_mil_views": round((130 - i * 10) / views * 1000, 2),
                       "mediana_do_formato": 3974, "nota": 10 if i < 6 else 5})
    videos[3]["views"] = 90                     # abaixo de 100 views: fora do top por inscritos
    videos[3]["inscritos_por_mil_views"] = 400.0
    videos[11]["curtidas"] = None               # métrica ausente, como no dado real
    videos[11]["interacoes"] = None
    videos[11]["taxa_engajamento"] = None
    return {"gerado_em": "2026-09-23T10:00:00", "canal": {"id": "UC1", "titulo": "Canal", "handle": "@canal"},
            "kpis": {"janela": {"desde": "2026-09-15", "ate": "2026-09-22"}, "basicas": [], "performance": [], "series": {}},
            "videos": sorted(videos, key=lambda v: -v["views"])}


DIAGNOSTICO_MINI = diagnostico_mini()


def png(largura, altura, cor=(22, 24, 26)):
    """PNG RGB válido gerado só com a stdlib."""
    def bloco(tipo, dados):
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)
    linha = b"\x00" + bytes(cor) * largura
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0))
            + bloco(b"IDAT", zlib.compress(linha * altura, 9)) + bloco(b"IEND", b""))


def ativos_falsos(pasta):
    """Grava os ativos que o DECK_OK cita: screenshot do CTA, print da ferramenta e logo."""
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "cta.png").write_bytes(png(1920, 1080, (11, 11, 11)))
    (pasta / "print.png").write_bytes(png(1920, 1080, (30, 30, 30)))
    (pasta / "logo.png").write_bytes(png(64, 64, (62, 207, 142)))
    return sorted(p.name for p in pasta.iterdir())


def deck(**mudancas):
    d = copy.deepcopy(DECK_OK)
    d.update(mudancas)
    return d
