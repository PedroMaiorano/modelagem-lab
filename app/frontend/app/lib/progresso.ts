// Interpreta o stream de log do Pedro_Wise (texto solto, ver
// python/pedro_wise/{selection,level2,level3,pipeline}.py) pra derivar
// estado ao vivo: modelo atual, histórico de score, estágio da busca, e
// o histórico de candidatas testadas por passo (pra árvore de busca ao
// vivo). O core nunca manda dados estruturados por evento (só strings
// formatadas pro log — decisão deliberada de não acoplar o algoritmo à
// interface, ver docs/planos). Isso é sempre best-effort: cobre os
// formatos conhecidos de hoje, e se um novo tipo de evento for adicionado
// ao core sem atualizar aqui, o parser simplesmente ignora a linha (não
// quebra, só não atualiza o estado ao vivo pra aquele evento).

import type { LinhaProgresso } from "../components/ProgressoAoVivo";

export interface PontoScore {
  indice: number;
  score: number;
}

/** Um passo da busca (ex.: "forward simples testando 9 candidatas") — o
 * núcleo declara a lista ANTES de avaliar (ver
 * `pedro_wise.selection._resumo_candidatas`), e `vencedor` é preenchido
 * quando o evento de aceite correspondente chega logo em seguida (`null`
 * se nenhuma candidata melhorou o score e a busca seguiu adiante). */
export interface EstagioTeste {
  rotulo: string;
  candidatos: string[];
  vencedor: string | null;
}

export interface EstadoAoVivo {
  variaveisAtuais: string[];
  scoreAtual: number | null;
  historicoScore: PontoScore[];
  estagioAtual: string | null;
  nEventosAceitos: number;
  estagiosTeste: EstagioTeste[];
}

const PADROES: Array<{
  regex: RegExp;
  aplicar: (m: RegExpMatchArray, vars: string[]) => string[];
  /** Label da candidata vencedora no MESMO formato usado em `candidatos`
   * de `PADROES_TESTANDO` — permite casar o aceite com a declaração
   * aberta. `null` pro caso do nível 3 (não tem declaração "testando"
   * pareada nesse nível, é tratado à parte via pilha de ramos). */
  labelVencedor: ((m: RegExpMatchArray) => string) | null;
}> = [
  // "Nível 3: ramo vencedor ... => score=X | variaveis=a,b,c" — substitui o
  // conjunto inteiro (o ramo pode ter reconstruído o modelo do zero).
  {
    regex: /^Nível 3: ramo vencedor supera o modelo atual => score=[\d.]+ \| variaveis=(.*)$/,
    aplicar: (m) => m[1].split(",").filter(Boolean),
    labelVencedor: null,
  },
  // "forward_duplo: +v +w => score=X"
  {
    regex: /^forward_duplo: \+(\S+) \+(\S+) => score=[\d.]+/,
    aplicar: (m, vars) => [...vars, m[1], m[2]],
    labelVencedor: (m) => `${m[1]}+${m[2]}`,
  },
  // "forward_triplo: +v1 +v2 +v3 => score=X"
  {
    regex: /^forward_triplo: \+(\S+) \+(\S+) \+(\S+) => score=[\d.]+/,
    aplicar: (m, vars) => [...vars, m[1], m[2], m[3]],
    labelVencedor: (m) => `${m[1]}+${m[2]}+${m[3]}`,
  },
  // "transformacao_simples[nivel2]: -a +b => score=X" ou "transformacao_simples: -a +b => score=X"
  {
    regex: /^transformacao_simples(?:\[nivel2\])?: -(\S+) \+(\S+) => score=[\d.]+/,
    aplicar: (m, vars) => [...vars.filter((v) => v !== m[1]), m[2]],
    labelVencedor: (m) => `${m[1]}→${m[2]}`,
  },
  // "backward_simples[nivel2]: -v => score=X" ou "backward_simples: -v => score=X"
  {
    regex: /^backward_simples(?:\[nivel2\])?: -(\S+) => score=[\d.]+/,
    aplicar: (m, vars) => vars.filter((v) => v !== m[1]),
    labelVencedor: (m) => m[1],
  },
  // "forward_simples: +v => score=X"
  {
    regex: /^forward_simples: \+(\S+) => score=[\d.]+/,
    aplicar: (m, vars) => [...vars, m[1]],
    labelVencedor: (m) => m[1],
  },
];

const REGEX_SCORE = /score=([\d.]+)/;

const ROTULOS_ESTAGIO: Array<[RegExp, string]> = [
  [/^Nível 3/, "Nível 3 — backward complexo"],
  [/^backward_complexo/, "Nível 3 — backward complexo"],
  [/^Nível 2\.5 melhorou/, "voltando ao nível 1 (nível 2.5 melhorou)"],
  [/^Nível 2 melhorou/, "voltando ao nível 1 (nível 2 melhorou)"],
  [/^forward_triplo|^Forward triplo/, "nível 2.5 — forward triplo"],
  [/^forward_duplo|^Forward duplo/, "nível 2 — forward duplo"],
  [/^transformacao_simples\[nivel2\]/, "nível 2 — transformação"],
  [/^backward_simples\[nivel2\]/, "nível 2 — backward"],
  [/^transformacao_simples/, "nível 1 — transformação"],
  [/^backward_simples/, "nível 1 — backward"],
  [/^forward_simples|^Forward simples/, "nível 1 — forward"],
  [/^Shadow probing/, "shadow probing"],
];

function estagioDaLinha(mensagem: string): string | null {
  for (const [regex, rotulo] of ROTULOS_ESTAGIO) {
    if (regex.test(mensagem)) return rotulo;
  }
  return null;
}

// "testando N candidatas/trocas/remoções/pares/triplas: a,b,c" — declarado
// pelo núcleo ANTES de avaliar (ver pedro_wise/{selection,level2}.py),
// abre um EstagioTeste que fecha quando o próximo evento chega (aceite
// vira `vencedor`, qualquer outra coisa vira `vencedor: null`).
const PADROES_TESTANDO: Array<{ regex: RegExp; rotulo: string }> = [
  { regex: /^forward_simples: testando \d+ candidatas: (.*)$/, rotulo: "forward simples" },
  { regex: /^transformacao_simples: testando \d+ trocas: (.*)$/, rotulo: "transformação simples" },
  { regex: /^backward_simples: testando \d+ remoções: (.*)$/, rotulo: "backward simples" },
  { regex: /^forward_duplo: testando \d+ pares: (.*)$/, rotulo: "forward duplo" },
  { regex: /^forward_triplo: testando \d+ triplas: (.*)$/, rotulo: "forward triplo" },
];

// O nível 3 roda sub-buscas completas "por baixo" pra cada candidato de
// remoção, e TODAS logam através do mesmo logger global — inclusive as que
// acabam descartadas porque não superaram o modelo atual. Sem distinguir
// isso, a reconstrução do "modelo atual" e do histórico de score ficam
// contaminadas com exploração que nunca foi aceita de fato (bug real,
// encontrado testando contra o backend: variáveis "fantasma" apareciam no
// modelo reconstruído sem nunca terem sido removidas na leitura ingênua do
// log). `python/pedro_wise/level3.py` foi ajustado pra emitir um marcador de
// início ("avaliando N candidato(s)") e sempre um de fechamento — "ramo
// vencedor" (commita) ou "nenhum ramo superou" (descarta) — formando pares
// que empilham corretamente mesmo com recursão (profundidade_maxima > 1).
const REGEX_INICIO_RAMO = /^Nível 3: avaliando \d+ candidato\(s\) de remoção/;
const REGEX_DESCARTE_RAMO = /^Nível 3: nenhum ramo superou o modelo atual/;

interface SnapshotRamo {
  variaveis: string[];
  scoreAtual: number | null;
  historicoLen: number;
  estagiosTesteLen: number;
}

export function interpretarProgresso(linhas: LinhaProgresso[]): EstadoAoVivo {
  let variaveis: string[] = [];
  let scoreAtual: number | null = null;
  let historicoScore: PontoScore[] = [];
  let estagioAtual: string | null = null;
  let nEventosAceitos = 0;
  let estagiosTeste: EstagioTeste[] = [];
  let estagioAberto: EstagioTeste | null = null;
  const pilhaRamos: SnapshotRamo[] = [];

  function fecharEstagioAberto(vencedor: string | null) {
    if (!estagioAberto) return;
    estagiosTeste = [...estagiosTeste, { ...estagioAberto, vencedor }];
    estagioAberto = null;
  }

  for (const linha of linhas) {
    // Quando o p-valor máximo está ativo, o backend roda a busca de novo
    // DO ZERO sem a restrição, só pra comparação (ver
    // app/backend/logica.py:rodar_pipeline) — e os eventos dessa segunda
    // busca passam pelo mesmo logger, com os MESMOS nomes de evento
    // (forward_simples, etc.). Sem esse reset, o parser não tem como saber
    // que é uma busca nova e ia continuar empilhando em cima do estado da
    // primeira, duplicando variável no "modelo atual" (bug real visto na
    // tela: cloud_quad/humidity_inv/temparature_inv apareciam 2x).
    if (linha.tipo === "etapa" && /^Rodando sem o filtro de p-valor/.test(linha.mensagem)) {
      variaveis = [];
      scoreAtual = null;
      historicoScore = [];
      estagiosTeste = [];
      estagioAberto = null;
      pilhaRamos.length = 0;
      continue;
    }
    if (linha.tipo !== "log") continue;
    const mensagem = linha.mensagem.trim().replace(/^\[pulado\]\s*/, "");

    const estagio = estagioDaLinha(mensagem);
    if (estagio) estagioAtual = estagio;

    if (REGEX_INICIO_RAMO.test(mensagem)) {
      fecharEstagioAberto(null);
      pilhaRamos.push({ variaveis, scoreAtual, historicoLen: historicoScore.length, estagiosTesteLen: estagiosTeste.length });
      continue;
    }
    if (REGEX_DESCARTE_RAMO.test(mensagem)) {
      fecharEstagioAberto(null);
      const snapshot = pilhaRamos.pop();
      if (snapshot) {
        variaveis = snapshot.variaveis;
        scoreAtual = snapshot.scoreAtual;
        historicoScore = historicoScore.slice(0, snapshot.historicoLen);
        estagiosTeste = estagiosTeste.slice(0, snapshot.estagiosTesteLen);
      }
      continue;
    }

    let casouTestando = false;
    for (const padrao of PADROES_TESTANDO) {
      const m = mensagem.match(padrao.regex);
      if (!m) continue;
      fecharEstagioAberto(null); // declaração anterior nunca teve aceite — descartada
      const candidatos = m[1].split(",").filter(Boolean);
      estagioAberto = { rotulo: padrao.rotulo, candidatos, vencedor: null };
      casouTestando = true;
      break;
    }
    if (casouTestando) continue;

    for (const padrao of PADROES) {
      const m = mensagem.match(padrao.regex);
      if (!m) continue;
      variaveis = padrao.aplicar(m, variaveis);
      nEventosAceitos += 1;
      // "ramo vencedor" fecha (commita) o par aberto por "avaliando N candidato(s)".
      if (padrao === PADROES[0]) pilhaRamos.pop();
      if (padrao.labelVencedor) fecharEstagioAberto(padrao.labelVencedor(m));
      const scoreMatch = mensagem.match(REGEX_SCORE);
      if (scoreMatch) {
        scoreAtual = Number(scoreMatch[1]);
        historicoScore = [...historicoScore, { indice: historicoScore.length, score: scoreAtual }];
      }
      break;
    }
  }

  if (estagioAberto) estagiosTeste = [...estagiosTeste, estagioAberto];

  return { variaveisAtuais: variaveis, scoreAtual, historicoScore, estagioAtual, nEventosAceitos, estagiosTeste };
}
