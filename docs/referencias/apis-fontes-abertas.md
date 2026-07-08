# APIs de Literatura Acadêmica — Fontes 100% Abertas

> Referência operacional do **pilar 2** (scraping). Só fontes abertas — **nunca** paywall,
> Sci-Hub ou cache pirata. Verificado em 2026-07-07.
>
> **Regra do polite pool**: em OpenAlex e CrossRef, inclua sempre `mailto=pedro.maiorano@gmail.com`
> no query — dá respostas mais rápidas e estáveis. Cheque `data/papers/` (cache imutável)
> antes de qualquer request.

---

## arXiv API
- **Endpoint**: `http://export.arxiv.org/api/query`
- **Chave**: não. **Formato**: **XML (Atom)** — única das listadas que não é JSON.
- **Rate limit**: gentil; ~1 request a cada 3s, `max_results` moderado por chamada.
- **Categorias relevantes**: `stat.ME` (metodologia), `stat.ML` (aprendizado), `stat.CO`
  (computacional), `stat.AP` (aplicada), `cs.LG`, `econ.EM`.
- **Exemplo**:
  ```
  http://export.arxiv.org/api/query?search_query=cat:stat.ML+AND+all:"variable selection"&sortBy=submittedDate&sortOrder=descending&max_results=15
  ```
- **Uso**: descoberta de preprints recentes de metodologia/ML. Melhor fonte para "o que há de novo".

## Semantic Scholar Graph API
- **Endpoint**: `https://api.semanticscholar.org/graph/v1`
- **Chave**: não por padrão (**100 requests / 5 min**). Chave gratuita p/ limites maiores via formulário.
- **Formato**: JSON. Recursos: TLDR (resumo gerado), citações, `openAccessPdf`.
- **Exemplo**:
  ```
  https://api.semanticscholar.org/graph/v1/paper/search?query=stability+selection&fields=title,abstract,year,authors,tldr,openAccessPdf&limit=15
  ```
- **Uso**: busca por texto com resumo pronto; ótimo para triagem rápida.

## OpenAlex
- **Endpoint**: `https://api.openalex.org/works`
- **Chave**: não. **Limite**: sem limite rígido (sugerido ≤100k/dia). `mailto=` → polite pool.
- **Formato**: JSON. 250M+ works; substituto aberto do Microsoft Academic Graph.
- **Exemplo** (só open access):
  ```
  https://api.openalex.org/works?search=double+machine+learning&filter=is_oa:true&mailto=pedro.maiorano@gmail.com&per-page=15
  ```
- **Uso**: cobertura ampla, métricas de citação, filtros ricos (`is_oa`, ano, conceito).

## CrossRef
- **Endpoint**: `https://api.crossref.org/works`
- **Chave**: não. Sem limite especificado; `mailto=` → polite pool.
- **Formato**: JSON. Metadados por DOI, licença, links de texto.
- **Exemplo**:
  ```
  https://api.crossref.org/works?query=elastic+net+selection&filter=has-abstract:true&mailto=pedro.maiorano@gmail.com&rows=15
  ```
- **Uso**: resolver DOI → metadados; complementa OpenAlex.

## Europe PMC / PubMed E-utilities
- **Europe PMC REST**: `https://www.ebi.ac.uk/europepmc/webservices/rest/search` — **sempre**
  filtrar `OPEN_ACCESS:Y`. JSON.
  ```
  https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=OPEN_ACCESS:Y%20AND%20"variable%20selection"&format=json
  ```
- **PubMed E-utilities**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` (`esearch.fcgi` →
  `efetch.fcgi`). Sem chave: **3 req/s**; com chave gratuita: 10 req/s.
- **Uso**: biomédico e aplicações de risco em saúde/atuária. Só o que for open access.

---

## Boas práticas de scraping (todos os clients em `scraping/`)
1. **Cache primeiro**: nome de arquivo determinístico por `fonte+id` em `data/papers/`; nunca re-baixar.
2. **`mailto` sempre** em OpenAlex/CrossRef.
3. **Respeitar rate limit** com backoff (arXiv 3s; S2 100/5min; PubMed 3/s).
4. **User-Agent identificável** com contato.
5. **Guardar só metadados/abstracts abertos** — não baixar PDF de fonte fechada.
6. **Nunca** adicionar fonte fora desta lista sem revisão explícita com o usuário.
