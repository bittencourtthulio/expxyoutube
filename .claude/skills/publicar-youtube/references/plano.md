# Plano de publicação e executor

Executor no projeto YouTube Squad: `publicacao.py`. Usar o Python de `.venv`, que já tem cliente Google.
Exemplo de estrutura (substituir pelos dados reais; caminhos relativos ao arquivo plano.json):

```json
{
  "alias": "apelido-autenticado",
  "channel_id": "ID_CONFERIDO_NA_API",
  "authorization": "Pedido explícito do usuário nesta sessão: enviar esta aula e agendar na data abaixo.",
  "publish_local": "2026-10-05T10:00:00-03:00",
  "timezone": "America/Sao_Paulo",
  "video": "../out/aula.mp4",
  "description": "rascunho-v02/descricao.txt",
  "captions": "rascunho-v02/legenda-video-01.srt",
  "thumbs": "rascunho-v02/thumbs.json",
  "made_for_kids": false,
  "contains_synthetic_media": true,
  "playlist": {"id": "ID_DA_PLAYLIST_EXISTENTE"}
}
```

Para criar playlist autorizada, trocar `playlist` por `{"title":"Nome da série", "description":"Descrição real", "privacy":"public"}`.
O executor consulta todas as páginas e rejeita criação se já existe título idêntico: conferir a playlist e usar seu ID.
Após criar a primeira, reutilizar esse ID nos planos seguintes. Não copiar o plano/journal de outra aula sem corrigir arquivos/destino.
Campos opcionais: `language` (pt-BR), `category_id` (27/Educação), `notify_subscribers` (true).
Para uma única thumbnail/título e nenhum experimento, registrar `ab_test: false`; o relatório informa
“não solicitado” e a sessão encerra após a conferência por API, sem etapa de Studio.
Valores booleanos do exemplo não substituem avaliação do conteúdo real.

Executar na raiz do squad:

```sh
.venv/bin/python publicacao.py validar /caminho/plano.json
.venv/bin/python publicacao.py enviar /caminho/plano.json --state /caminho/publicacao-estado.json
.venv/bin/python publicacao.py verificar /caminho/plano.json --state /caminho/publicacao-estado.json
```

- `validar`: sem rede e sem escrita; confere dados, hash dos arquivos, manifesto de thumbs e fuso/offset.
  Usa `ffprobe` já instalado para vídeo 16:9/HD, áudio e duração. Valida pelo menos três capítulos
  começando em zero, crescentes, com 10 s mínimos (inclusive o último); confere índices, texto e
  tempos do SRT dentro do vídeo. O JSON de saída inclui metadados, capítulos e quantidade de legendas.
  Isso comprova estrutura; não comprova que os capítulos/legendas correspondem semanticamente à aula.
  A validação não comprova autorização: o agente deve citar fielmente o pedido na sessão, não inventá-lo.
- `enviar`: mutação externa, somente no pedido autorizado. Lock exclui dois envios simultâneos com mesmo journal.
  O journal é exclusivo da aula e prende plano+hashes. Nunca usar um journal novo para repetir uma operação incerta.
- `verificar`: consulta recursos remotos conhecidos, sem escrita no canal ou journal. Exige mesmo plano/arquivos.
  Antes da hora, espera privado + publishAt correto; depois da hora, espera público (publishAt pode desaparecer).
  Aceita qualquer um dos títulos aprovados, pois o A/B pode alterná-los. Confere o ID da legenda enviada e
  os campos de status preservados. Nunca publica como correção se o vídeo continuar privado depois da hora.
  O resultado A/B ainda exige consulta ao Studio.

Código 0: etapa/checagens aprovadas; 1: erro ou bloqueio; 2: envio aceito, mas alguma checagem remota ainda pendente.
Após 2, inspecionar checks e retomar somente `verificar`; não iniciar outro upload. O polling de enviar faz no máximo
cinco rodadas de consultas (esperas 2,4,8,16 s); não garante que o processamento terminou nesse período.

O executor nunca configura A/B, não atualiza títulos depois do teste, não publica imediatamente nem cancela/exclui vídeo.
Não acompanha indefinidamente em segundo plano. `authorization` é registro do pedido, não um mecanismo mágico de aprovação.

## Resposta incerta e reconciliação

Journal marca pending ANTES de cada operação e grava resultado/ID imediatamente ao retorno. Se a chamada falhar,
interromper. Ver o recurso com ID conhecido; para upload sem ID, listar uploads recentes do canal e conferir título,
janela/duração/arquivo no Studio. Não concluir identidade só pelo título. Listar legendas e playlistItems para confirmar
se a etapa correspondente já ocorreu. Nunca guardar URI assinada de sessão de upload em logs comuns.

Depois de evidência inequívoca, a sessão pode registrar no journal o resultado real em done, documentar fonte/data e
remover apenas o pending reconciliado. Se não puder provar envio ou ausência, manter o bloqueio concreto. Não há
comando de “limpar pending” nem repetição cega. Não alterar hashes antigos para fazer um plano diferente passar.

`containsSyntheticMedia` pode não aparecer na leitura videos.list; a resposta do update comprova aceitação do campo,
mas a conferência visual no Studio continua indicada. A miniatura padrão é verificada como presente via API;
correspondência visual e variantes A/B exigem Studio.

Regras dos capítulos: https://support.google.com/youtube/answer/9884579?hl=pt-BR . O preflight valida os
timestamps; a disponibilidade de capítulos no canal e sua exibição final continuam sendo condições do YouTube.
