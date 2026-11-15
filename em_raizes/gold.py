"""Camada GOLD — modelagem.

Transforma a tabela única da silver em um modelo dimensional (esquema estrela)
mais duas tabelas prontas para consumo (marts):

  dim_voo               quando o drone voou e com que chuva
  dim_setor             as 9 regiões do morro
  dim_celula            cada quadradinho de 10 m x 10 m (terreno, não muda entre voos)
  fato_medicao_celula   o que foi medido/calculado em cada célula em cada voo
  mart_risco_setor      resumo por setor -> alimenta os alertas do app
  mart_avaliacao_visao  acerto da visão computacional -> monitora o modelo de IA
  log_qualidade         resultado das regras de qualidade de cada carga
"""
import json
import logging
from pathlib import Path

import pandas as pd

from em_raizes import config
from em_raizes.qualidade import classificar_risco

log = logging.getLogger(__name__)

ORDEM_FAIXA = ["Alto", "Meio", "Baixo"]
ORDEM_LADO = ["Oeste", "Centro", "Leste"]


def _dim_voo(voo: dict, n_celulas: int) -> pd.DataFrame:
    return pd.DataFrame([{**voo, "n_celulas": n_celulas}])


def _dim_setor(df: pd.DataFrame) -> pd.DataFrame:
    setores = df[["setor"]].drop_duplicates().copy()
    partes = setores["setor"].str.split("-", expand=True)
    setores["faixa_altura"] = partes[0]   # Alto / Meio / Baixo
    setores["faixa_lateral"] = partes[1]  # Oeste / Centro / Leste
    # id estável: 1..9, de cima para baixo e de oeste para leste
    setores["setor_id"] = (
        setores["faixa_altura"].map(ORDEM_FAIXA.index) * 3
        + setores["faixa_lateral"].map(ORDEM_LADO.index)
        + 1
    ).astype("int64")
    return setores.sort_values("setor_id")[
        ["setor_id", "setor", "faixa_altura", "faixa_lateral"]
    ].reset_index(drop=True)


def _dim_celula(df: pd.DataFrame, dim_setor: pd.DataFrame) -> pd.DataFrame:
    celulas = df.merge(dim_setor[["setor_id", "setor"]], on="setor", how="left")
    return celulas[
        ["celula_id", "linha", "coluna", "setor_id",
         "altitude_m", "inclinacao_graus", "tipo_solo_amostra"]
    ]


def _fato(df: pd.DataFrame) -> pd.DataFrame:
    fato = df[
        ["voo_id", "celula_id", "umidade_solo_pct", "vegetacao_fracao", "casas",
         "moradores_estimados", "tem_vazamento", "erosao_indice", "prob_fissura",
         "fissura_detectada", "tipo_solo_visao", "confianca_visao",
         "risco_agora", "classe_agora", "risco_24h", "classe_24h", "tendencia",
         "plantar_capim", "mudas_sugeridas", "irrigar", "agua_sugerida_l"]
    ].copy()
    # coluna derivada: a visão acertou o tipo de solo da amostra de campo?
    posicao = fato.columns.get_loc("confianca_visao") + 1
    fato.insert(posicao, "visao_acertou_solo", df["tipo_solo_visao"] == df["tipo_solo_amostra"])
    return fato


def _mart_risco_setor(df: pd.DataFrame, dim_setor: pd.DataFrame) -> pd.DataFrame:
    base = df.assign(
        em_risco_alto=df["classe_agora"].isin(["Alto", "Crítico"]),
        moradores_risco=df["moradores_estimados"].where(
            df["classe_agora"].isin(["Alto", "Crítico"]), 0.0
        ),
    )
    mart = (
        base.groupby(["voo_id", "setor"], as_index=False)
        .agg(
            n_celulas=("celula_id", "count"),
            risco_medio_agora=("risco_agora", "mean"),
            risco_maximo_agora=("risco_agora", "max"),
            risco_medio_24h=("risco_24h", "mean"),
            celulas_risco_alto=("em_risco_alto", "sum"),
            casas=("casas", "sum"),
            moradores_estimados=("moradores_estimados", "sum"),
            moradores_em_risco_alto=("moradores_risco", "sum"),
            vazamentos=("tem_vazamento", "sum"),
            fissuras=("fissura_detectada", "sum"),
            celulas_para_plantio=("plantar_capim", "sum"),
            mudas_sugeridas=("mudas_sugeridas", "sum"),
        )
        .merge(dim_setor[["setor_id", "setor"]], on="setor")
    )
    for col in ["risco_medio_agora", "risco_maximo_agora", "risco_medio_24h",
                "moradores_estimados", "moradores_em_risco_alto"]:
        mart[col] = mart[col].round(1)
    for col in ["celulas_risco_alto", "vazamentos", "fissuras", "celulas_para_plantio"]:
        mart[col] = mart[col].astype("int64")
    mart["pct_celulas_risco_alto"] = (100 * mart["celulas_risco_alto"] / mart["n_celulas"]).round(1)
    mart["classe_setor"] = classificar_risco(mart["risco_medio_agora"])
    # prioridade de atendimento: 1 = setor com mais moradores em área de risco alto
    mart = mart.sort_values(
        ["moradores_em_risco_alto", "risco_medio_agora"], ascending=False
    ).reset_index(drop=True)
    mart["prioridade"] = mart.index + 1
    return mart[
        ["voo_id", "setor_id", "setor", "prioridade", "classe_setor", "n_celulas",
         "risco_medio_agora", "risco_maximo_agora", "risco_medio_24h",
         "celulas_risco_alto", "pct_celulas_risco_alto", "casas",
         "moradores_estimados", "moradores_em_risco_alto", "vazamentos",
         "fissuras", "celulas_para_plantio", "mudas_sugeridas"]
    ]


def _mart_avaliacao_visao(df: pd.DataFrame) -> pd.DataFrame:
    base = df.assign(acertou=df["tipo_solo_visao"] == df["tipo_solo_amostra"])
    mart = base.groupby(["voo_id", "tipo_solo_amostra"], as_index=False).agg(
        n_celulas=("celula_id", "count"),
        acertos=("acertou", "sum"),
        confianca_media=("confianca_visao", "mean"),
    )
    mart["acertos"] = mart["acertos"].astype("int64")
    mart["acuracia"] = (mart["acertos"] / mart["n_celulas"]).round(3)
    mart["confianca_media"] = mart["confianca_media"].round(3)
    return mart[
        ["voo_id", "tipo_solo_amostra", "n_celulas", "acertos", "acuracia", "confianca_media"]
    ]


def modelar(dir_silver: str) -> str:
    """Lê a silver validada e grava as 7 tabelas da gold em Parquet."""
    silver = Path(dir_silver)
    df = pd.read_parquet(silver / "medicoes_celula.parquet")
    voo = json.loads((silver / "voo.json").read_text(encoding="utf-8"))
    qualidade = pd.read_csv(silver / "qualidade.csv", keep_default_na=False)

    dim_setor = _dim_setor(df)
    tabelas = {
        "dim_voo": _dim_voo(voo, len(df)),
        "dim_setor": dim_setor,
        "dim_celula": _dim_celula(df, dim_setor),
        "fato_medicao_celula": _fato(df),
        "mart_risco_setor": _mart_risco_setor(df, dim_setor),
        "mart_avaliacao_visao": _mart_avaliacao_visao(df),
        "log_qualidade": qualidade,
    }

    destino = config.DIR_GOLD / silver.name
    destino.mkdir(parents=True, exist_ok=True)
    for nome, tabela in tabelas.items():
        tabela.to_parquet(destino / f"{nome}.parquet", index=False)
        log.info("gold: %-22s %4d linhas, %2d colunas", nome, len(tabela), tabela.shape[1])
    return str(destino)
