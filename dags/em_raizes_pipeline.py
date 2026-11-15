"""DAG do Airflow: pipeline de dados do MVP Em Raízes.

    ingestao_bronze -> tratamento_silver -> validacao_qualidade
                    -> modelagem_gold -> carga_warehouse -> verificacao_final

Cada tarefa só chama uma função do pacote `em_raizes` (a lógica fica lá, o DAG
só orquestra). As tarefas trocam entre si apenas o CAMINHO da partição gerada
(via XCom), nunca os dados em si.
"""
from datetime import datetime, timedelta

from airflow.decorators import dag, task

from em_raizes import bronze, carga, gold, qualidade, silver


@dag(
    dag_id="em_raizes_pipeline",
    description="Voo do drone (xlsx) -> bronze -> silver -> qualidade -> gold -> warehouse",
    schedule="@daily",                 # um processamento por dia
    start_date=datetime(2026, 11, 1),
    catchup=False,                     # não reprocessa dias passados ao ligar
    max_active_runs=1,
    default_args={
        "owner": "em-raizes",
        "retries": 1,                  # se falhar, tenta mais uma vez
        "retry_delay": timedelta(minutes=1),
    },
    tags=["em-raizes", "citizentech", "etl"],
)
def em_raizes_pipeline():
    @task
    def ingestao_bronze(ds=None) -> str:
        """Extrai o Excel da fonte e grava CSV bruto em bronze/dt=<data>."""
        return bronze.ingerir(ds)  # ds = data lógica da execução (AAAA-MM-DD)

    @task
    def tratamento_silver(dir_bronze: str) -> str:
        """Padroniza nomes, tipos e textos; extrai metadados do voo."""
        return silver.tratar(dir_bronze)

    @task(retries=0)  # dado ruim não melhora tentando de novo
    def validacao_qualidade(dir_silver: str) -> str:
        """Aplica as regras de qualidade; reprova a execução se houver erro."""
        return qualidade.validar(dir_silver)

    @task
    def modelagem_gold(dir_silver: str) -> str:
        """Monta dimensões, fato e marts (esquema estrela) em Parquet."""
        return gold.modelar(dir_silver)

    @task
    def carga_warehouse(dir_gold: str) -> dict:
        """Carrega a gold no banco do MVP, de forma idempotente."""
        return carga.carregar(dir_gold)

    @task
    def verificacao_final(carregadas: dict) -> dict:
        """Confere contagens e integridade direto no banco."""
        return carga.verificar(carregadas)

    dir_bronze = ingestao_bronze()
    dir_silver = tratamento_silver(dir_bronze)
    dir_validado = validacao_qualidade(dir_silver)
    dir_gold = modelagem_gold(dir_validado)
    carregadas = carga_warehouse(dir_gold)
    verificacao_final(carregadas)


em_raizes_pipeline()
