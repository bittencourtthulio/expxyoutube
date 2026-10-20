# Studio: três pares de título e miniatura

Usar a skill computer-use e seu guia da versão atual antes de controlar navegador. API para metadados;
interface somente onde necessária. Abrir uma aba nova no Studio pelo ID conhecido, preservar outras abas.
Conferir vídeo/canal antes de editar. Não imprimir a árvore completa de abas: uma aba OAuth antiga pode
conter código de autorização na URL. Filtrar a saída para controles do trabalho; não salvar esses códigos.

1. Detalhes → Teste A/B → **Título e miniatura**. Primeira combinação vem do título/thumbnail padrão.
2. Carregar imagens 02 e 03 **antes de editar os títulos**: nesta sessão, o rerender do upload descartou
   valores que estavam apenas visíveis no controle e não tinham sido incorporados ao formulário.
3. Seletor nativo macOS: Cmd+Shift+G, caminho absoluto do JPG final, Return, confirmar seleção e Abrir.
   Não usar o `*-base.png` nem a prévia conjunta. Não reutilizar índices depois do diálogo ou upload.
4. Preencher títulos 02/03 com o texto exato. Ler estado novo após cada ação. Verificar também título 01.
   Não supor que sucesso de set-value significa estado interno do formulário atualizado.
5. Se texto estiver visível mas o botão continuar desabilitado, ler a mensagem de validação. Conferir
   thumbnails carregadas, foco real e campos obrigatórios antes de culpar privacidade/recurso indisponível.
   Nesta execução, clique semântico às vezes não mudou foco; clique pelas coordenadas da screenshot atual
   resolveu o foco. Respeitar a escala da imagem. Nunca copiar coordenadas/índices desta sessão.
6. Usar seleção/substituição com foco confirmado e uma única estratégia de entrada. Se surgir placeholder
   literal (“Adicione o título 3”) ou título duplicado, corrigir e ler de novo. Não acumular set-value,
   paste-text e type-text sem verificar: isso produziu duplicações aqui. Uma edição real de teclado após
   set-value fez o formulário reconhecer o texto; ao usar espaço temporário, removê-lo e conferir o texto
   final normalizado antes de salvar. Não tratar esse recurso como garantia universal.
7. Após ação assíncrona, esperar brevemente (~1 s quando necessário) e obter estado novo; sucesso de chamada
   não é sucesso da ação. Se dois métodos não produzem progresso verificável, diagnosticar uma vez (foco,
   captura, mensagem do Studio) e informar impedimento concreto, em vez de repetir dezenas de chamadas.
8. Conferir visualmente as três imagens e os títulos. Concluir/Começar teste no diálogo. Na página principal,
   **Salvar**, aguardar confirmação e **recarregar**. Só então registrar “configuração salva”.
9. Conferir novamente o agendamento via API após salvar o Studio. Não alterar publicação para permitir teste.
   Se o Studio disser “não é público”, registrar `saved_waiting_public`; não declarar `running`.

AppleScript JS estava desativado neste Chrome; não insistir nem mudar configuração global para contornar isso.
Não depender de endpoints internos do Studio, cookies extraídos ou sessão CDP improvisada.

Estados usados no registro A/B:
- `not_configured`: nenhum envio confirmado.
- `configured_unsaved`: diálogo concluído, ainda falta Salvar na página.
- `saved_waiting_public`: persistiu após reload, impedido pela privacidade.
- `running`: interface explicitamente confirma execução.
- `blocked`: impedimento observado, com mensagem e etapa.

Guardar mensagem, horário e lista dos três pares/arquivos verificados. Não inventar ID de experimento.
Fonte oficial (rever se interface/regras mudarem): https://support.google.com/youtube/answer/16391400
