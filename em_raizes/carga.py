"""CARGA no banco (warehouse) que o MVP consulta.

A carga é idempotente: rodar o pipeline de novo para o mesmo voo NÃO duplica
linhas. Para isso:
  - dimensões usam UPSERT (insere; se a chave já existe, atualiza);
  - fatos e marts apagam as linhas daquele voo e inserem de novo.
Tudo dentro de UMA transação: ou entra tudo, ou não entra nada.
"""
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from em_raizes import config

log = logging.getLogger(__name__)

# ordem de carga respeita as chaves estrangeiras (dimensões antes dos fatos)
# tabela -> (chave primária, é particionada por voo?)
TABELAS = {
    "dim_voo": (["voo_id"], False),
    "dim_setor": (["setor_id"], False),
    "dim_celula": (["celula_id"], False),
    "fato_medicao_celula": (["voo_id", "celula_id"], True),
    "mart_risco_setor": (["voo_id", "setor_id"], True),
    "mart_avaliacao_visao": (["voo_id", "tipo_solo_amostra"], True),
    "log_qualidade": (["voo_id", "regra"], True),
}


def _engine():
    url = config.WAREHOUSE_URL
    if url.startswith("sqlite:///"):
        Path(url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url)


def _criar_tabelas(conn) -> None:
    ddl = config.ARQUIVO_DDL.read_text(encoding="utf-8")
    sem_comentarios = "\n".join(
        linha for linha in ddl.splitlines() if not linha.strip().startswith("--")
    )
    for comando in sem_comentarios.split(";"):
        if comando.strip():
            conn.execute(text(comando))


def _registros(df: pd.DataFrame) -> list:
    """DataFrame -> lista de dicts com tipos nativos do Python (o driver do
    banco não entende tipos do numpy) e None no lugar de NaN."""
    return [
        {
            coluna: (None if pd.isna(valor) else valor.item() if hasattr(valor, "item") else valor)
            for coluna, valor in linha.items()
        }
        for linha in df.to_dict("records")
    ]


def _upsert(conn, tabela: str, df: pd.DataFrame, chave: list) -> None:
    colunas = list(df.columns)
    demais = [c for c in colunas if c not in chave]
    sql = (
        f"INSERT INTO {tabela} ({', '.join(colunas)}) "
        f"VALUES ({', '.join(':' + c for c in colunas)}) "
        f"ON CONFLICT ({', '.join(chave)}) DO UPDATE SET "
        + ", ".join(f"{c} = EXCLUDED.{c}" for c in demais)
    )
    conn.execute(text(sql), _registros(df))


def carregar(dir_gold: str) -> dict:
    """Carrega os Parquet da gold no banco. Devolve {tabela: linhas carregadas}."""
    gold = Path(dir_gold)
    carregadas = {}
    engine = _engine()
    with engine.begin() as conn:  # transação única
        _criar_tabelas(conn)
        voo_id = pd.read_parquet(gold / "dim_voo.parquet")["voo_id"].iloc[0]

        # limpa as linhas deste voo (na ordem inversa, por causa das FKs)
        for tabela, (_, por_voo) in reversed(list(TABELAS.items())):
            if por_voo:
                conn.execute(text(f"DELETE FROM {tabela} WHERE voo_id = :v"), {"v": voo_id})

        for tabela, (chave, _) in TABELAS.items():
            df = pd.read_parquet(gold / f"{tabela}.parquet")
            _upsert(conn, tabela, df, chave)
            carregadas[tabela] = len(df)
            log.info("carga: %-22s %4d linhas", tabela, len(df))
    engine.dispose()
    log.info("carga: voo %s carregado em %s", voo_id, config.WAREHOUSE_URL.split("@")[-1])
    return carregadas


def verificar(carregadas: dict) -> dict:
    """Confere, direto no banco, se o que foi carregado está íntegro."""
    engine = _engine()
    with engine.connect() as conn:
        def um(sql: str) -> int:
            return int(conn.execute(text(sql)).scalar())

        contagem = {t: um(f"SELECT COUNT(*) FROM {t}") for t in TABELAS}
        for tabela, n in contagem.items():
            log.info("verificacao: %-22s %4d linhas no banco", tabela, n)
            if n < carregadas[tabela]:
                raise ValueError(f"{tabela}: banco tem {n} linhas, esperava >= {carregadas[tabela]}")

        divergentes = um(
            "SELECT COUNT(*) FROM dim_voo v WHERE v.n_celulas <> "
            "(SELECT COUNT(*) FROM fato_medicao_celula f WHERE f.voo_id = v.voo_id)"
        )
        orfas = um(
            "SELECT COUNT(*) FROM fato_medicao_celula f "
            "LEFT JOIN dim_celula c ON c.celula_id = f.celula_id "
            "WHERE c.celula_id IS NULL"
        )
        if divergentes or orfas:
            raise ValueError(
                f"Integridade quebrada: {divergentes} voo(s) com contagem divergente, "
                f"{orfas} medição(ões) sem célula"
            )
        log.info("verificacao: integridade OK (fato x dim_voo, fato x dim_celula)")

        pior = conn.execute(text(
            "SELECT setor, classe_setor, risco_medio_agora, moradores_em_risco_alto "
            "FROM mart_risco_setor ORDER BY voo_id DESC, prioridade LIMIT 3"
        )).fetchall()
        for setor, classe, risco, moradores in pior:
            log.info(
                "verificacao: prioridade -> %-13s classe %-9s risco médio %5.1f | %5.1f moradores em risco alto",
                setor, classe, risco, moradores,
            )
    engine.dispose()
    return contagem
