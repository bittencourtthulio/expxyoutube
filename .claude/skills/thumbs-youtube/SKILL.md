---
name: thumbs-youtube
description: Criar ou revisar três pares de thumbnail e título para os vídeos do Usuário, preservando seu rosto e a identidade visual da ferramenta. Usar em pedidos de thumbs, miniaturas ou variações para teste no YouTube; não publica nem agenda vídeos.
---

# Thumbnails e títulos do Usuário

## Contrato aprendido e aprovado

- Por padrão, entregar **três pares numerados**: título, texto da thumb, conceito e JPG final. Cada par testa um gancho diferente do mesmo vídeo, não só outra cor. Quantidade explicitamente solicitada prevalece.
- Série sobre ferramenta: nome oficial da ferramenta no título e na própria thumb. Usar logo oficial quando disponível, sem inventar símbolo. Paleta principal e destaques vêm da marca da ferramenta; a linguagem do canal orienta composição, não substitui a marca do tema.
- Ler roteiro, legenda ou vídeo antes de formular promessas. Número/benchmark só com trecho e contexto verificáveis. Não transformar teste específico em garantia geral. Título complementa a imagem, sem repetir toda a frase.
- Rosto do Usuário deve corresponder à referência real: nariz, olhos, mandíbula, cabelo e textura. Nunca usar uma geração com defeito como referência de identidade para as próximas.
- Ajuste de texto não exige gerar o rosto de novo. Preservar o que foi aprovado; aplicar alterações pontuais e versionar a entrega.

## Fluxo

1. **Briefing:** identificar vídeo, série, ferramenta e canal efetivamente escolhido. Não presumir o canal pelo token padrão ou por CLAUDE.md. Amostrar thumbs recentes desse canal apenas para análise visual, sem copiá-las como referência de geração.
2. **Marca e rosto:** localizar ativos oficiais e sua fonte. Conferir referências antes de enviar ao gerador. Quando houver Soul ID existente, consultar e reutilizar; não treinar outro sem necessidade. Para referências e exemplos locais, ler [referência da sessão](references/exemplo.md).
3. **Três hipóteses:** escrever título + texto curto + ideia visual + evidência do conteúdo para cada variante. Manter identidade de série. O nome/logo fica em área de marca; o gancho, em área própria, com margens. Evitar fonte esmagada, contorno grosso por padrão, texto sobre rosto/mãos/elemento principal e excesso de palavras.
4. **Produção:** usar a ferramenta de imagem disponível conforme suas instruções. Se Higgsfield for escolhido, consultar as skills Higgsfield de thumbnail/Soul presentes no ambiente. Se a ferramenta não estiver disponível, informar o limite concreto; não prometer geração sem job. Planejar espaço livre para texto já no prompt. Para sobreposição solicitada, preferir texto e logo em camada determinística editável (Canvas/HTML), depois exportar o JPG achatado. Texto embutido por IA apenas quando solicitado.
5. **Custos e retomada:** conferir saldo e modelo antes de operação paga; persistir provedor, modelo, prompt, ID real, estado e arquivo. Resultado incerto exige consulta antes de repetir. Não manter tentativas pagas quando a identidade falha. Declarar a procedência real: foto associada ao Soul não significa saída direta do modelo Soul.
6. **Revisão:** abrir cada JPG final e a prévia de feed (aprox. 320 px; checar também leitura geral a 120 px). Conferir rosto/nariz, texto correto, nome da ferramenta, logo, paleta, margens, hierarquia, contraste e sobreposições. Corrigir e abrir de novo o que mudou. Registrar a revisão dos arquivos atuais, nunca copiar um checklist antigo.
7. **Entrega:** três JPGs 16:9, padrão local 1280×720 e abaixo de 2 MB; três títulos; prévia conjunta e de feed; base sem texto; fonte, logo, prompt e composição editável; manifesto e revisão. Descrição/SRT só fazem parte quando solicitados ou já pertencentes ao pacote, preservando o CTA inicial do Seu Site e capítulos conferidos. Não ampliar revisão de thumbs para upload/agendamento.

## Validação e aprovação

Ler [manifesto e validação](references/manifesto.md). O script local `scripts/validar.py` verifica arquivos, pares, nomes, formato e se a revisão pertence à versão atual. Não avalia beleza, semelhança facial ou verdade do vídeo: isso exige abrir as imagens e consultar o conteúdo.

Distinguir **revisado pelo agente**, **aprovado pelo usuário** e **teste configurado no YouTube**. Não inventar aprovação, desempenho ou suporte de teste na conta. Se o usuário pediu piloto, encerrar com o pacote concreto para revisão; uma aprovação anterior persiste para a versão e escopo aprovados.

## Passagem para o YouTube

Pedido explícito de upload/agendamento ou configuração A/B: seguir a skill irmã
`../publicar-youtube/SKILL.md`. A aprovação deste pacote não dispara essa etapa.
