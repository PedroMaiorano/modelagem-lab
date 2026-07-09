# Decisão: interface v2 — FastAPI + Next.js (2026-07-09)

> Segunda iteração da interface. A v1 (Streamlit, `docs/planos/interface-streamlit.md`)
> continua no repo — não foi removida, ver "O que fica da v1" abaixo.

## Pedido do usuário

Depois que os 4 módulos de modelagem estavam prontos e testados (ver
`docs/planos/expansao-modulos-2026-07-08.md`), o usuário pediu explicitamente
uma interface "melhor, fluida e responsiva conforme vai rodando" — queria
ver o progresso em tempo real, não só o resultado final — e "bonita"
(achou o Streamlit v1 feio). Perguntado sobre o caminho técnico, escolheu
**FastAPI + React/Next.js** entre as opções apresentadas (as outras eram
NiceGUI/Reflex e "melhorar o Streamlit atual").

## Arquitetura

```
app/backend/          FastAPI — expõe os 4 módulos via API + streaming SSE
├── main.py             endpoints (/api/datasets, /api/dataset/upload,
│                        /api/dataset/preparar, /api/modulo/*, /api/pipeline/run)
├── ingestao.py          detecção de coluna/data + os 3 modos de split
└── logica.py            orquestra construção→categorização→WOE→Pedro_Wise
                          (módulos expostos separados E compostos)

app/frontend/          Next.js 16 (App Router) + TypeScript + Tailwind v4
└── app/
    ├── page.tsx                  página única, orquestra estado
    ├── lib/api.ts                 tipos + cliente HTTP/SSE
    └── components/
        ├── PainelUpload.tsx       upload CSV → detecção → split → preparar
        ├── PainelConfig.tsx       sidebar: dataset, critério, flags (níveis 1-3)
        ├── PainelModulos.tsx      construção / categorização+transformação isolados
        ├── ProgressoAoVivo.tsx    log ao vivo (auto-scroll)
        └── PainelResultado.tsx    métricas, variáveis, barras de IV
```

## Fases 1-4 (2026-07-09, pós-feedback do usuário)

Depois do primeiro teste visual da v2, o usuário pediu (verbatim, resumido):
upload de CSV com perguntas sobre como o backend reconhece tipo de coluna/
resposta/split; sentiu falta do nível 3 e de flags granulares que existiam
na v1; achou o botão do pipeline feio; perguntou se dava pra fazer por
módulos. Aprovou fazer as 4 fases em sequência.

1. **Upload + split** (`ingestao.py`, `/api/dataset/upload`,
   `/api/dataset/preparar`): detecção de tipo por coluna (numérico/data/
   categórico), com heurística de comprimento modal de string pra formato
   de data (evita falso positivo tipo idade~"%Y%m"). Três modos de split:
   coluna de amostra já existente na base, out-of-time por data (com
   sugestão automática de corte), aleatório com semente. Depois de
   "preparado" vira `data/<nome>/{dev,teste}.csv` — mesmo formato que todo
   o resto do backend já consome.
2. **Nível 3 + flags granulares**: `rodar_pipeline` ganhou parâmetros pra
   cada flag de nível 1 (forward/transformação/backward simples,
   min_vars_para_backward) e nível 2 (forward duplo/triplo, transformação/
   backward simples) que existiam na v1 Streamlit mas foram perdidas no
   port; nível 3 (backward complexo recursivo, `run_pedro_wise_completo`)
   nunca tinha sido exposto na v2 antes.
3. **Módulos isolados**: `_construir_e_transformar` foi quebrada em
   `_construir` + `_categorizar_e_transformar`; novos endpoints
   `/api/modulo/construcao` e `/api/modulo/categorizacao-transformacao`
   rodam cada etapa isolada (sem persistir cache — recomputam do zero a
   cada chamada, evita risco de cache desatualizado). `PainelModulos.tsx`
   mostra as 2 etapas como seções expansíveis com resultado (colunas
   construídas / ranking de IV) antes do treinamento.
4. **Polish visual**: botão "Rodar seleção" ganhou gradiente + sombra +
   spinner de loading (era um botão chapado — a reclamação específica do
   usuário). Header ganhou separador e indicador de status do backend.

Testado ponta a ponta contra o backend real em cada fase (curl + scripts
`node` replicando o fluxo exato do frontend) — achou e corrigiu um bug
real: coluna categórica (texto) quebrava `bins_monotonicos` porque a
categorização era aplicada incondicionalmente a toda coluna candidata;
corrigido ramificando por `pd.api.types.is_numeric_dtype` (categóricas
pulam o binning, cada categoria já é o próprio "bin" pro WOE).

## Como o progresso em tempo real funciona (sem tocar o core)

O `pedro_wise` já loga cada atualização aceita via `logger.info(...)` em
todos os módulos (`selection`, `level2`, `level3`, `pipeline`,
`shadow_probing`) — não foi preciso mudar uma linha do core, já testado e
estável. `CapturadorProgresso` (`app/backend/logica.py`) é um
`logging.Handler` anexado ao logger pai `"pedro_wise"` só durante a
execução, que publica cada record numa `queue.Queue`. O endpoint
`/api/pipeline/run` roda o pipeline numa thread separada (é código síncrono/
CPU-bound) e um generator assíncrono lê da fila e emite como
Server-Sent Events (`sse-starlette`).

No frontend, **`EventSource` nativo do navegador não serve** — só faz GET,
e o endpoint precisa de POST (manda a config do usuário). `rodarPipelineComProgresso`
em `app/lib/api.ts` usa `fetch` com `POST` e lê `response.body` como stream,
parseando os frames SSE manualmente.

## Bugs reais encontrados e corrigidos durante a construção (não hipotéticos)

1. **Double-suffix `_woe` em datasets sintéticos**: `experimento_colinearidade`
   e `validacao_r` já nomeiam as colunas cruas com sufixo `_woe` por
   convenção do lab (`docs/algoritmos-originais/pedro-wise-resumo.md`).
   `_construir_e_transformar` (backend) aplicava `f"{coluna}_woe"`
   incondicionalmente, gerando `xa_woe_woe`. Corrigido: só acrescenta o
   sufixo se a coluna ainda não terminar em `_woe`.
2. **Separador de frame SSE errado no parser do frontend**: `sse-starlette`/
   uvicorn terminam cada frame com `\r\n\r\n` (CRLF), não `\n\n` como eu
   assumi inicialmente. Com `\n\n`, o parser nunca encontrava um frame
   completo — a UI teria ficado "presa" sem nunca mostrar progresso ou
   resultado, um bug silencioso e sem erro visível (o `fetch` completa com
   sucesso, só o parsing manual falhava). **Só foi pego porque testei a
   função de parsing de verdade com `node`, simulando exatamente o que o
   navegador faria** — não dava para confiar só no build/lint do TypeScript
   passar (isso não pega erros de lógica de parsing em runtime). Corrigido
   com regex `/\r?\n\r?\n/` (tolera os dois formatos).

Registro deliberado destes dois: são exatamente o tipo de bug que "parece
funcionar" no código lido, só quebra em execução real — reforça o hábito já
estabelecido no lab de testar de ponta a ponta, não confiar em lint/type
check sozinhos.

## Testes feitos (sem navegador disponível neste ambiente)

- Backend isolado: `curl` no `/api/datasets` e no SSE do `/api/pipeline/run`
  (dataset pequeno e o `credito_real` completo, ~49s) — confirma que os
  números batem exatamente com `docs/experimentos/pipeline-completo-credito-real.md`.
- Frontend: `next build` (type-check completo) + `eslint` limpos.
- Integração real: script `node` replicando exatamente a lógica de
  `rodarPipelineComProgresso` contra o backend rodando de verdade — é como
  descobri os dois bugs acima. Não substitui teste visual num navegador
  real, mas verifica que o caminho de dados ponta a ponta funciona.
- **Não verificado**: aparência visual real (não há ferramenta de screenshot
  neste ambiente). O usuário deve rodar localmente e conferir o layout.

## Como rodar

```bash
# Backend (terminal 1)
python -m uvicorn main:app --reload --port 8001 --app-dir app/backend

# Frontend (terminal 2)
cd app/frontend && npm run dev
```

Abre em `http://localhost:3000`. Se o backend não estiver em
`localhost:8001`, copiar `app/frontend/.env.local.example` para `.env.local`
e ajustar `NEXT_PUBLIC_API_URL`.

## O que fica da v1 (Streamlit)

Não removida — `app/streamlit_app.py` e `app/logica.py` continuam
funcionais e testados (`docs/planos/interface-streamlit.md`). Não há
decisão do usuário para descartar; as duas convivem até haver instrução
explícita de remover uma.

## Escopo não coberto (backlog)

- Gráfico de progresso do KS ao longo da busca (a v1 Streamlit tinha via
  `st.line_chart`) — não portado ainda, só o log de texto ao vivo.
- Sem testes automatizados de frontend (Playwright/Vitest) — só as
  verificações manuais/via `node`. Se a interface crescer, vale considerar.
- Tema único escuro, sem alternância clara/escura (decisão deliberada de
  escopo para uma ferramenta interna de um usuário só).
- Módulos isolados (Fase 3) não persistem estado entre si — rodar
  "categorização+transformação" recomputa a construção internamente se
  `usar_construcao=true`, não reaproveita o resultado já mostrado da etapa
  1. Simplicidade deliberada (evita cache desatualizado); se o dataset
  crescer muito, considerar persistir intermediários em disco.
- Sem verificação visual num navegador real neste ambiente (sem ferramenta
  de screenshot) — todas as fases testadas via `curl`/`node`/build/lint,
  não com olhos humanos. Próximo passo se o usuário reportar algo quebrado
  visualmente.
