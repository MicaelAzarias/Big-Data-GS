-- Consultas que o MVP (app Em Raízes) faz nas tabelas entregues pelo pipeline.
-- Servem também como evidência de "dados carregados".

-- 1) Painel de alertas: setores em ordem de prioridade de atendimento
SELECT prioridade, setor, classe_setor, risco_medio_agora, risco_medio_24h,
       casas, moradores_em_risco_alto, vazamentos, fissuras
FROM mart_risco_setor
WHERE voo_id = (SELECT MAX(voo_id) FROM dim_voo)
ORDER BY prioridade;

-- 2) Mapa de calor: risco de cada célula do último voo
SELECT c.linha, c.coluna, f.risco_agora, f.classe_agora, f.casas
FROM fato_medicao_celula f
JOIN dim_celula c ON c.celula_id = f.celula_id
WHERE f.voo_id = (SELECT MAX(voo_id) FROM dim_voo)
ORDER BY c.linha, c.coluna;

-- 3) Lista de vistoria: células com casas em risco alto ou crítico
SELECT f.celula_id, s.setor, f.risco_agora, f.casas, f.moradores_estimados,
       f.tem_vazamento, f.fissura_detectada
FROM fato_medicao_celula f
JOIN dim_celula c ON c.celula_id = f.celula_id
JOIN dim_setor  s ON s.setor_id = c.setor_id
WHERE f.classe_agora IN ('Alto', 'Crítico') AND f.casas > 0
ORDER BY f.risco_agora DESC;

-- 4) Plano de plantio de capim-vetiver por setor
SELECT s.setor, COUNT(*) AS celulas, SUM(f.mudas_sugeridas) AS mudas
FROM fato_medicao_celula f
JOIN dim_celula c ON c.celula_id = f.celula_id
JOIN dim_setor  s ON s.setor_id = c.setor_id
WHERE f.plantar_capim
GROUP BY s.setor
ORDER BY mudas DESC;

-- 5) Monitoramento do modelo de visão: acerto por tipo de solo
SELECT tipo_solo_amostra, n_celulas, acertos, acuracia, confianca_media
FROM mart_avaliacao_visao
ORDER BY acuracia;

-- 6) Auditoria: resultado das regras de qualidade da última carga
SELECT severidade, regra, passou, linhas_com_falha, detalhe
FROM log_qualidade
WHERE NOT passou;
