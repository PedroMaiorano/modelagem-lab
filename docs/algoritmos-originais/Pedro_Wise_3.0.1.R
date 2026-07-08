

library(dplyr)
library(MASS)
library(smotefamily)
library(speedglm)
library(data.table)
calc_ks_score <- function(modelo, df_dev, df_teste) {
  # Checagens básicas
  stopifnot(is.data.frame(df_dev), is.data.frame(df_teste))
  stopifnot("y" %in% colnames(df_dev), "y" %in% colnames(df_teste))
  
  # 1) Predição e score na base de desenvolvimento
  df_dev$prob <- predict(modelo, newdata = df_dev, type = "response")
  df_dev$xbeta <- -log((1 / df_dev$prob) - 1)
  df_dev$SCORE_GAUSS <- trunc(500 + df_dev$xbeta * (100 / log(2)))
  
  # Definição das quebras
  q <- c(0, 0.025, 0.070, 0.150, 0.300, 0.500, 0.700, 0.85, 0.930, 0.975, 1)
  quebras <- quantile(df_dev$SCORE_GAUSS, q)
  
  df_dev$prob <- predict(modelo, newdata = df_dev, type = "response")
  df_dev$xbeta <- -log((1 / df_dev$prob) - 1)
  df_dev$SCORE_GAUSS <- trunc(500 + df_dev$xbeta * (100 / log(2)))
  
  df_dev$SCORE_LOG <- ifelse(
    df_dev$SCORE_GAUSS <= quebras[1], 0,
    ifelse(df_dev$SCORE_GAUSS <= quebras[2],
           0 + ((df_dev$SCORE_GAUSS - quebras[1]) * (100 - 0)) / (quebras[2] - quebras[1]),
           ifelse(df_dev$SCORE_GAUSS <= quebras[3],
                  101 + ((df_dev$SCORE_GAUSS - quebras[2]) * (200 - 101)) / (quebras[3] - quebras[2]),
                  ifelse(df_dev$SCORE_GAUSS <= quebras[4],
                         201 + ((df_dev$SCORE_GAUSS - quebras[3]) * (300 - 201)) / (quebras[4] - quebras[3]),
                         ifelse(df_dev$SCORE_GAUSS <= quebras[5],
                                301 + ((df_dev$SCORE_GAUSS - quebras[4]) * (400 - 301)) / (quebras[5] - quebras[4]),
                                ifelse(df_dev$SCORE_GAUSS <= quebras[6],
                                       401 + ((df_dev$SCORE_GAUSS - quebras[5]) * (500 - 401)) / (quebras[6] - quebras[5]),
                                       ifelse(df_dev$SCORE_GAUSS <= quebras[7],
                                              501 + ((df_dev$SCORE_GAUSS - quebras[6]) * (600 - 501)) / (quebras[7] - quebras[6]),
                                              ifelse(df_dev$SCORE_GAUSS <= quebras[8],
                                                     601 + ((df_dev$SCORE_GAUSS - quebras[7]) * (700 - 601)) / (quebras[8] - quebras[7]),
                                                     ifelse(df_dev$SCORE_GAUSS <= quebras[9],
                                                            701 + ((df_dev$SCORE_GAUSS - quebras[8]) * (800 - 701)) / (quebras[9] - quebras[8]),
                                                            ifelse(df_dev$SCORE_GAUSS <= quebras[10],
                                                                   801 + ((df_dev$SCORE_GAUSS - quebras[9]) * (900 - 801)) / (quebras[10] - quebras[9]),
                                                                   ifelse(df_dev$SCORE_GAUSS <= quebras[11],
                                                                          901 + ((df_dev$SCORE_GAUSS - quebras[10]) * (1000 - 901)) / (quebras[11] - quebras[10]),
                                                                          1000
                                                                   )))))))))))
  
  
  # SCORE final é trunc do SCORE_LOG
  df_dev$SCORE <- trunc(df_dev$SCORE_LOG)
  
  
  # 2) Predição e score na base de teste (df_teste)
  df_teste$prob <- predict(modelo, newdata = df_teste, type = "response")
  df_teste$xbeta <- -log((1 / df_teste$prob) - 1)
  df_teste$SCORE_GAUSS <- trunc(500 + df_teste$xbeta * (100 / log(2)))
  
  # Criação de SCORE_LOG de acordo com as quebras
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
                                                                   )))))))))))
  
  
  # SCORE final é trunc do SCORE_LOG
  df_teste$SCORE <- trunc(df_teste$SCORE_LOG)
  
  ks_value_1 <- ks.test(
    df_dev[df_dev$y == 1,]$SCORE,
    df_dev[df_dev$y == 0,]$SCORE
  )$statistic
  
  
   ks_value_2 <- ks.test(
    df_teste[df_teste$y == 1,]$SCORE,
    df_teste[df_teste$y == 0,]$SCORE
  )$statistic
  
  return(as.numeric(ks_value_1,ks_value_2))
}

Pedro_Wise_3.0 <- function(
    modelo_inicial,
    df_treino,
    df_teste,
    forward_simples_nivel_1 = TRUE,
    transformacao_simples_nivel_1 = TRUE,
    backward_simples_nivel_1 = TRUE,
    forward_duplo_nivel_2 = TRUE,
    transformacao_simples_nivel_2 = TRUE,
    backward_simples_nivel_2 = TRUE,
    forward_triplo_nivel_2 = TRUE,
    backward_complexo_nivel_3 = TRUE,
    n_best_duplo = 5,
    n_best_triplo_1 = 2,
    n_best_triplo_2 = 2,
    n_best_backward = 0,
    n_max_prolongamento = 0,
    n_max_complexidade = 999,
    trace = TRUE
){
  #### 1) Checagens iniciais ####
  stopifnot(is.data.frame(df_treino), is.data.frame(df_teste))
  stopifnot("y" %in% colnames(df_treino), "y" %in% colnames(df_teste))
  
  # Verificar se modelo_inicial é um objeto glm binomial
  if (!inherits(modelo_inicial, "glm")) {
    stop("O argumento 'modelo_inicial' não é um objeto glm.")
  }
  if (family(modelo_inicial)$family != "binomial") {
    stop("O 'modelo_inicial' precisa ter família = binomial.")
  }
  
  #### 2) Funções internas ####
  
  # Usa calc_ks_score para calcular o KS do modelo atual
  calc_ks_local <- function(mod) {
    calc_ks_score(mod, df_treino, df_teste)
  }
  
  # Pega as variáveis do modelo (exceto 'y')
  get_vars <- function(modelo) {
    all.vars(formula(modelo))[-1]
  }
  
  # Converte a fórmula para string (para manipular facilmente)
  formula_to_string <- function(modelo) {
    paste(deparse(formula(modelo)), collapse = " ")
  }
  
  # Extrai prefixo (antes do último "_") – se for parte da sua lógica de base
  extrair_base <- function(var) {
    sub("_[^_]+$", "", var)
  }
  
  # Filtra variáveis fora do modelo, ignorando a resposta 'y'
  filtrar_variaveis_fora_modelo <- function(vars_no_modelo, todas_variaveis) {
    todas_variaveis <- setdiff(todas_variaveis, "y")  # remove var resposta
    
    vars_base_modelo <- unique(sapply(vars_no_modelo, extrair_base))
    vars_base_treino <- unique(sapply(todas_variaveis, extrair_base))
    
    # quais "bases" ainda não foram usadas
    vars_fora_modelo <- setdiff(vars_base_treino, vars_base_modelo)
    
    # retorna apenas variáveis cujos prefixos ainda não estão no modelo
    vars_fora_modelo_com_versao <- todas_variaveis[
      unlist(sapply(todas_variaveis, function(v) {
        base_ <- extrair_base(v)
        base_ %in% vars_fora_modelo
      }))
    ]
    return(vars_fora_modelo_com_versao)
  }
  
  # Forward simples: testa adicionar cada var fora do modelo
  forward_simples <- function(melhor_modelo, dados) {
    vars_no_modelo <- get_vars(melhor_modelo)
    vars_disponiveis <- filtrar_variaveis_fora_modelo(vars_no_modelo, colnames(dados))
    results_single <- data.frame(var = character(0), ks = numeric(0))
    
    if (length(vars_disponiveis) == 0) {
      if (trace) cat("Forward simples: sem variáveis disponíveis\n")
      return(results_single)
    }
    
    f_str <- formula_to_string(melhor_modelo)
    for (v in vars_disponiveis) {
      nova_formula <- as.formula(paste(f_str, "+", v))
      # Ajuste do modelo com tryCatch para não quebrar
      mod_temp <- tryCatch(
        suppressWarnings(glm(nova_formula, data = dados, family = binomial)),
        error = function(e) NULL
      ) %>% 
      if (!is.null(mod_temp)) {
        ks_temp <- calc_ks_local(mod_temp)
        results_single <- rbind(results_single, data.frame(var = v, ks = ks_temp))
      }
    }
    return(results_single)
  }
  
  # Forward duplo: pega as n_best_duplo variáveis do forward simples e combina em pares
  forward_duplo <- function(result_single, melhor_modelo, dados, n_best_duplo) {
    if (nrow(result_single) == 0) {
      return(data.frame(var1=character(0), var2=character(0), ks=numeric(0)))
    }
    # ordena e pega top n
    result_single <- result_single[order(result_single$ks, decreasing = TRUE), ]
    result_single <- head(result_single, n_best_duplo)
    
    vars_no_modelo <- get_vars(melhor_modelo)
    vars_disponiveis <- filtrar_variaveis_fora_modelo(vars_no_modelo, colnames(dados))
    
    result_double <- data.frame(var1 = character(0), var2 = character(0), ks = numeric(0))
    f_str <- formula_to_string(melhor_modelo)
    
    hist_vars <- c() # para não repetir combinações
    
    for (v in result_single$var) {
      # filtra var disponíveis excluindo as já testadas
      vars_disponiveis_2 <- filtrar_variaveis_fora_modelo(
        v,
        setdiff(vars_disponiveis, hist_vars)
      )
      hist_vars <- c(hist_vars, v)
      
      if (length(vars_disponiveis_2) == 0) {
        if (trace) cat("Forward duplo: sem variáveis disponíveis para combinar com", v, "\n")
        next
      }
      for (w in vars_disponiveis_2) {
        nova_formula_2 <- as.formula(paste(f_str, "+", v, "+", w))
        mod_temp <- tryCatch(
          suppressWarnings(glm(nova_formula_2, data = dados, family = binomial)),
          error = function(e) NULL
        )
        if (!is.null(mod_temp)) {
          ks_temp <- calc_ks_local(mod_temp)
          result_double <- rbind(result_double, data.frame(var1 = v, var2 = w, ks = ks_temp))
        }
      }
    }
    return(result_double)
  }
  
  # Forward triplo: combinando 3 variáveis com base no top do forward duplo
  forward_triplo <- function(result_double, melhor_modelo, dados, n_best_triplo_1, n_best_triplo_2) {
    if (!requireNamespace("dplyr", quietly = TRUE)) {
      stop("Pacote 'dplyr' é necessário para forward_triplo(). Instale usando install.packages('dplyr').")
    }
    
    if (nrow(result_double) == 0) {
      return(data.frame(var1=character(0), var2=character(0), var3=character(0), ks=numeric(0)))
    }
    
    result_double <- result_double[order(result_double$ks, decreasing = TRUE), ]
    
    # pega os n_best_triplo_1 valores de var1 e, para cada, pega n_best_triplo_2 var2
    var_fixa_1 <- unique(result_double$var1)[1:n_best_triplo_1]
    
    result_tmp <- result_double %>%
      dplyr::filter(var1 %in% var_fixa_1) %>%
      dplyr::group_by(var1) %>%
      dplyr::slice_max(order_by = ks, n = n_best_triplo_2) %>%
      dplyr::ungroup()
    
    vars_no_modelo <- get_vars(melhor_modelo)
    result_triple <- data.frame(var1=character(0), var2=character(0), var3=character(0), ks=numeric(0))
    f_str <- formula_to_string(melhor_modelo)
    
    for (v in unique(result_tmp$var1)) {
      subset_v <- subset(result_tmp, var1 == v)
      for (w in unique(subset_v$var2)) {
        # Montar as variáveis já no modelo
        vars_no_modelo_atual <- c(vars_no_modelo, v, w)
        
        # Filtra as bases ainda não usadas
        vars_disp_triple <- filtrar_variaveis_fora_modelo(vars_no_modelo_atual, colnames(dados))
        
        if (length(vars_disp_triple) == 0) {
          if (trace) cat("Forward Triplo: sem variáveis disponíveis para (",v,",",w,")\n")
          next
        }
        
        for (z in vars_disp_triple) {
          nova_formula_3 <- as.formula(paste(f_str, "+", v, "+", w, "+", z))
          mod_temp <- tryCatch(
            suppressWarnings(glm(nova_formula_3, data=dados, family=binomial)),
            error = function(e) NULL
          )
          if (!is.null(mod_temp)) {
            ks_temp <- calc_ks_local(mod_temp)
            result_triple <- rbind(
              result_triple,
              data.frame(var1=v, var2=w, var3=z, ks=ks_temp)
            )
          }
        }
      }
    }
    return(result_triple)
  }
  
  # Backward simples: tenta remover cada variável do modelo
  backward_simples <- function(melhor_modelo, dados) {
    vars_no_modelo <- get_vars(melhor_modelo)
    results_remove <- data.frame(var = character(0), ks = numeric(0))
    f_str <- formula_to_string(melhor_modelo)
    
    for (v in vars_no_modelo) {
      nova_formula <- as.formula(paste(f_str, "-", v))
      mod_temp <- tryCatch(
        suppressWarnings(glm(nova_formula, data=dados, family=binomial)),
        error = function(e) NULL
      )
      if (!is.null(mod_temp)) {
        ks_temp <- calc_ks_local(mod_temp)
        results_remove <- rbind(results_remove, data.frame(var = v, ks = ks_temp))
      }
    }
    return(results_remove)
  }
  
  # Troca simples: remove uma versão da variável e insere outra versão transformada
  teste_troca_simples <- function(melhor_modelo, dados){
    vars_no_modelo <- get_vars(melhor_modelo)
    vars_disponiveis <- filtrar_variaveis_fora_modelo(vars_no_modelo, colnames(dados))
    vars_transformadas <- setdiff(setdiff(colnames(dados), vars_no_modelo), vars_disponiveis)
    
    associacoes <- expand.grid(var_out=vars_no_modelo, var_in=vars_transformadas, stringsAsFactors=FALSE)
    
    # Filtra associações em que "base" coincide (ex.: extrair_base(x) == extrair_base(y))
    associacoes <- associacoes[
      extrair_base(associacoes$var_out) == extrair_base(associacoes$var_in),
    ]
    
    if(nrow(associacoes) == 0){
      if (trace) cat("Troca simples: sem variáveis transformadas correspondentes.\n")
      return(data.frame())
    }
    
    lista_ks <- numeric(nrow(associacoes))
    f_str <- formula_to_string(melhor_modelo)
    
    for (i in seq_len(nrow(associacoes))) {
      row_ <- associacoes[i, , drop=FALSE]
      var_out <- row_$var_out
      var_in  <- row_$var_in
      
      if (!(var_out %in% colnames(dados)) || !(var_in %in% colnames(dados))) {
        if (trace) cat("Erro: Variável não encontrada em dados:", var_out, var_in, "\n")
        lista_ks[i] <- NA
        next
      }
      
      # Criar nova fórmula removendo var_out e adicionando var_in
      termos <- unlist(strsplit(gsub("y ~ ", "", f_str), " \\+ "))
      termos <- setdiff(termos, var_out)
      termos <- c(termos, var_in)
      nova_formula <- as.formula(paste("y ~", paste(termos, collapse=" + ")))
      
      mod_temp <- tryCatch(
        suppressWarnings(glm(nova_formula, data=dados, family=binomial)),
        error = function(e) {
          if (trace) cat("Erro ao ajustar modelo:", conditionMessage(e), "\n")
          return(NULL)
        }
      )
      if (!is.null(mod_temp)) {
        ks_temp <- calc_ks_local(mod_temp)
        lista_ks[i] <- ks_temp
      } else {
        lista_ks[i] <- NA
      }
    }
    
    associacoes$ks <- lista_ks
    return(associacoes)
  }
  
  #### 3) Lógica Principal de Seleção ####
  
  melhor_modelo_global <- modelo_inicial
  melhor_ks_global <- calc_ks_local(melhor_modelo_global)
  modelo_melhorado <- TRUE
  nivel_atual <- 1
  
  if (trace) {
    cat("Modelo inicial: KS =", format(melhor_ks_global, digits=6), "\n")
  }
  
  while (modelo_melhorado) {
    modelo_melhorado <- FALSE
    modelo_atual <- melhor_modelo_global
    ks_atual <- calc_ks_local(modelo_atual)
    formula_atual <- formula_to_string(modelo_atual)
    complexidade_melhor_modelo <- length(get_vars(modelo_atual))
    
    if ( complexidade_melhor_modelo >= n_max_complexidade ){
      cat("\n Complexidade máxima atingida \n")
      return(modelo_atual)
    }
    
    ## -- Nível 1 -- ##
    if (nivel_atual == 1) {
      if (trace) cat("\n[ Nível 1 ]\n")
      
      # 1. Forward simples
      if (forward_simples_nivel_1) {
        if (trace) cat("-> Forward simples nível 1 iniciada\n")
        
        tabela_fws <- forward_simples(modelo_atual, df_treino)
        tabela_fws <- tabela_fws[order(tabela_fws$ks, decreasing = TRUE), ]
        
        if (nrow(tabela_fws) > 0) {
          var_nova <- tabela_fws$var[1]
          ks_novo  <- tabela_fws$ks[1]
          
          # Verifica se KS melhorou e se a var_nova realmente existe
          if (!is.na(var_nova) && var_nova %in% colnames(df_treino) && ks_novo > ks_atual) {
            nova_formula <- as.formula(paste(formula_atual, "+", var_nova))
            modelo_temp <- tryCatch(
              suppressWarnings(glm(nova_formula, data=df_treino, family=binomial)),
              error=function(e) NULL
            )
            if (!is.null(modelo_temp)) {
              ks_atual_temp <- calc_ks_local(modelo_temp)
              
              if (ks_atual_temp > ks_atual) {
                modelo_atual <- modelo_temp
                ks_atual <- ks_atual_temp
                formula_atual <- formula_to_string(modelo_atual)
                modelo_melhorado <- TRUE
                if (trace) {
                  cat(sprintf("-> [Global Update] Forward Simples: +%s => KS: %.4f\n", var_nova, ks_atual))
                }
              }
            }
          }
        } else {
          if (trace) cat("Nenhuma variável disponível para Forward Simples.\n")
        }
      }
      
      # 2. Transformação simples
      if (transformacao_simples_nivel_1) {
        if (trace) cat("-> Transformação simples nível 1 iniciada\n")
        
        tabela_tfs <- teste_troca_simples(modelo_atual, df_treino)
        if (nrow(tabela_tfs) > 0) {
          tabela_tfs <- tabela_tfs[order(tabela_tfs$ks, decreasing=TRUE), ]
          melhor_ks_troca <- tabela_tfs$ks[1]
          var_out <- tabela_tfs$var_out[1]
          var_in  <- tabela_tfs$var_in[1]
          
          if (melhor_ks_troca > ks_atual) {
            # Montar a nova fórmula
            termos <- unlist(strsplit(gsub("y ~ ", "", formula_atual), " \\+ "))
            termos <- setdiff(termos, var_out)
            termos <- c(termos, var_in)
            nova_formula_str <- paste("y ~", paste(termos, collapse=" + "))
            nova_formula <- as.formula(nova_formula_str)
            
            modelo_temp <- tryCatch(
              suppressWarnings(glm(nova_formula, data=df_treino, family=binomial)),
              error = function(e) NULL
            )
            if (!is.null(modelo_temp)) {
              ks_temp <- calc_ks_local(modelo_temp)
              if (ks_temp > ks_atual) {
                modelo_atual <- modelo_temp
                ks_atual <- ks_temp
                formula_atual <- formula_to_string(modelo_atual)
                modelo_melhorado <- TRUE
                if (trace) {
                  cat(sprintf("-> [Global Update] Troca simples: -%s +%s => KS: %.4f\n", var_out, var_in, ks_atual))
                }
              }
            }
          }
        }
      }
      
      # 3. Backward simples
      if (backward_simples_nivel_1 && length(get_vars(modelo_atual)) > 5) {
        if (trace) cat("-> Backward simples nível 1 iniciada\n")
        
        tabela_bws <- backward_simples(modelo_atual, df_treino)
        tabela_bws <- tabela_bws[order(tabela_bws$ks, decreasing=TRUE), ]
        
        if (nrow(tabela_bws) > 0) {
          melhor_ks_bw <- tabela_bws$ks[1]
          var_removida <- tabela_bws$var[1]
          
          if (melhor_ks_bw > ks_atual) {
            termos <- unlist(strsplit(gsub("y ~ ", "", formula_atual), " \\+ "))
            termos <- setdiff(termos, var_removida)
            nova_formula_str <- paste("y ~", paste(termos, collapse=" + "))
            nova_formula <- as.formula(nova_formula_str)
            
            modelo_temp <- tryCatch(
              suppressWarnings(glm(nova_formula, data=df_treino, family=binomial)),
              error=function(e) NULL
            )
            if (!is.null(modelo_temp)) {
              ks_temp <- calc_ks_local(modelo_temp)
              if (ks_temp > ks_atual) {
                modelo_atual <- modelo_temp
                ks_atual <- ks_temp
                formula_atual <- formula_to_string(modelo_atual)
                modelo_melhorado <- TRUE
                if (trace) cat(sprintf("-> [Global Update] Backward: -%s => KS: %.4f\n", var_removida, ks_atual))
              }
            }
          }
        }
      }
    } # Fim nivel 1
    
    # Atualiza melhor global se teve melhora
    if (ks_atual > melhor_ks_global) {
      melhor_modelo_global <- modelo_atual
      melhor_ks_global <- ks_atual
    } else {
      # se não melhorou, avança p/ nível 2
      modelo_melhorado <- FALSE
      nivel_atual <- 2
    }
    
    ## -- Nível 2 -- ##
    if (nivel_atual == 2) {
      if (trace) cat("\n[ Nível 2 ]\n")
      
      # Partimos do modelo_atual
      modelo_nivel_2 <- modelo_atual
      ks_nivel_2 <- ks_atual
      formula_nivel_2 <- formula_atual
      
      # 1. Forward duplo
      if (forward_duplo_nivel_2) {
        if (trace) cat("-> Forward duplo nível 2 iniciada\n")
        if(forward_simples_nivel_1 == FALSE){
          tabela_fws <- forward_simples(modelo_atual, df_treino)
          tabela_fws <- tabela_fws[order(tabela_fws$ks, decreasing = TRUE), ]
        }
        
        #presumis que fws rodou
        tabela_fwd <- forward_duplo(tabela_fws, modelo_nivel_2, df_treino, n_best_duplo)
        tabela_fwd <- tabela_fwd[order(tabela_fwd$ks, decreasing=TRUE), ]
        
        if (nrow(tabela_fwd) > 0) {
          var1 <- tabela_fwd$var1[1]
          var2 <- tabela_fwd$var2[1]
          ks_novo <- tabela_fwd$ks[1]
          
          if (ks_novo > ks_nivel_2) {
            nova_formula_2 <- as.formula(paste(formula_nivel_2, "+", var1, "+", var2))
            modelo_temp <- tryCatch(
              suppressWarnings(glm(nova_formula_2, data=df_treino, family=binomial)),
              error=function(e) NULL
            )
            if (!is.null(modelo_temp)) {
              ks_temp <- calc_ks_local(modelo_temp)
              if (ks_temp > ks_nivel_2) {
                modelo_nivel_2 <- modelo_temp
                ks_nivel_2 <- ks_temp
                formula_nivel_2 <- formula_to_string(modelo_nivel_2)
                if (trace) {
                  cat(sprintf("-> [Nível 2 Update] Forward Duplo: +%s, +%s => KS: %.4f\n", var1, var2, ks_nivel_2))
                }
              }
            }
          }
        }
      }
      
      # 2. Transformação simples nível 2
      if (transformacao_simples_nivel_2) {
        if (trace) cat("-> Transformação simples nível 2 iniciada\n")
        tabela_tfs <- teste_troca_simples(modelo_nivel_2, df_treino)
        
        if (nrow(tabela_tfs) > 0) {
          tabela_tfs <- tabela_tfs[order(tabela_tfs$ks, decreasing=TRUE), ]
          
          ks_tfs_top <- tabela_tfs$ks[1]
          var_out <- tabela_tfs$var_out[1]
          var_in  <- tabela_tfs$var_in[1]
          
          if (ks_tfs_top > ks_nivel_2) {
            # monta nova fórmula
            termos <- unlist(strsplit(gsub("y ~ ", "", formula_nivel_2), " \\+ "))
            termos <- setdiff(termos, var_out)
            termos <- c(termos, var_in)
            nova_formula <- as.formula(paste("y ~", paste(termos, collapse=" + ")))
            
            modelo_temp <- tryCatch(
              suppressWarnings(glm(nova_formula, data=df_treino, family=binomial)),
              error=function(e) NULL
            )
            if (!is.null(modelo_temp)) {
              ks_temp <- calc_ks_local(modelo_temp)
              if (ks_temp > ks_nivel_2) {
                modelo_nivel_2 <- modelo_temp
                ks_nivel_2 <- ks_temp
                formula_nivel_2 <- formula_to_string(modelo_nivel_2)
                if (trace) {
                  cat(sprintf("-> [Nível 2 Update] Troca Simples: -%s +%s => KS: %.4f\n", var_out, var_in, ks_nivel_2))
                }
              }
            }
          }
        }
      }
      
      # 3. Backward simples nível 2
      if (backward_simples_nivel_2 && length(get_vars(modelo_nivel_2)) > 5) {
        if (trace) cat("-> Backward simples nível 2 iniciada\n")
        tabela_bws <- backward_simples(modelo_nivel_2, df_treino)
        tabela_bws <- tabela_bws[order(tabela_bws$ks, decreasing=TRUE), ]
        
        if (nrow(tabela_bws) > 0) {
          ks_bw_top <- tabela_bws$ks[1]
          var_bw    <- tabela_bws$var[1]
          if (ks_bw_top > ks_nivel_2) {
            termos <- unlist(strsplit(gsub("y ~ ", "", formula_nivel_2), " \\+ "))
            termos <- setdiff(termos, var_bw)
            nova_formula_str <- paste("y ~", paste(termos, collapse=" + "))
            nova_formula <- as.formula(nova_formula_str)
            
            modelo_temp <- tryCatch(
              suppressWarnings(glm(nova_formula, data=df_treino, family=binomial)),
              error=function(e) NULL
            )
            if (!is.null(modelo_temp)) {
              ks_temp <- calc_ks_local(modelo_temp)
              if (ks_temp > ks_nivel_2) {
                modelo_nivel_2 <- modelo_temp
                ks_nivel_2 <- ks_temp
                formula_nivel_2 <- formula_to_string(modelo_nivel_2)
                if (trace) {
                  cat(sprintf("-> [Nível 2 Update] Backward: -%s => KS: %.4f\n", var_bw, ks_nivel_2))
                }
              }
            }
          }
        }
      }
      
      # Verifica se melhorou global
      if (ks_nivel_2 > melhor_ks_global) {
        melhor_modelo_global <- modelo_nivel_2
        melhor_ks_global <- ks_nivel_2
        nivel_atual <- 1
        modelo_melhorado <- TRUE
        formula_atual <- formula_nivel_2
        
        if (trace) cat(sprintf("-> [Global Update] Modelo nível 2 virou melhor => KS: %.4f\n", ks_nivel_2))
      } else {
        if (trace) cat(sprintf("-> [Global Update] Nada melhor no nível 2 => KS atual: %.4f\n", melhor_ks_global))
        nivel_atual <- 2.5
      }
    }
    
    ## -- Nível 2.5 (Forward triplo) -- ##
    if (nivel_atual == 2.5) {
      if (trace) cat("\n[ Nível 2.5 ]\n")
      
      modelo_melhorado <- FALSE
      modelo_atual <- melhor_modelo_global
      ks_atual <- calc_ks_local(modelo_atual)
      formula_atual <- formula_to_string(modelo_atual)
      
      if (forward_triplo_nivel_2) {
        if (trace) cat("-> Forward triplo nível 2.5 iniciada\n")
        
        if(forward_simples_nivel_1 == FALSE){
          tabela_fws <- forward_simples(modelo_atual, df_treino)
          tabela_fws <- tabela_fws[order(tabela_fws$ks, decreasing = TRUE), ]
        }
        if(forward_duplo_nivel_2 == FALSE){
          tabela_fwd <- forward_duplo(tabela_fws,modelo_atual, df_treino,n_best_duplo)
          tabela_fwd <- tabela_fwd[order(tabela_fwd$ks, decreasing = TRUE), ]
        }
        
        tabela_fwt <- forward_triplo(tabela_fwd, modelo_atual, df_treino, n_best_triplo_1, n_best_triplo_2)
        tabela_fwt <- tabela_fwt[order(tabela_fwt$ks, decreasing=TRUE), ]
        
        if (nrow(tabela_fwt) > 0) {
          top_ks_triplo <- tabela_fwt$ks[1]
          v1 <- tabela_fwt$var1[1]
          v2 <- tabela_fwt$var2[1]
          v3 <- tabela_fwt$var3[1]
          
          if (top_ks_triplo > ks_atual) {
            nova_formula <- as.formula(paste(formula_atual, "+", v1, "+", v2, "+", v3))
            modelo_temp <- tryCatch(
              suppressWarnings(glm(nova_formula, data=df_treino, family=binomial)),
              error=function(e) NULL
            )
            if (!is.null(modelo_temp)) {
              ks_temp <- calc_ks_local(modelo_temp)
              if (ks_temp > ks_atual) {
                melhor_modelo_global <- modelo_temp
                ks_atual <- ks_temp
                formula_atual <- formula_to_string(melhor_modelo_global)
                modelo_melhorado <- TRUE
                nivel_atual <- 1
                if (trace) {
                  cat(sprintf("-> [Global Update] Forward Triplo: +%s +%s +%s => KS: %.4f\n", v1, v2, v3, ks_atual))
                }
              }
            }
          }
        }
      } else {
        if (trace) cat(sprintf("-> [Nível 2.5] Nenhuma combinação tripla melhor => KS: %.4f\n", melhor_ks_global))
        nivel_atual <- 3
      }
    }
    
    if (nivel_atual == 3) {
      if (trace) cat("\n[ Nível 3 ]\n")
      
      modelo_melhorado <- FALSE
      modelo_atual <- melhor_modelo_global
      ks_atual <- calc_ks_local(modelo_atual)
      formula_atual <- formula_to_string(modelo_atual)
      
      if (backward_complexo_nivel_3) {
        if (trace) cat("-> Backward Complexo nível 3 iniciada\n")
        if (trace) cat(sprintf("\n Localizando as %s variáveis \n", n_best_backward))
        
        
        tabela_bws <- backward_simples(modelo_atual, df_treino)
        tabela_bws <- tabela_bws[order(tabela_bws$ks, decreasing=TRUE), ]
        lista_var <- c()
        lista_ks <- c()
        lista_modelo <- c()
        if (nrow(tabela_bws) > 0) {
          for (i in 1:n_best_backward) {
            cat(sprintf("\n %s \n", tabela_bws$var[i]))
          }
          
          
          cat("\n ############## \n")
          cat("\n ############## \n")
          
          for (i in 1:n_best_backward) {
            var_remover <- tabela_bws$var[i]
            
            cat(sprintf("\n Removendo a variável %s \n", var_remover))
            cat(sprintf("Ks atual: %s \n", tabela_bws$ks[i]))
            
            modelo_bwc <- update(modelo_atual, paste0(". ~ . - ", var_remover))
            
            modelo_bwc <- Pedro_Wise_3.0(modelo_bwc,
                                         subset(df_treino, select = -var_remover),
                                         subset(df_teste, select = -var_remover),
                                         forward_simples_nivel_1 = forward_simples_nivel_1,
                                         transformacao_simples_nivel_1 = transformacao_simples_nivel_1,
                                         backward_simples_nivel_1 = backward_simples_nivel_1,
                                         forward_duplo_nivel_2 = forward_duplo_nivel_2,
                                         transformacao_simples_nivel_2 = transformacao_simples_nivel_2,
                                         backward_simples_nivel_2 = backward_simples_nivel_2,
                                         forward_triplo_nivel_2 = forward_triplo_nivel_2,
                                         backward_complexo_nivel_3 = FALSE,
                                         n_best_duplo = n_best_duplo,
                                         n_best_triplo_1 = n_best_triplo_1,
                                         n_best_triplo_2 = n_best_triplo_2,
                                         n_best_backward = 0,
                                         n_max_prolongamento = 0,
                                         n_max_complexidade = length(get_vars(modelo_bwc))+n_max_prolongamento,
                                         trace = TRUE)
          
            lista_var     <- c(lista_var,var_remover)
            lista_ks      <- c(lista_ks,calc_ks_local(modelo_bwc))
            lista_modelo  <- c(lista_modelo,modelo_bwc)
          }
          cat(sprintf("\n Fim do Backward Complexo \n"))
          cat(sprintf("\n Avaliando resultados \n"))
          
          Resultado_backward_complexo <- data.frame(
            var = lista_var,
            ks = lista_ks,
            modelo = lista_modelo
          )
          Resultado_backward_complexo <- Resultado_backward_complexo[order(Resultado_backward_complexo$ks, decreasing=TRUE), ]
          
          if (Resultado_backward_complexo$ks[1] > ks_atual){
            cat(sprintf("\n Backward Complexo: encontrou uma otimização \n"))
            cat(sprintf("\n Backward Complexo: remover a variavel %s \n",Resultado_backward_complexo$var[1]))
            cat(sprintf("\n Dando continuidade \n"))
            
            melhor_modelo_global <- Resultado_backward_complexo$modelo[[1]]
            ks_atual <- calc_ks_local(modelo_bwc)
            formula_atual <- formula_to_string(melhor_modelo_global)
            modelo_melhorado <- TRUE
            nivel_atual <- 1
            
          }else{
              cat(sprintf("\n Backward Complexo: Deu ruim! \n"))
            
          }
            
          }
        }
      }
  } 
  
  return(melhor_modelo_global)
}

#dados2 <- fread(file = "D:/OneDrive - StepWise/20250212_Banco_BV/base_teste_auto_ks3.txt")
#colnames(dados2)[1] <- "y"
#
#df_treino <- dados2[dados2$AMOSTRA == "DES"]
#df_teste <- dados2[dados2$AMOSTRA == "OOT"]
#df_treino$AMOSTRA <- NULL
#df_teste$AMOSTRA <- NULL

# Ajuste de modelo inicial (nulo)
modelo_nulo <- glm(y ~ 1, data=df_treino, family=binomial)
modelo_final <- Pedro_Wise_3.0(
  modelo_inicial = modelo_nulo,
  df_treino      = df_treino,
  df_teste       = df_teste,
  forward_simples_nivel_1  = TRUE,
  transformacao_simples_nivel_1 = TRUE,
  backward_simples_nivel_1 = TRUE,
  forward_duplo_nivel_2    = TRUE,
  
  transformacao_simples_nivel_2 = TRUE,
  backward_simples_nivel_2 = TRUE,
  forward_triplo_nivel_2   = TRUE,
  backward_complexo_nivel_3 = FALSE,
  n_best_duplo     = 5,
  n_best_triplo_1  = 3,
  n_best_triplo_2  = 3,
  n_best_backward  = 0,
  n_max_prolongamento = 0,
  n_max_complexidade  = 999,
  trace = TRUE
)


