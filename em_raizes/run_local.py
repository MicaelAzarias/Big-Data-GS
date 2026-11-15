"""Roda o pipeline inteiro SEM Airflow (útil para testar rápido).

    python -m em_raizes.run_local              # usa a data de hoje
    python -m em_raizes.run_local 2026-11-15   # ou uma data específica

As funções chamadas aqui são exatamente as mesmas que o DAG do Airflow chama.
"""
import logging
import sys
from datetime import date

from em_raizes import bronze, carga, gold, qualidade, silver


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
    data_execucao = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()

    dir_bronze = bronze.ingerir(data_execucao)
    dir_silver = silver.tratar(dir_bronze)
    dir_silver = qualidade.validar(dir_silver)
    dir_gold = gold.modelar(dir_silver)
    carregadas = carga.carregar(dir_gold)
    carga.verificar(carregadas)
    logging.info("Pipeline concluído com sucesso.")


if __name__ == "__main__":
    main()
