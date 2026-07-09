"use client";

import type { EventoResultado, FaixaDecil } from "../lib/api";

function Metrica({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/70 px-4 py-3">
      <div className="text-[11px] uppercase tracking-wider text-slate-500">{rotulo}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-100 tabular-nums">{valor}</div>
    </div>
  );
}

/** Barras de IV: uma única cor (magnitude, não categoria) — sem legenda
 * necessária para série única, ver referências/palette.md da skill dataviz. */
function BarraIV({ variavel, iv, maximo }: { variavel: string; iv: number; maximo: number }) {
  const largura = maximo > 0 ? Math.max(4, (iv / maximo) * 100) : 0;
  return (
    <div className="flex items-center gap-3 text-xs">
      <div className="w-32 shrink-0 truncate text-slate-400" title={variavel}>
        {variavel}
      </div>
      <div className="h-3.5 flex-1 overflow-hidden rounded-full bg-slate-800/50">
        <div className="h-full rounded-full bg-emerald-600" style={{ width: `${largura}%` }} />
      </div>
      <div className="w-14 shrink-0 text-right tabular-nums text-slate-400">{iv.toFixed(3)}</div>
    </div>
  );
}

const LARGURA = 560;
const ALTURA = 220;
const MARGEM = { topo: 12, base: 34, esquerda: 36, direita: 12 };

/** Curva KS: % acumulado de eventos vs. não-eventos por faixa de score,
 * com a maior distância entre as duas curvas marcada (é o próprio KS). Mais
 * informativo que só o número agregado — mostra ONDE o modelo separa bem. */
function GraficoKS({ tabela }: { tabela: FaixaDecil[] }) {
  const larguraUtil = LARGURA - MARGEM.esquerda - MARGEM.direita;
  const alturaUtil = ALTURA - MARGEM.topo - MARGEM.base;
  const n = tabela.length;
  const x = (i: number) => MARGEM.esquerda + (i / (n - 1)) * larguraUtil;
  const y = (pct: number) => MARGEM.topo + (1 - pct) * alturaUtil;

  const pontosEventos = tabela.map((f, i) => `${x(i)},${y(f.pct_eventos_capturados)}`).join(" ");
  const pontosNaoEventos = tabela.map((f, i) => `${x(i)},${y(f.pct_nao_eventos_capturados)}`).join(" ");

  const indiceMaxKS = tabela.reduce(
    (melhor, f, i) => (f.ks_acumulado > tabela[melhor].ks_acumulado ? i : melhor),
    0,
  );
  const faixaMaxKS = tabela[indiceMaxKS];

  return (
    <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} className="w-full" role="img" aria-label="Curva KS acumulada">
      {[0, 0.25, 0.5, 0.75, 1].map((frac) => (
        <g key={frac}>
          <line
            x1={MARGEM.esquerda}
            x2={LARGURA - MARGEM.direita}
            y1={y(frac)}
            y2={y(frac)}
            stroke="rgb(30 41 59 / 0.6)"
            strokeWidth={1}
          />
          <text x={MARGEM.esquerda - 6} y={y(frac) + 3} textAnchor="end" className="fill-slate-500" fontSize={10}>
            {Math.round(frac * 100)}%
          </text>
        </g>
      ))}
      <line
        x1={x(indiceMaxKS)}
        x2={x(indiceMaxKS)}
        y1={y(faixaMaxKS.pct_eventos_capturados)}
        y2={y(faixaMaxKS.pct_nao_eventos_capturados)}
        stroke="rgb(244 63 94)"
        strokeWidth={2}
        strokeDasharray="3 2"
      />
      <polyline points={pontosEventos} fill="none" stroke="rgb(16 185 129)" strokeWidth={2} />
      <polyline points={pontosNaoEventos} fill="none" stroke="rgb(100 116 139)" strokeWidth={2} />
      {tabela.map((f, i) => (
        <text
          key={f.faixa}
          x={x(i)}
          y={ALTURA - MARGEM.base + 16}
          textAnchor="middle"
          className="fill-slate-500"
          fontSize={10}
        >
          {f.faixa}
        </text>
      ))}
      <text
        x={(MARGEM.esquerda + LARGURA - MARGEM.direita) / 2}
        y={ALTURA - 6}
        textAnchor="middle"
        className="fill-slate-600"
        fontSize={10}
      >
        faixa de score (decil, 1 = maior risco)
      </text>
      <text
        x={x(indiceMaxKS) + 4}
        y={(y(faixaMaxKS.pct_eventos_capturados) + y(faixaMaxKS.pct_nao_eventos_capturados)) / 2}
        className="fill-rose-400"
        fontSize={10}
      >
        KS {faixaMaxKS.ks_acumulado.toFixed(3)}
      </text>
    </svg>
  );
}

/** Taxa de evento por decil de score — as faixas dividem o teste em ~10
 * grupos de tamanho igual (não 10% fixo se `n` não for múltiplo de 10; a
 * última faixa absorve o resto), ordenados do maior score (mais risco)
 * pro menor. `n` e a taxa exata aparecem no tooltip nativo (passe o mouse). */
function GraficoTaxaEvento({ tabela }: { tabela: FaixaDecil[] }) {
  const larguraUtil = LARGURA - MARGEM.esquerda - MARGEM.direita;
  const alturaUtil = ALTURA - MARGEM.topo - MARGEM.base;
  const maximo = Math.max(...tabela.map((f) => f.taxa_evento), 0.01);
  const larguraBarra = (larguraUtil / tabela.length) * 0.7;
  const y = (taxa: number) => MARGEM.topo + (1 - taxa / maximo) * alturaUtil;

  return (
    <svg
      viewBox={`0 0 ${LARGURA} ${ALTURA}`}
      className="w-full"
      role="img"
      aria-label="Taxa de evento por faixa de score"
    >
      {[0, 0.5, 1].map((frac) => (
        <g key={frac}>
          <line
            x1={MARGEM.esquerda}
            x2={LARGURA - MARGEM.direita}
            y1={y(frac * maximo)}
            y2={y(frac * maximo)}
            stroke="rgb(30 41 59 / 0.6)"
            strokeWidth={1}
          />
          <text
            x={MARGEM.esquerda - 6}
            y={y(frac * maximo) + 3}
            textAnchor="end"
            className="fill-slate-500"
            fontSize={10}
          >
            {(frac * maximo * 100).toFixed(0)}%
          </text>
        </g>
      ))}
      {tabela.map((f, i) => {
        const alturaBarra = (f.taxa_evento / maximo) * alturaUtil;
        const xCentro = MARGEM.esquerda + ((i + 0.5) / tabela.length) * larguraUtil;
        return (
          <g key={f.faixa}>
            <rect
              x={xCentro - larguraBarra / 2}
              y={MARGEM.topo + alturaUtil - alturaBarra}
              width={larguraBarra}
              height={Math.max(1, alturaBarra)}
              rx={3}
              className="fill-sky-600"
            >
              <title>
                faixa {f.faixa} · n={f.n} · taxa de evento={(f.taxa_evento * 100).toFixed(1)}%
              </title>
            </rect>
            <text
              x={xCentro}
              y={MARGEM.topo + alturaUtil - alturaBarra - 4}
              textAnchor="middle"
              className="fill-slate-400"
              fontSize={9}
            >
              {(f.taxa_evento * 100).toFixed(0)}%
            </text>
            <text
              x={xCentro}
              y={ALTURA - MARGEM.base + 16}
              textAnchor="middle"
              className="fill-slate-500"
              fontSize={10}
            >
              {f.faixa}
            </text>
          </g>
        );
      })}
      <text
        x={(MARGEM.esquerda + LARGURA - MARGEM.direita) / 2}
        y={ALTURA - 6}
        textAnchor="middle"
        className="fill-slate-600"
        fontSize={10}
      >
        faixa de score (decil, ~{tabela[0]?.n ?? 0} casos cada, 1 = maior risco)
      </text>
    </svg>
  );
}

function formatarPValor(p: number): string {
  return p < 0.0001 ? "<0.0001" : p.toFixed(4);
}

/** `*` = p<0.05, `**` = p<0.01, `***` = p<0.001 — convenção padrão de
 * relatórios de regressão, útil pra escanear rapidamente quais coeficientes
 * são estatisticamente significativos SEM ler cada p-valor numérico. */
function marcadorSignificancia(p: number): string {
  if (p < 0.001) return "***";
  if (p < 0.01) return "**";
  if (p < 0.05) return "*";
  return "";
}

/** Comparação com/sem o filtro de p-valor — só aparece quando o filtro
 * estava ativo neste run. O backend roda a busca DE NOVO sem a restrição
 * só pra isso, pedido explícito do usuário ("guardar uma cópia sem o
 * p-valor") pra ver o que a restrição custou em KS. */
function ComparacaoSignificancia({ resultado }: { resultado: EventoResultado }) {
  const semFiltro = resultado.resultado_sem_filtro_pvalor;
  if (!semFiltro) return null;

  const variaveisRemovidas = semFiltro.variaveis.filter((v) => !resultado.variaveis.includes(v));
  const deltaKS = resultado.ks_teste - semFiltro.ks_teste;

  return (
    <div className="rounded-xl border border-amber-800/60 bg-amber-950/20 p-4">
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-amber-400">
        Comparação: com vs. sem restrição de p-valor
      </h3>
      <p className="mb-3 text-[11px] text-slate-500">
        Modelo ao lado é o oficial (com a restrição). Este é só uma referência de quanto KS a restrição
        custou — rodado sem o filtro, tudo mais igual.
      </p>
      <div className="grid grid-cols-2 gap-4 text-xs sm:grid-cols-4">
        <div>
          <div className="text-slate-500">KS teste (com filtro)</div>
          <div className="mt-0.5 text-base font-semibold tabular-nums text-slate-100">
            {resultado.ks_teste.toFixed(4)}
          </div>
        </div>
        <div>
          <div className="text-slate-500">KS teste (sem filtro)</div>
          <div className="mt-0.5 text-base font-semibold tabular-nums text-slate-100">
            {semFiltro.ks_teste.toFixed(4)}
          </div>
        </div>
        <div>
          <div className="text-slate-500">diferença</div>
          <div
            className={`mt-0.5 text-base font-semibold tabular-nums ${deltaKS < 0 ? "text-rose-400" : "text-emerald-400"}`}
          >
            {deltaKS >= 0 ? "+" : ""}
            {deltaKS.toFixed(4)}
          </div>
        </div>
        <div>
          <div className="text-slate-500">variáveis (sem filtro)</div>
          <div className="mt-0.5 text-base font-semibold tabular-nums text-slate-100">
            {semFiltro.variaveis.length}
          </div>
        </div>
      </div>
      {variaveisRemovidas.length > 0 && (
        <div className="mt-3">
          <p className="mb-1.5 text-[11px] text-slate-500">
            Entrariam sem a restrição, mas foram bloqueadas por p-valor:
          </p>
          <div className="flex flex-wrap gap-1.5">
            {variaveisRemovidas.map((v) => (
              <span
                key={v}
                className="rounded-full border border-amber-800 bg-amber-950/40 px-2.5 py-1 text-xs text-amber-300"
              >
                {v}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Formula({ resultado }: { resultado: EventoResultado }) {
  const termos = resultado.coeficientes
    .slice()
    .sort((a, b) => Math.abs(b.coeficiente) - Math.abs(a.coeficiente));

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
        Fórmula do modelo (logit)
      </h3>
      <p className="mb-3 text-[11px] text-slate-600">
        log-odds do evento = intercepto + soma dos coeficientes × variável. O Pedro_Wise seleciona
        variáveis só pelo KS — p-valor/erro padrão aqui são diagnóstico pós-hoc, não influenciam a
        seleção (ver pergunta sobre isso na conversa).
      </p>
      <p className="mb-4 overflow-x-auto whitespace-nowrap font-mono text-xs text-slate-300">
        logit(p) = {resultado.intercepto.toFixed(4)}
        {termos.map((t) => (
          <span key={t.variavel}>
            {" "}
            {t.coeficiente >= 0 ? "+" : "−"} {Math.abs(t.coeficiente).toFixed(4)}·{t.variavel}
          </span>
        ))}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-700 text-slate-500">
              <th className="py-1.5 pr-4 font-medium">variável</th>
              <th className="py-1.5 pr-4 text-right font-medium">coeficiente</th>
              <th className="py-1.5 pr-4 text-right font-medium">erro padrão</th>
              <th className="py-1.5 pr-4 text-right font-medium">p-valor</th>
              <th className="py-1.5 text-left font-medium">sig.</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-slate-800 text-slate-300">
              <td className="py-1.5 pr-4">intercepto</td>
              <td className="py-1.5 pr-4 text-right tabular-nums">{resultado.intercepto.toFixed(4)}</td>
              <td className="py-1.5 pr-4 text-right tabular-nums">
                {resultado.intercepto_erro_padrao.toFixed(4)}
              </td>
              <td className="py-1.5 pr-4 text-right tabular-nums">
                {formatarPValor(resultado.intercepto_p_valor)}
              </td>
              <td className="py-1.5 text-amber-400">{marcadorSignificancia(resultado.intercepto_p_valor)}</td>
            </tr>
            {termos.map((t) => (
              <tr key={t.variavel} className="border-b border-slate-800/60 text-slate-300 last:border-0">
                <td className="py-1.5 pr-4 truncate" title={t.variavel}>
                  {t.variavel}
                </td>
                <td className="py-1.5 pr-4 text-right tabular-nums">{t.coeficiente.toFixed(4)}</td>
                <td className="py-1.5 pr-4 text-right tabular-nums">{t.erro_padrao.toFixed(4)}</td>
                <td className="py-1.5 pr-4 text-right tabular-nums">{formatarPValor(t.p_valor)}</td>
                <td className="py-1.5 text-amber-400">{marcadorSignificancia(t.p_valor)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-[11px] text-slate-600">* p&lt;0.05 · ** p&lt;0.01 · *** p&lt;0.001</p>
    </div>
  );
}

export default function PainelResultado({ resultado }: { resultado: EventoResultado }) {
  const maximoIV = Math.max(0, ...resultado.top_iv.map((i) => i.iv));

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
        <Metrica rotulo="KS (teste)" valor={resultado.ks_teste.toFixed(4)} />
        <Metrica rotulo="KS (treino)" valor={resultado.ks_dev.toFixed(4)} />
        <Metrica rotulo="GINI" valor={resultado.gini.toFixed(3)} />
        <Metrica rotulo="AUC" valor={resultado.auc.toFixed(3)} />
        <Metrica rotulo="Taxa de mau (teste)" valor={`${(resultado.taxa_evento_teste * 100).toFixed(1)}%`} />
        <Metrica rotulo="Variáveis" valor={String(resultado.variaveis.length)} />
        <Metrica rotulo="Tempo" valor={`${resultado.tempo_segundos}s`} />
      </div>

      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Variáveis selecionadas
        </h3>
        <div className="flex flex-wrap gap-1.5">
          {resultado.variaveis.map((v) => (
            <span
              key={v}
              className="rounded-full border border-emerald-800 bg-emerald-950/50 px-2.5 py-1 text-xs text-emerald-300"
            >
              {v}
            </span>
          ))}
        </div>
      </div>

      <ComparacaoSignificancia resultado={resultado} />

      {resultado.coeficientes.length > 0 && <Formula resultado={resultado} />}

      {resultado.tabela_decis.length > 1 && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
              Curva KS (teste)
            </h3>
            <p className="mb-2 text-[11px] text-slate-600">
              % acumulado de <span className="text-emerald-400">eventos</span> vs.{" "}
              <span className="text-slate-400">não-eventos</span> por faixa de score, base de teste.
            </p>
            <GraficoKS tabela={resultado.tabela_decis} />
          </div>
          <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
              Taxa de evento por faixa (teste)
            </h3>
            <p className="mb-2 text-[11px] text-slate-600">
              Decis de score, base de teste — passe o mouse numa barra pra ver n e taxa exata.
            </p>
            <GraficoTaxaEvento tabela={resultado.tabela_decis} />
          </div>
        </div>
      )}

      {resultado.top_iv.length > 0 && (
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Top Information Value
          </h3>
          <div className="flex flex-col gap-2 rounded-xl border border-slate-700 bg-slate-900/70 p-4">
            {resultado.top_iv.map((item) => (
              <BarraIV key={item.variavel} variavel={item.variavel} iv={item.iv} maximo={maximoIV} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
