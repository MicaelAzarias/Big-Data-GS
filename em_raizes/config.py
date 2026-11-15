"""Configuração central do pipeline.

Tudo que muda de ambiente para ambiente (pastas, banco) vem de variáveis de
ambiente. Assim o MESMO código roda no Airflow (Docker + Postgres) e na
máquina local (SQLite), sem editar nada.
"""
import os
from pathlib import Path

# Raiz do repositório (pasta que contém em_raizes/, dags/, data/ ...)
RAIZ = Path(os.getenv("EMRAIZES_HOME", Path(__file__).resolve().parents[1]))

# Data lake local, organizado em camadas (arquitetura medalhão)
DATA_DIR = Path(os.getenv("EMRAIZES_DATA_DIR", RAIZ / "data"))
DIR_RAW = DATA_DIR / "raw"        # zona de pouso: arquivo como chegou da fonte
DIR_BRONZE = DATA_DIR / "bronze"  # cópia fiel, só mudou o formato (CSV)
DIR_SILVER = DATA_DIR / "silver"  # limpo, tipado, validado (Parquet)
DIR_GOLD = DATA_DIR / "gold"      # modelo dimensional (Parquet)

# Arquivo de origem entregue pelo simulador do drone
ARQUIVO_FONTE = Path(
    os.getenv("EMRAIZES_FONTE", DIR_RAW / "dados_simulados_em_raizes.xlsx")
)

# Banco que o MVP consulta. Padrão: SQLite local. No Docker: Postgres.
WAREHOUSE_URL = os.getenv(
    "EMRAIZES_WAREHOUSE_URL",
    f"sqlite:///{DATA_DIR / 'warehouse' / 'em_raizes.db'}",
)

# Arquivo com o CREATE TABLE das tabelas finais
ARQUIVO_DDL = RAIZ / "sql" / "ddl_warehouse.sql"
