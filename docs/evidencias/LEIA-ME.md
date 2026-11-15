# Evidências de execução

## O que já está aqui

- `log_airflow_dags_test.txt` — log completo de uma execução do DAG com
  `airflow dags test em_raizes_pipeline 2026-11-15` (Airflow 2.10.5, banco SQLite).
  As seis tarefas terminam em SUCCESS.

## Prints que a equipe precisa tirar (rodando a Opção A do README)

Salve nesta pasta com estes nomes:

1. `01_dag_graph.png` — Airflow, DAG `em_raizes_pipeline`, aba **Graph**, seis tarefas verdes.
2. `02_dag_grid.png` — aba **Grid**, mostrando a execução com sucesso e a duração.
3. `03_log_qualidade.png` — **Logs** da tarefa `validacao_qualidade` (lista das regras, "32 regras | 0 erros | 4 avisos").
4. `04_log_verificacao.png` — **Logs** da tarefa `verificacao_final` (contagens por tabela e "integridade OK").
5. `05_tabelas_postgres.png` — terminal com o resultado de `\dt` e da consulta em `mart_risco_setor` (comandos no README).

Se preferirem vídeo: grave a tela do passo "Trigger DAG" até as tarefas ficarem
verdes e termine mostrando a consulta no banco. Um a dois minutos bastam.
