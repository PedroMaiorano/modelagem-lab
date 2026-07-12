"use client";

import { useEffect, useState } from "react";
import { buscarValoresDistintosBase, type BaseFeatureLab, type ValorDistintoBase } from "../lib/api";

interface Props {
  bases: BaseFeatureLab[];
  base: BaseFeatureLab | null;
  aoMudarBase: (base: BaseFeatureLab) => void;
  aoEnviarPainel: (arquivo: File, nome: string) => Promise<void>;
  colunasBase: string[];
  colunaY: string;
  aoMudarColunaY: (coluna: string) => void;
  metodoSplit: "aleatorio" | "coluna";
  aoMudarMetodoSplit: (metodo: "aleatorio" | "coluna") => void;
  colunaSplit: string;
  aoMudarColunaSplit: (coluna: string) => void;
  valoresDev: Set<string>;
  valoresTeste: Set<string>;
  aoAlternarValorSplit: (valor: string, destino: "dev" | "teste") => void;
  aoLimparTudo: () => void;
}

export default function SidebarFeatureLab({
  bases,
  base,
  aoMudarBase,
  aoEnviarPainel,
  colunasBase,
  colunaY,
  aoMudarColunaY,
  metodoSplit,
  aoMudarMetodoSplit,
  colunaSplit,
  aoMudarColunaSplit,
  valoresDev,
  valoresTeste,
  aoAlternarValorSplit,
  aoLimparTudo,
}: Props) {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [nome, setNome] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [valoresDistintos, setValoresDistintos] = useState<ValorDistintoBase[]>([]);

  useEffect(() => {
    if (!base || !colunaSplit || metodoSplit !== "coluna") return;
    buscarValoresDistintosBase(base.nome, base.tipo, colunaSplit)
      .then(setValoresDistintos)
      .catch(() => setValoresDistintos([]));
  }, [base, colunaSplit, metodoSplit]);

  async function aoClicarEnviar() {
    if (!arquivo || !nome.trim()) return;
    setEnviando(true);
    try {
      await aoEnviarPainel(arquivo, nome.trim());
      setArquivo(null);
      setNome("");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <aside className="w-72 shrink-0 border-r border-slate-700 bg-slate-900/70 p-5 flex flex-col gap-4 overflow-y-auto">
      <div>
        <h2 className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-2">Base</h2>
        <select
          className="w-full rounded-lg bg-slate-800 border border-slate-600 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          value={base ? `${base.tipo}:${base.nome}` : ""}
          onChange={(e) => {
            const [tipo, nomeBase] = e.target.value.split(":");
            aoMudarBase({ tipo: tipo as BaseFeatureLab["tipo"], nome: nomeBase });
          }}
        >
          {bases.map((b) => (
            <option key={`${b.tipo}:${b.nome}`} value={`${b.tipo}:${b.nome}`}>
              {b.nome}
            </option>
          ))}
        </select>
      </div>

      <div>
        <h2 className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-2">Coluna resposta</h2>
        {colunasBase.length > 0 ? (
          <select
            value={colunaY}
            onChange={(e) => aoMudarColunaY(e.target.value)}
            className="w-full rounded-lg bg-slate-800 border border-slate-600 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            {!colunasBase.includes(colunaY) && <option value={colunaY}>{colunaY}</option>}
            {colunasBase.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        ) : (
          <p className="text-[11px] text-slate-500">escolha uma base primeiro</p>
        )}
      </div>

      {colunasBase.length > 0 && (
        <div>
          <h2 className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-2">Split treino/teste</h2>
          <div className="flex gap-1.5">
            <button
              onClick={() => aoMudarMetodoSplit("aleatorio")}
              className={`flex-1 rounded-lg border px-2 py-1.5 text-xs font-medium transition ${
                metodoSplit === "aleatorio"
                  ? "border-emerald-600 bg-emerald-950/40 text-emerald-300"
                  : "border-slate-700 bg-slate-800/60 text-slate-400 hover:text-slate-200"
              }`}
            >
              aleatório
            </button>
            <button
              onClick={() => aoMudarMetodoSplit("coluna")}
              className={`flex-1 rounded-lg border px-2 py-1.5 text-xs font-medium transition ${
                metodoSplit === "coluna"
                  ? "border-emerald-600 bg-emerald-950/40 text-emerald-300"
                  : "border-slate-700 bg-slate-800/60 text-slate-400 hover:text-slate-200"
              }`}
            >
              coluna existente
            </button>
          </div>

          {metodoSplit === "coluna" && (
            <div className="mt-2 flex flex-col gap-2">
              <select
                value={colunaSplit}
                onChange={(e) => aoMudarColunaSplit(e.target.value)}
                className="w-full rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
              >
                <option value="">selecione a coluna…</option>
                {colunasBase.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>

              {valoresDistintos.length > 0 && (
                <div className="max-h-48 overflow-y-auto rounded-lg border border-slate-700">
                  <table className="w-full text-[11px]">
                    <thead className="sticky top-0 bg-slate-800/90 text-slate-500">
                      <tr>
                        <th className="px-2 py-1 text-left font-medium">valor</th>
                        <th className="px-2 py-1 text-right font-medium">treino</th>
                        <th className="px-2 py-1 text-right font-medium">teste</th>
                      </tr>
                    </thead>
                    <tbody>
                      {valoresDistintos.map((v) => (
                        <tr key={v.valor} className="border-t border-slate-800">
                          <td className="px-2 py-1 font-mono text-slate-300" title={`${v.contagem} linhas`}>
                            {v.valor}
                          </td>
                          <td className="px-2 py-1 text-right">
                            <input
                              type="checkbox"
                              checked={valoresDev.has(v.valor)}
                              onChange={() => aoAlternarValorSplit(v.valor, "dev")}
                              className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
                            />
                          </td>
                          <td className="px-2 py-1 text-right">
                            <input
                              type="checkbox"
                              checked={valoresTeste.has(v.valor)}
                              onChange={() => aoAlternarValorSplit(v.valor, "teste")}
                              className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
          <p className="mt-1 text-[11px] text-slate-500">
            {metodoSplit === "aleatorio"
              ? "50/50 aleatório — não se aplica se a fonte da esfera 2 já tiver dev/teste prontos (dataset flat)."
              : "marque quais valores da coluna viram treino e quais viram teste."}
          </p>
        </div>
      )}

      <div className="flex flex-col gap-2 border-t border-slate-800 pt-4">
        <h2 className="text-xs font-medium uppercase tracking-wider text-slate-500">Nova base (CSV)</h2>
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
          className="block text-xs text-slate-400 file:mr-2 file:rounded file:border-0 file:bg-slate-700 file:px-2 file:py-1 file:text-xs file:text-slate-200"
        />
        <input
          type="text"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          placeholder="nome da base"
          className="w-full rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
        />
        <button
          onClick={aoClicarEnviar}
          disabled={enviando || !arquivo || !nome.trim()}
          className="w-full rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-emerald-700 hover:text-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {enviando ? "Enviando…" : "Enviar"}
        </button>
      </div>

      <button
        onClick={aoLimparTudo}
        className="mt-auto rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-500 transition hover:border-red-800 hover:text-red-400"
      >
        Limpar tudo
      </button>
    </aside>
  );
}
