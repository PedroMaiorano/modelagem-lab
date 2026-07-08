---
name: buscar-literatura
description: Use quando o usuário quiser buscar literatura acadêmica recente sobre uma técnica de modelagem estatística/ML. Dispara em "tem papers recentes sobre stability selection?", "busca literatura de causal ML", "o que há de novo em AutoML tabular?". Só fontes abertas.
---

# Skill: buscar-literatura

Buscar e sintetizar literatura em fontes 100% abertas, alimentando a wiki `docs/literatura/`. Aciona o agente `literature-scout`.

## Quando usar
- Pedido de papers/literatura recente sobre um tópico de modelagem.
- Popular/atualizar a wiki de técnicas.

## Quando NÃO usar
- Técnica já documentada em `docs/literatura/` (leia o arquivo).
- Escolher qual técnica usar num problema (use `stats-advisor`).

## Fontes e comandos concretos (todas abertas)
Ver `docs/referencias/apis-fontes-abertas.md` para detalhes. Atalhos:

- **arXiv** (XML, sem chave): `http://export.arxiv.org/api/query?search_query=cat:stat.ML+AND+all:"variable selection"&sortBy=submittedDate&sortOrder=descending&max_results=15`
- **Semantic Scholar** (JSON, 100 req/5min): `https://api.semanticscholar.org/graph/v1/paper/search?query=stability+selection&fields=title,abstract,year,authors,tldr,openAccessPdf&limit=15`
- **OpenAlex** (JSON, polite pool): `https://api.openalex.org/works?search=double+machine+learning&filter=is_oa:true&mailto=pedro.maiorano@gmail.com&per-page=15`
- **CrossRef** (JSON): `https://api.crossref.org/works?query=elastic+net+selection&filter=has-abstract:true&mailto=pedro.maiorano@gmail.com&rows=15`
- **Europe PMC** (JSON, sempre `OPEN_ACCESS:Y`): `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=OPEN_ACCESS:Y%20AND%20"variable%20selection"&format=json`

## Processo

### 1. Delimite o tópico
Específico o suficiente para busca útil (ex.: "shadow-variable probing", não "estatística").
**Gate**: o tópico gera uma query focada?

### 2. Cheque o cache
`data/papers/` — não re-baixe metadados já salvos.

### 3. Delegue ao literature-scout
Passe o tópico + lembrete de que só fontes abertas valem e `mailto` deve ir nos queries OpenAlex/CrossRef.

### 4. Revise
Confirme gravação em `docs/literatura/{topico}.md`, link no `docs/INDEX.md`, e se algum achado atualiza o `sota-tracker-modelagem.md`.

## Formato de Saída
- Papers com síntese curta (3-5 frases) — herdado do `literature-scout`.
- Caminho do arquivo gravado.
- Aviso se algo relevante ficou de fora por paywall.

## Armadilhas Comuns
- Tópico genérico demais → ruído.
- Esquecer `mailto` no OpenAlex/CrossRef → sai do polite pool (mais lento/instável).
- Não linkar o achado ao SOTA tracker quando ele muda o estado da arte.
