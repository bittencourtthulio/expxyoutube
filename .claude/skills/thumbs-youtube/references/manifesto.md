# Manifesto do pacote

Salvar `thumbs.json` junto aos JPGs. Caminhos relativos são resolvidos a partir desse manifesto.
Preencha o manifesto com dados e referências do seu próprio projeto.

Campos:

- `version`: 1.
- `expected_variants`: 3 por padrão; outra quantidade somente quando pedida explicitamente,
  registrando `count_reason`.
- `tool`: nome oficial da ferramenta (string; obrigatório neste fluxo de séries sobre ferramentas).
- `brand`: objeto com `source` (URL oficial), `colors` (lista de hex), `logo` (arquivo local ou null)
  e `logo_note` (origem/atribuição; se não localizado, registrar a busca e não inventar símbolo).
- `identity`: objeto com `method` e `reference` (origem real da identidade; caminho local ou URL),
  `soul_id` quando aplicável. Sem pessoa, explicar em `method` e usar `reference: null`.
- `variants`: lista de objetos `id`, `title`, `headline` (todo texto visível, incluindo nome),
  `concept` (hipótese distinta), `evidence` (trecho/fonte que sustenta promessa), `file` (JPG/PNG).
- Cada variante contém `review`: `fingerprint`, `reviewer`, `notes` e booleanos
  `face`, `text`, `brand`, `composition`, `feed`. Só marcar true após conferir; sem rosto,
  registrar essa condição em notes e marcar face como conferido/não aplicável.
- `user_approval`: opcional, objeto com data, mensagem e escopo exatos; nunca preenchido por inferência.
  Não é uma permissão de publicação e não participa do resultado técnico.

No diretório da skill (ou com caminho absoluto equivalente):

```sh
python3 scripts/validar.py fingerprints /caminho/do/pacote/thumbs.json
python3 scripts/validar.py validar /caminho/do/pacote/thumbs.json
```

O primeiro comando apenas calcula as assinaturas. Abrir e revisar as imagens ANTES de registrar
essas assinaturas em review. O segundo retorna 0 se não houver pendências e 1 se houver falhas.
Nenhum comando grava revisão, publica, usa rede ou acessa autenticação. A assinatura cobre bytes
da imagem, título, texto, conceito, evidência e dados de marca/identidade. Alterações exigem revisão nova.
Validação de cabeçalho de imagem não substitui abrir o arquivo final para confirmar decodificação.
