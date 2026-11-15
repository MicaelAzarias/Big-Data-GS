"""Camada BRONZE — ingestão.

Regra da camada: NÃO transformar. Só trazer o dado da fonte para dentro do
data lake, em formato aberto (CSV), e registrar de onde veio e quando.
Se algo der errado depois, dá para reprocessar a partir daqui sem depender
do arquivo original.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from em_raizes import config

log = logging.getLogger(__name__)

# aba do Excel -> nome do arquivo na bronze
ABAS = {"Sobre": "sobre.csv", "Dados": "dados.csv", "Dicionário": "dicionario.csv"}


def ingerir(data_execucao: str) -> str:
    """Lê o Excel da fonte e grava cada aba como CSV em bronze/dt=<data>/.

    A pasta é particionada pela data de execução. Rodar duas vezes no mesmo
    dia sobrescreve a mesma partição (idempotência).
    Devolve o caminho da partição criada.
    """
    fonte = config.ARQUIVO_FONTE
    if not fonte.exists():
        raise FileNotFoundError(f"Arquivo de origem não encontrado: {fonte}")

    destino = config.DIR_BRONZE / f"dt={data_execucao}"
    destino.mkdir(parents=True, exist_ok=True)

    linhas = {}
    with pd.ExcelFile(fonte) as excel:
        faltando = set(ABAS) - set(excel.sheet_names)
        if faltando:
            raise ValueError(f"Abas ausentes no arquivo de origem: {faltando}")
        for aba, arquivo in ABAS.items():
            # dtype=str: tudo entra como texto, sem o pandas "adivinhar" tipos.
            # A aba Sobre não tem cabeçalho (é um texto livre em duas colunas).
            df = excel.parse(aba, dtype=str, header=None if aba == "Sobre" else 0)
            df.to_csv(destino / arquivo, index=False, encoding="utf-8")
            linhas[arquivo] = len(df)
            log.info("bronze: aba '%s' -> %s (%d linhas)", aba, arquivo, len(df))

    # Manifesto = "etiqueta" do lote: origem, hash e horário (linhagem do dado)
    manifesto = {
        "arquivo_origem": fonte.name,
        "sha256": hashlib.sha256(fonte.read_bytes()).hexdigest(),
        "tamanho_bytes": fonte.stat().st_size,
        "ingerido_em_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "data_execucao": data_execucao,
        "linhas_por_arquivo": linhas,
    }
    (destino / "_manifesto.json").write_text(
        json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("bronze: manifesto gravado em %s", destino / "_manifesto.json")
    return str(destino)
