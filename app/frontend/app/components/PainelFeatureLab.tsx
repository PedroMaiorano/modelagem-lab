"use client";

import { useEffect, useState } from "react";
import {
  buscarInfoPainel,
  listarPaineis,
  rodarFeatureLab,
  type InfoPainel,
  type ResultadoFeatureLab,
} from "../lib/api";

function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-5">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">{titulo}</h2>
      {children}
    </div>
  );
}

function Metrica({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{rotulo}</div>
      <div className="mt-0.5 text-lg font-semibold text-slate-100 tabular-nums">{valor}</div>
    </div>
  );
}

export default function PainelFeatureLab() {
  const [paineis, setPaineis] = useState<string[]>([]);
  const [painel, setPainel] = useState("");
  const [info, setInfo] = useState<InfoPainel | null>(null);
  const [chave, setChave] = useState("");
  const [colunaTempo, setColunaTempo] = useState("");
  const [colunasValor, setColunasValor] = useState<Set<string>>(new Set());
  const [janelasTexto, setJanelasTexto] = useState("3");

  const [profundidadeMaxima, setProfundidadeMaxima] = useState(2);
  const [nArvores, setNArvores] = useState(60);
  const [minSuporte, setMinSuporte] = useState(0.02);
  const [maxSuporte, setMaxSuporte] = useState(0.5);
  const [maxRegras, setMaxRegras] = useState(10);
  const [permitirCruzamento, setPermitirCruzamento] = useState(true);

  const [rodando, setRodando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<ResultadoFeatureLab | null>(null);

  useEffect(() => {
    listarPaineis()
      .then((lista) => {
        setPaineis(lista);
        if (lista.length > 0) setPainel(lista[0]);
      })
      .catch((e) => setErro(String(e)));
  }, []);

  useEffect(() => {
    if (!painel) return;
    buscarInfoPainel(painel)
      .then((i) => {
        setInfo(i);
        setChave(i.chave_sugerida);
        setColunaTempo(i.tempo_sugerido);
        setColunasValor(new Set(i.colunas_valor_disponiveis));
        setResultado(null);
      })
      .catch((e) => setErro(String(e)));
  }, [painel]);

  function alternarColunaValor(coluna: string) {
    setColunasValor((atual) => {
      const novo = new Set(atual);
      if (novo.has(coluna)) novo.delete(coluna);
      else novo.add(coluna);
      return novo;
    });
  }

  async function aoRodar() {
    const janelas = janelasTexto
      .split(",")
      .map((s) => Number(s.trim()))
      .filter((n) => Number.isFinite(n) && n > 0);

    if (colunasValor.size === 0) {
      setErro("Selecione ao menos uma coluna de valor.");
      return;
    }
    if (janelas.length === 0) {
      setErro("Informe ao menos uma janela válida (ex.: 3,6).");
      return;
    }

    setRodando(true);
    setErro(null);
    setResultado(null);
    try {
      const r = await rodarFeatureLab({
        painel,
        chave,
        coluna_tempo: colunaTempo,
        colunas_valor: [...colunasValor],
        janelas,
        profundidade_maxima: profundidadeMaxima,
        n_arvores: nArvores,
        min_suporte: minSuporte,
        max_suporte: maxSuporte,
        max_regras: maxRegras,
        permitir_cruzamento_entre_bases: permitirCruzamento,
      });
      setResultado(r);
    } catch (e) {
      setErro(String(e));
    } finally {
      setRodando(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-lg border border-amber-800/50 bg-amber-950/30 px-4 py-3 text-xs text-amber-200">
        Experimental — agregação temporal (esfera 1) e descoberta de interação via árvores rasas
        (esfera 2), rodando sobre um dataset sintético por enquanto. Cada clique em &ldquo;Rodar&rdquo;
        recalcula tudo do zero a partir dos parâmetros abaixo, sem estado entre chamadas.
      </div>

      <Secao titulo="Painel">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">dataset de painel</label>
            <select
              value={painel}
              onChange={(e) => setPainel(e.target.value)}
              className="rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
            >
              {paineis.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          {info && (
            <>
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">chave</label>
                <select
                  value={chave}
                  onChange={(e) => setChave(e.target.value)}
                  className="rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
                >
                  {info.colunas.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">coluna de tempo/safra</label>
                <select
                  value={colunaTempo}
                  onChange={(e) => setColunaTempo(e.target.value)}
                  className="rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
                >
                  {info.colunas.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
              <p className="text-xs text-slate-500">
                {info.n_linhas.toLocaleString("pt-BR")} linhas, {info.n_chaves.toLocaleString("pt-BR")} chaves
              </p>
            </>
          )}
        </div>
      </Secao>

      {info && (
        <Secao titulo="Esfera 1 — agregação temporal">
          <div className="flex flex-col gap-3">
            <div>
              <p className="mb-1.5 text-[11px] text-slate-500">
                colunas brutas a agregar (máximo/média/mínimo/desvio/tendência por janela)
              </p>
              <div className="flex flex-wrap gap-2">
                {info.colunas_valor_disponiveis.map((c) => (
                  <label
                    key={c}
                    className="flex cursor-pointer items-center gap-1.5 rounded-full border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-xs text-slate-300"
                  >
                    <input
                      type="checkbox"
                      checked={colunasValor.has(c)}
                      onChange={() => alternarColunaValor(c)}
                      className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
                    />
                    {c}
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">janelas (meses, separadas por vírgula)</label>
              <input
                type="text"
                value={janelasTexto}
                onChange={(e) => setJanelasTexto(e.target.value)}
                placeholder="3,6,12"
                className="w-32 rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
              />
            </div>
          </div>
        </Secao>
      )}

      <Secao titulo="Esfera 2 — descoberta de interação">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">profundidade máxima</label>
            <input
              type="number"
              min={2}
              max={6}
              value={profundidadeMaxima}
              onChange={(e) => setProfundidadeMaxima(Number(e.target.value))}
              className="w-full rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">nº árvores</label>
            <input
              type="number"
              min={10}
              max={300}
              value={nArvores}
              onChange={(e) => setNArvores(Number(e.target.value))}
              className="w-full rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">suporte mínimo</label>
            <input
              type="number"
              step={0.01}
              min={0}
              max={1}
              value={minSuporte}
              onChange={(e) => setMinSuporte(Number(e.target.value))}
              className="w-full rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">suporte máximo</label>
            <input
              type="number"
              step={0.01}
              min={0}
              max={1}
              value={maxSuporte}
              onChange={(e) => setMaxSuporte(Number(e.target.value))}
              className="w-full rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">máx. regras exibidas</label>
            <input
              type="number"
              min={1}
              max={50}
              value={maxRegras}
              onChange={(e) => setMaxRegras(Number(e.target.value))}
              className="w-full rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
            />
          </div>
        </div>
        <label className="mt-4 flex items-center gap-2 text-sm text-slate-200 cursor-pointer">
          <input
            type="checkbox"
            checked={permitirCruzamento}
            onChange={(e) => setPermitirCruzamento(e.target.checked)}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
          />
          Permitir cruzar variáveis brutas diferentes numa mesma regra
        </label>
        <p className="mt-1 text-xs text-slate-500">
          Desmarcado: cada regra só combina primitivas da mesma variável bruta (ex.: tendência e
          máximo do atraso, nunca atraso com renda) — útil se regra de negócio não quer misturar
          domínios diferentes numa condição só.
        </p>
      </Secao>

      <div className="flex items-center gap-3">
        <button
          onClick={aoRodar}
          disabled={rodando || !painel}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {rodando ? "Rodando…" : "Rodar"}
        </button>
        {erro && <p className="text-sm text-red-400">{erro}</p>}
      </div>

      {resultado && (
        <Secao titulo="Resultado">
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <Metrica rotulo="linhas do painel" valor={resultado.n_linhas_painel.toLocaleString("pt-BR")} />
            <Metrica rotulo="chaves" valor={resultado.n_chaves.toLocaleString("pt-BR")} />
            <Metrica rotulo="colunas geradas" valor={String(resultado.colunas_geradas.length)} />
            <Metrica rotulo="dev / teste" valor={`${resultado.n_dev} / ${resultado.n_teste}`} />
            <Metrica rotulo="taxa evento dev" valor={`${(resultado.taxa_evento_dev * 100).toFixed(1)}%`} />
            <Metrica rotulo="taxa evento teste" valor={`${(resultado.taxa_evento_teste * 100).toFixed(1)}%`} />
          </div>

          {resultado.regras.length === 0 ? (
            <p className="text-sm text-slate-500">
              Nenhuma regra sobreviveu aos filtros de suporte — tente ajustar suporte mínimo/máximo
              ou profundidade.
            </p>
          ) : (
            <>
              <div className="max-h-72 overflow-y-auto rounded-lg border border-slate-700">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-slate-800/90 text-slate-400">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">regra</th>
                      <th className="px-3 py-2 text-right font-medium">suporte dev</th>
                      <th className="px-3 py-2 text-right font-medium">suporte teste</th>
                      <th className="px-3 py-2 text-right font-medium">IV dev</th>
                      <th className="px-3 py-2 text-right font-medium">IV teste</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resultado.regras.map((r, i) => (
                      <tr key={i} className={i % 2 === 0 ? "bg-slate-900/40" : "bg-slate-900/70"}>
                        <td className="px-3 py-1.5 font-mono text-slate-300">{r.regra}</td>
                        <td className="px-3 py-1.5 text-right tabular-nums text-slate-400">
                          {r.suporte_dev.toFixed(3)}
                        </td>
                        <td className="px-3 py-1.5 text-right tabular-nums text-slate-400">
                          {r.suporte_teste.toFixed(3)}
                        </td>
                        <td className="px-3 py-1.5 text-right tabular-nums text-slate-400">
                          {r.iv_dev.toFixed(3)}
                        </td>
                        <td className="px-3 py-1.5 text-right tabular-nums text-emerald-400">
                          {r.iv_teste.toFixed(3)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {resultado.auc_sem_regra !== null && resultado.auc_com_regra !== null && (
                <div className="mt-4 rounded-lg border border-slate-700 bg-slate-800/60 p-3 text-xs">
                  <p className="mb-1 text-slate-400">
                    Melhor regra: <span className="font-mono text-slate-200">{resultado.melhor_regra}</span>
                  </p>
                  <p className="text-slate-400">
                    AUC (teste) sem a regra:{" "}
                    <span className="tabular-nums text-slate-200">{resultado.auc_sem_regra.toFixed(4)}</span>
                    {"  |  "}com a regra:{" "}
                    <span className="tabular-nums text-emerald-400">{resultado.auc_com_regra.toFixed(4)}</span>
                  </p>
                </div>
              )}
            </>
          )}
        </Secao>
      )}
    </div>
  );
}
