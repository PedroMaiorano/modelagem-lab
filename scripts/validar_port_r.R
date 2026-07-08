# Valida o port Python rodando o Pedro_Wise_3.0.1 (R) sobre o dataset
# compartilhado gerado por gerar_dataset_validacao.py. Escreve
# data/validacao_r/resultado_r.txt com as variáveis selecionadas e o KS
# (dev/teste) para o script Python comparar.
#
# IMPORTANTE: usa scripts/Pedro_Wise_3.0.1_corrigido_para_validacao.R, não o
# arquivo em docs/algoritmos-originais/ diretamente — o original, como está,
# não roda (tem um `%>%` órfão em `forward_simples` que quebra em runtime; ver
# o cabeçalho da cópia corrigida para o diff exato, uma única linha).
#
# Uso: Rscript scripts/validar_port_r.R

.args <- commandArgs(trailingOnly = FALSE)
.arquivo_script <- sub("--file=", "", .args[grep("--file=", .args)])
raiz <- normalizePath(file.path(dirname(.arquivo_script), ".."))
dir_dados <- file.path(raiz, "data", "validacao_r")

df_treino <- read.csv(file.path(dir_dados, "dev.csv"))
df_teste <- read.csv(file.path(dir_dados, "teste.csv"))

# Sourcing do arquivo executa a busca completa no final do script (usa
# df_treino/df_teste já carregados acima) e deixa `modelo_final` no ambiente
# global — mesmo fluxo do script original, só com o bug de sintaxe corrigido.
source(file.path(raiz, "scripts", "Pedro_Wise_3.0.1_corrigido_para_validacao.R"))

variaveis_selecionadas <- names(coef(modelo_final))[-1] # remove "(Intercept)"
ks_dev <- calc_ks_score(modelo_final, df_treino, df_teste) # bug conhecido: só retorna KS-dev

# calc_ks_score não expõe o KS de teste (bug do as.numeric ignorando o 2º
# argumento) — replicamos aqui só o necessário para obter o KS de teste,
# reaproveitando as MESMAS quebras calculadas na base de dev.
calcular_ks_teste <- function(modelo, df_dev, df_teste) {
  df_dev$prob <- predict(modelo, newdata = df_dev, type = "response")
  df_dev$xbeta <- -log((1 / df_dev$prob) - 1)
  df_dev$SCORE_GAUSS <- trunc(500 + df_dev$xbeta * (100 / log(2)))
  q <- c(0, 0.025, 0.070, 0.150, 0.300, 0.500, 0.700, 0.85, 0.930, 0.975, 1)
  quebras <- quantile(df_dev$SCORE_GAUSS, q)

  df_teste$prob <- predict(modelo, newdata = df_teste, type = "response")
  df_teste$xbeta <- -log((1 / df_teste$prob) - 1)
  df_teste$SCORE_GAUSS <- trunc(500 + df_teste$xbeta * (100 / log(2)))

  df_teste$SCORE_LOG <- ifelse(
    df_teste$SCORE_GAUSS <= quebras[1], 0,
    ifelse(df_teste$SCORE_GAUSS <= quebras[2],
      0 + ((df_teste$SCORE_GAUSS - quebras[1]) * (100 - 0)) / (quebras[2] - quebras[1]),
      ifelse(df_teste$SCORE_GAUSS <= quebras[3],
        101 + ((df_teste$SCORE_GAUSS - quebras[2]) * (200 - 101)) / (quebras[3] - quebras[2]),
        ifelse(df_teste$SCORE_GAUSS <= quebras[4],
          201 + ((df_teste$SCORE_GAUSS - quebras[3]) * (300 - 201)) / (quebras[4] - quebras[3]),
          ifelse(df_teste$SCORE_GAUSS <= quebras[5],
            301 + ((df_teste$SCORE_GAUSS - quebras[4]) * (400 - 301)) / (quebras[5] - quebras[4]),
            ifelse(df_teste$SCORE_GAUSS <= quebras[6],
              401 + ((df_teste$SCORE_GAUSS - quebras[5]) * (500 - 401)) / (quebras[6] - quebras[5]),
              ifelse(df_teste$SCORE_GAUSS <= quebras[7],
                501 + ((df_teste$SCORE_GAUSS - quebras[6]) * (600 - 501)) / (quebras[7] - quebras[6]),
                ifelse(df_teste$SCORE_GAUSS <= quebras[8],
                  601 + ((df_teste$SCORE_GAUSS - quebras[7]) * (700 - 601)) / (quebras[8] - quebras[7]),
                  ifelse(df_teste$SCORE_GAUSS <= quebras[9],
                    701 + ((df_teste$SCORE_GAUSS - quebras[8]) * (800 - 701)) / (quebras[9] - quebras[8]),
                    ifelse(df_teste$SCORE_GAUSS <= quebras[10],
                      801 + ((df_teste$SCORE_GAUSS - quebras[9]) * (900 - 801)) / (quebras[10] - quebras[9]),
                      ifelse(df_teste$SCORE_GAUSS <= quebras[11],
                        901 + ((df_teste$SCORE_GAUSS - quebras[10]) * (1000 - 901)) / (quebras[11] - quebras[10]),
                        1000
                      )
                    )
                  )
                )
              )
            )
          )
        )
      )
    )
  )
  df_teste$SCORE <- trunc(df_teste$SCORE_LOG)
  ks.test(
    df_teste[df_teste$y == 1, ]$SCORE,
    df_teste[df_teste$y == 0, ]$SCORE
  )$statistic
}

ks_teste <- calcular_ks_teste(modelo_final, df_treino, df_teste)

cat("\n\n==== RESULTADO VALIDACAO R ====\n")
cat("VARIAVEIS:", paste(sort(variaveis_selecionadas), collapse = ","), "\n")
cat("KS_DEV:", as.numeric(ks_dev), "\n")
cat("KS_TESTE:", as.numeric(ks_teste), "\n")

writeLines(
  c(
    paste0("variaveis=", paste(sort(variaveis_selecionadas), collapse = ",")),
    paste0("ks_dev=", as.numeric(ks_dev)),
    paste0("ks_teste=", as.numeric(ks_teste))
  ),
  file.path(dir_dados, "resultado_r.txt")
)
cat("\nEscrito", file.path(dir_dados, "resultado_r.txt"), "\n")
