# Dicionário de dados — tabelas entregues pelo pipeline

## dim_voo

**Dimensão** · Um registro por voo do drone (uma geração do simulador), com a chuva considerada e a linhagem do arquivo de origem.

- Grão: 1 linha por voo
- Chave primária: `voo_id`

| Coluna | Tipo | Descrição | Origem |
|---|---|---|---|
| `voo_id` | VARCHAR(30) | Identificador do voo: 'voo_' + data e hora da geração (ex.: voo_20261110_1925). | Pipeline |
| `gerado_em` | TIMESTAMP | Data e hora em que o simulador gerou os dados (horário de Brasília). | Simulado |
| `semente` | INTEGER | Semente aleatória do simulador; a mesma semente gera o mesmo morro. | Simulado |
| `chuva_72h_mm` | DOUBLE | Chuva acumulada nas últimas 72 h, em mm (percentil 75 dos pluviômetros ativos do Cemaden). | Real |
| `chuva_prevista_24h_mm` | DOUBLE | Chuva prevista para as próximas 24 h, em mm (Open-Meteo). | Real |
| `chuva_e_real` | BOOLEAN | Verdadeiro quando a chuva veio das fontes reais, e não de valor simulado. | Pipeline |
| `local_chuva` | VARCHAR(80) | Cidade/UF de onde a chuva foi lida (ex.: Petrópolis/RJ). | Real |
| `descricao_area` | VARCHAR(200) | Descrição da área mapeada (tamanho da grade e das células). | Simulado |
| `arquivo_origem` | VARCHAR(200) | Nome do arquivo ingerido. | Pipeline |
| `sha256_origem` | CHAR(64) | Hash SHA-256 do arquivo ingerido; prova qual versão do arquivo gerou os dados. | Pipeline |
| `ingerido_em_utc` | TIMESTAMP | Data e hora (UTC) em que o pipeline ingeriu o arquivo. | Pipeline |
| `n_celulas` | INTEGER | Quantidade de células medidas no voo; usada na verificação final da carga. | Pipeline |

## dim_setor

**Dimensão** · As 9 regiões do morro (grade 3 x 3) usadas para agrupar alertas.

- Grão: 1 linha por setor
- Chave primária: `setor_id`

| Coluna | Tipo | Descrição | Origem |
|---|---|---|---|
| `setor_id` | INTEGER | Identificador de 1 a 9, do topo para a base e de oeste para leste. | Pipeline |
| `setor` | VARCHAR(30) | Nome do setor (ex.: Meio-Leste). | Simulado |
| `faixa_altura` | VARCHAR(10) | Posição vertical no morro: Alto, Meio ou Baixo. | Pipeline |
| `faixa_lateral` | VARCHAR(10) | Posição horizontal no morro: Oeste, Centro ou Leste. | Pipeline |

## dim_celula

**Dimensão** · Cada quadradinho de 10 m x 10 m do morro, com as características do terreno que não mudam de um voo para outro.

- Grão: 1 linha por célula
- Chave primária: `celula_id`

| Coluna | Tipo | Descrição | Origem |
|---|---|---|---|
| `celula_id` | CHAR(6) | Código da célula: L + linha, C + coluna (ex.: L05C12). | Simulado |
| `linha` | INTEGER | Linha da grade. 0 = topo do morro; 23 = base (rua). | Simulado |
| `coluna` | INTEGER | Coluna da grade, de 0 (oeste) a 23 (leste). | Simulado |
| `setor_id` | INTEGER | Setor a que a célula pertence. FK para dim_setor. | Pipeline |
| `altitude_m` | DOUBLE | Altura do terreno em relação à base do morro, em metros (pode ser negativa abaixo da rua). | Simulado |
| `inclinacao_graus` | DOUBLE | Inclinação do terreno em graus (0 a 90). | Simulado |
| `tipo_solo_amostra` | VARCHAR(20) | Tipo de solo de referência (amostra de campo): argiloso, siltoso, arenoso, aterro ou rochoso. | Simulado |

## fato_medicao_celula

**Fato** · O que foi medido pelo drone e calculado pelo sistema em cada célula, em cada voo. É a tabela central do modelo.

- Grão: 1 linha por célula por voo
- Chave primária: `voo_id + celula_id`

| Coluna | Tipo | Descrição | Origem |
|---|---|---|---|
| `voo_id` | VARCHAR(30) | Voo da medição. FK para dim_voo. | Pipeline |
| `celula_id` | CHAR(6) | Célula medida. FK para dim_celula. | Simulado |
| `umidade_solo_pct` | DOUBLE | Umidade volumétrica do solo em % (0 a 100). 45% = solo encharcado. | Simulado |
| `vegetacao_fracao` | DOUBLE | Fração da célula coberta por vegetação, de 0 a 1 (tipo NDVI). | Simulado |
| `casas` | INTEGER | Número de casas detectadas na célula. | Simulado |
| `moradores_estimados` | DOUBLE | Casas x 2,8 moradores por casa (média do Censo IBGE 2022). | Calculado |
| `tem_vazamento` | BOOLEAN | Vazamento de água ou esgoto detectado pela câmera térmica. | Simulado |
| `erosao_indice` | DOUBLE | Intensidade de erosão visível, de 0 a 1. | Simulado |
| `prob_fissura` | DOUBLE | Probabilidade de fissura no terreno segundo a visão computacional, de 0 a 1. | Simulado |
| `fissura_detectada` | BOOLEAN | Verdadeiro quando prob_fissura passa de 0,55. | Simulado |
| `tipo_solo_visao` | VARCHAR(20) | Tipo de solo previsto pela visão computacional. | Simulado |
| `confianca_visao` | DOUBLE | Confiança da previsão do tipo de solo, de 0 a 1. | Simulado |
| `visao_acertou_solo` | BOOLEAN | Verdadeiro quando tipo_solo_visao é igual ao tipo_solo_amostra da célula. | Pipeline |
| `risco_agora` | DOUBLE | Índice de risco de deslizamento de 0 a 100 (6 fatores ponderados; pesos ilustrativos). | Calculado |
| `classe_agora` | VARCHAR(10) | Baixo (<30), Moderado (30–54), Alto (55–74) ou Crítico (>=75). | Calculado |
| `risco_24h` | DOUBLE | O mesmo índice somando a chuva prevista para as próximas 24 h. | Calculado |
| `classe_24h` | VARCHAR(10) | Classe do risco previsto para 24 h. | Calculado |
| `tendencia` | VARCHAR(10) | subindo, estavel ou caindo, comparando o risco agora e em 24 h. | Calculado |
| `plantar_capim` | BOOLEAN | Recomendação de plantio de capim-vetiver (sem casas, sem rocha, pouca vegetação). | Calculado |
| `mudas_sugeridas` | INTEGER | Quantidade de mudas de capim-vetiver sugerida para a célula. | Calculado |
| `irrigar` | BOOLEAN | Recomendação de irrigação (solo seco, sem casas, risco baixo/moderado, sem chuva prevista). | Calculado |
| `agua_sugerida_l` | INTEGER | Litros de água sugeridos para as faixas plantadas. | Calculado |

## mart_risco_setor

**Mart (consumo do app)** · Resumo do risco por setor, pronto para a tela de alertas do MVP. Evita que o app agregue 576 células a cada consulta.

- Grão: 1 linha por setor por voo
- Chave primária: `voo_id + setor_id`

| Coluna | Tipo | Descrição | Origem |
|---|---|---|---|
| `voo_id` | VARCHAR(30) | Voo do resumo. FK para dim_voo. | Pipeline |
| `setor_id` | INTEGER | Setor resumido. FK para dim_setor. | Pipeline |
| `setor` | VARCHAR(30) | Nome do setor (repetido aqui para o app não precisar de JOIN). | Pipeline |
| `prioridade` | INTEGER | Ordem de atendimento: 1 = setor com mais moradores em células de risco alto/crítico (desempate: maior risco médio). | Pipeline |
| `classe_setor` | VARCHAR(10) | Classe do risco médio do setor, pelas mesmas faixas da célula. | Pipeline |
| `n_celulas` | INTEGER | Células do setor. | Pipeline |
| `risco_medio_agora` | DOUBLE | Média de risco_agora das células do setor. | Pipeline |
| `risco_maximo_agora` | DOUBLE | Maior risco_agora entre as células do setor. | Pipeline |
| `risco_medio_24h` | DOUBLE | Média de risco_24h das células do setor. | Pipeline |
| `celulas_risco_alto` | INTEGER | Células com classe Alto ou Crítico. | Pipeline |
| `pct_celulas_risco_alto` | DOUBLE | Percentual das células do setor em classe Alto ou Crítico. | Pipeline |
| `casas` | INTEGER | Total de casas no setor. | Pipeline |
| `moradores_estimados` | DOUBLE | Total de moradores estimados no setor. | Pipeline |
| `moradores_em_risco_alto` | DOUBLE | Moradores estimados em células de classe Alto ou Crítico. | Pipeline |
| `vazamentos` | INTEGER | Células com vazamento detectado. | Pipeline |
| `fissuras` | INTEGER | Células com fissura detectada. | Pipeline |
| `celulas_para_plantio` | INTEGER | Células com recomendação de plantio. | Pipeline |
| `mudas_sugeridas` | INTEGER | Total de mudas sugeridas no setor. | Pipeline |

## mart_avaliacao_visao

**Mart (consumo de IA)** · Compara o tipo de solo previsto pela visão computacional com a amostra de campo. Alimenta o monitoramento do modelo de IA.

- Grão: 1 linha por tipo de solo por voo
- Chave primária: `voo_id + tipo_solo_amostra`

| Coluna | Tipo | Descrição | Origem |
|---|---|---|---|
| `voo_id` | VARCHAR(30) | Voo avaliado. FK para dim_voo. | Pipeline |
| `tipo_solo_amostra` | VARCHAR(20) | Tipo de solo verdadeiro (amostra de campo). | Simulado |
| `n_celulas` | INTEGER | Células com esse tipo de solo. | Pipeline |
| `acertos` | INTEGER | Células em que a visão previu o tipo correto. | Pipeline |
| `acuracia` | DOUBLE | acertos / n_celulas, de 0 a 1. | Pipeline |
| `confianca_media` | DOUBLE | Média da confiança declarada pela visão nessas células. | Pipeline |

## log_qualidade

**Auditoria** · Resultado de cada regra de qualidade aplicada na carga de um voo.

- Grão: 1 linha por regra por voo
- Chave primária: `voo_id + regra`

| Coluna | Tipo | Descrição | Origem |
|---|---|---|---|
| `voo_id` | VARCHAR(30) | Voo validado. FK para dim_voo. | Pipeline |
| `regra` | VARCHAR(60) | Nome da regra (ex.: faixa_umidade_solo_pct). | Pipeline |
| `severidade` | VARCHAR(5) | ERRO (bloqueia a carga) ou AVISO (só registra). | Pipeline |
| `passou` | BOOLEAN | Verdadeiro quando nenhuma linha violou a regra. | Pipeline |
| `linhas_com_falha` | INTEGER | Quantidade de linhas que violaram a regra. | Pipeline |
| `detalhe` | VARCHAR(200) | Explicação ou valor observado. | Pipeline |
