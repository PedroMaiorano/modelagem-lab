# Literatura — Wiki de Técnicas de Modelagem

Acervo de técnicas de modelagem documentadas a partir de literatura **aberta**, populado
pelo agente `literature-scout` (skill `buscar-literatura`).

## Convenção
- Um arquivo por tópico: `docs/literatura/{topico}.md` (ex.: `stability-selection.md`).
- Cada arquivo: síntese curada (3-5 frases por paper: contribuição, método, relevância),
  não abstract cru.
- Linkar de volta ao `sota-tracker-modelagem.md` quando o achado muda o estado da arte.
- Registrar cada tópico novo no `docs/INDEX.md`.

## Estrutura sugerida de uma ficha de técnica
```
# {Técnica}
## O que é / quando usar
## Pressupostos e trade-offs (clássico vs. SOTA)
## Papers-chave (título, autores, ano, fonte aberta, link/DOI + síntese)
## Conexão com o acervo (Pedro_Wise / seleção de variáveis / outro)
```

## Organização por módulo

O lab tem 4 módulos de modelagem (ver `docs/guias/fluxo-de-trabalho.md`):
categorização, transformação, construção, treinamento. A literatura segue
essa mesma divisão — ao adicionar um tópico novo, identifique de qual
módulo ele é antes de criar o arquivo.

## Tópicos cobertos
- **Categorização**: [categorizacao](categorizacao.md) — 2026-07-08 (13 refs).
- **Transformação**: [transformacao](transformacao.md) — 2026-07-08 (11 refs).
- **Construção**: [construcao-variaveis](construcao-variaveis.md) — 2026-07-08 (12 refs).
- **Treinamento**: [stability-selection](stability-selection.md) — 2026-07-07 (5 refs); [shadow-variable-probing](shadow-variable-probing.md) — 2026-07-07 (3 refs).
