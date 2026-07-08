#!/usr/bin/env node
/**
 * Hook PreToolUse para Bash — modelagem-lab.
 * Bloqueia comandos que destruam o acervo (docs/, data/papers/, algoritmos-originais/)
 * ou operacoes git perigosas.
 * Exit 2 = bloqueia e devolve stderr ao Claude para correcao.
 */

let input = {};
try {
  input = JSON.parse(process.argv[2] || process.env.CLAUDE_TOOL_INPUT || '{}');
} catch (_) {
  // Fail-open: se nao parsear, nao bloqueia para nao travar o fluxo.
  process.exit(0);
}

const command = (input.tool_input?.command || input.command || '').trim();
if (!command) process.exit(0);

const BLOCKED_PATTERNS = [
  // Acervo de literatura (cache imutavel, caro de refazer e sujeito a rate limit)
  { pattern: /rm\s+(-[a-zA-Z]*\s+)*.*\bdata\/papers\b/i, label: 'remocao do cache de literatura (data/papers)' },
  { pattern: /rm\s+-rf\s+(\.\/)?data\b/i, label: 'rm -rf no diretorio data/' },
  { pattern: /rm\s+-rf\s+(\.\/)?docs\b/i, label: 'rm -rf no diretorio docs/ (acervo e algoritmo original)' },
  // Algoritmo original Pedro_Wise — peca insubstituivel do pilar 1
  { pattern: /rm\s+(-[a-zA-Z]*\s+)*.*algoritmos-originais/i, label: 'remocao de docs/algoritmos-originais (Pedro_Wise original)' },
  { pattern: /rm\s+-rf\s+\//, label: 'rm -rf na raiz do sistema' },

  // Git perigoso
  { pattern: /git\s+push\s+--force(?:-with-lease)?\s+(?:origin\s+)?(main|master)/i, label: 'force push em main/master' },
  { pattern: /git\s+reset\s+--hard\s+HEAD~[2-9]/, label: 'reset --hard de multiplos commits' },
  { pattern: /git\s+clean\s+-[a-z]*f[a-z]*d/i, label: 'git clean -fd (apaga arquivos nao rastreados)' },
];

for (const { pattern, label } of BLOCKED_PATTERNS) {
  if (pattern.test(command)) {
    process.stderr.write(
      `BLOQUEADO pelo hook de seguranca do modelagem-lab: "${label}".\n` +
      `Comando: ${command}\n` +
      `docs/, data/papers e o algoritmo original sao o acervo do lab e nao podem ser perdidos.\n` +
      `Se a operacao for realmente necessaria, peca autorizacao explicita ao usuario.`
    );
    process.exit(2);
  }
}

process.exit(0);
