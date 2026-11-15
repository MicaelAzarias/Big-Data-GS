"""Portão de QUALIDADE entre a silver e a gold.

Cada regra tem uma severidade:
  ERRO  -> o dado está errado; o pipeline PARA e nada chega ao MVP.
  AVISO -> merece atenção, mas não impede o uso (fica registrado no log e
           na tabela log_qualidade).
"""
import json
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

SOLOS = {"argiloso", "siltoso", "arenoso", "aterro", "rochoso"}
CLASSES = {"Baixo", "Moderado", "Alto", "Crítico"}
TENDENCIAS = {"subindo", "estavel", "caindo"}

# (coluna, mínimo, máximo) — limites físicos de cada medida
FAIXAS = [
    ("inclinacao_graus", 0, 90),
    ("umidade_solo_pct", 0, 100),
    ("vegetacao_fracao", 0, 1),
    ("erosao_indice", 0, 1),
    ("prob_fissura", 0, 1),
    ("confianca_visao", 0, 1),
    ("risco_agora", 0, 100),
    ("risco_24h", 0, 100),
    ("casas", 0, 50),
    ("mudas_sugeridas", 0, 10_000),
    ("agua_sugerida_l", 0, 100_000),
]


def classificar_risco(risco: pd.Series) -> pd.Series:
    """Regra de negócio do dicionário: Baixo <30, Moderado 30–54, Alto 55–74, Crítico >=75."""
    return pd.cut(
        risco,
        bins=[-float("inf"), 30, 55, 75, float("inf")],
        labels=["Baixo", "Moderado", "Alto", "Crítico"],
        right=False,
    ).astype(str)


def validar(dir_silver: str) -> str:
    """Roda todas as regras, grava qualidade.csv na silver e levanta erro se
    alguma regra de severidade ERRO falhar. Devolve o caminho da silver."""
    silver = Path(dir_silver)
    df = pd.read_parquet(silver / "medicoes_celula.parquet")
    voo = json.loads((silver / "voo.json").read_text(encoding="utf-8"))
    resultados = []

    def checar(regra: str, severidade: str, n_falhas: int, detalhe: str = ""):
        resultados.append(
            {
                "voo_id": voo["voo_id"],
                "regra": regra,
                "severidade": severidade,
                "passou": bool(n_falhas == 0),
                "linhas_com_falha": int(n_falhas),
                "detalhe": detalhe,
            }
        )

    # ---- estrutura e chaves -------------------------------------------------
    checar("tabela_nao_vazia", "ERRO", 0 if len(df) > 0 else 1)
    checar("sem_valores_nulos", "ERRO", int(df.isna().any(axis=1).sum()))
    checar("celula_id_unica", "ERRO", int(df["celula_id"].duplicated().sum()))
    esperado = (
        "L" + df["linha"].astype(str).str.zfill(2)
        + "C" + df["coluna"].astype(str).str.zfill(2)
    )
    checar("celula_id_bate_com_linha_coluna", "ERRO", int((df["celula_id"] != esperado).sum()))
    n_lin, n_col = df["linha"].nunique(), df["coluna"].nunique()
    checar(
        "grade_completa", "ERRO", abs(n_lin * n_col - len(df)),
        f"{n_lin} linhas x {n_col} colunas = {n_lin * n_col} células; recebidas {len(df)}",
    )

    # ---- faixas válidas -------------------------------------------------------
    for col, minimo, maximo in FAIXAS:
        fora = int((~df[col].between(minimo, maximo)).sum())
        checar(f"faixa_{col}", "ERRO", fora, f"esperado entre {minimo} e {maximo}")

    # ---- domínios (valores permitidos) ------------------------------------------
    checar("dominio_tipo_solo_amostra", "ERRO", int((~df["tipo_solo_amostra"].isin(SOLOS)).sum()))
    checar("dominio_tipo_solo_visao", "ERRO", int((~df["tipo_solo_visao"].isin(SOLOS)).sum()))
    checar("dominio_classe_agora", "ERRO", int((~df["classe_agora"].isin(CLASSES)).sum()))
    checar("dominio_classe_24h", "ERRO", int((~df["classe_24h"].isin(CLASSES)).sum()))
    checar("dominio_tendencia", "ERRO", int((~df["tendencia"].isin(TENDENCIAS)).sum()))

    # ---- coerência com as regras de negócio do dicionário -------------------------
    checar(
        "classe_agora_coerente_com_risco", "ERRO",
        int((classificar_risco(df["risco_agora"]) != df["classe_agora"]).sum()),
        "Baixo <30, Moderado 30–54, Alto 55–74, Crítico >=75",
    )
    checar(
        "classe_24h_coerente_com_risco", "ERRO",
        int((classificar_risco(df["risco_24h"]) != df["classe_24h"]).sum()),
    )
    checar(
        "moradores_igual_casas_x_2_8", "ERRO",
        int(((df["moradores_estimados"] - df["casas"] * 2.8).abs() > 0.05).sum()),
    )
    checar(
        "fissura_detectada_quando_prob_maior_55", "ERRO",
        int(((df["prob_fissura"] > 0.55) != df["fissura_detectada"]).sum()),
    )
    checar(
        "plantio_so_sem_casas_e_sem_rocha", "ERRO",
        int((df["plantar_capim"] & ((df["casas"] > 0) | (df["tipo_solo_amostra"] == "rochoso"))).sum()),
    )
    checar(
        "mudas_so_onde_ha_plantio", "ERRO",
        int(((df["mudas_sugeridas"] > 0) != df["plantar_capim"]).sum()),
    )

    # ---- avisos (não bloqueiam) ---------------------------------------------------
    n_neg = int((df["altitude_m"] < 0).sum())
    checar(
        "altitude_negativa", "AVISO", n_neg,
        "altitude é relativa à base do morro; valores < 0 ficam abaixo da rua",
    )
    erro_visao = float((df["tipo_solo_visao"] != df["tipo_solo_amostra"]).mean())
    checar(
        "erro_visao_ate_20_pct", "AVISO", 0 if erro_visao <= 0.20 else int(erro_visao * len(df)),
        f"visão errou o tipo de solo em {erro_visao:.1%} das células (esperado ~12%)",
    )
    for col in ["tendencia", "irrigar", "agua_sugerida_l"]:
        constante = df[col].nunique() == 1
        checar(
            f"coluna_sem_variacao_{col}", "AVISO", len(df) if constante else 0,
            f"único valor neste voo: {df[col].iloc[0]}" if constante else "",
        )

    # ---- resultado ---------------------------------------------------------------
    relatorio = pd.DataFrame(resultados)
    relatorio.to_csv(silver / "qualidade.csv", index=False, encoding="utf-8")

    for r in resultados:
        situacao = "OK   " if r["passou"] else ("FALHA" if r["severidade"] == "ERRO" else "AVISO")
        log.info("qualidade: [%s] %-42s %s", situacao, r["regra"], r["detalhe"])

    erros = relatorio[(relatorio["severidade"] == "ERRO") & (~relatorio["passou"])]
    avisos = relatorio[(relatorio["severidade"] == "AVISO") & (~relatorio["passou"])]
    log.info(
        "qualidade: %d regras | %d erros | %d avisos",
        len(relatorio), len(erros), len(avisos),
    )
    if len(erros) > 0:
        raise ValueError(
            "Dados reprovados na qualidade. Regras com falha: "
            + ", ".join(erros["regra"].tolist())
        )
    return str(silver)
