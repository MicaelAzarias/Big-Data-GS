"""Camada SILVER — tratamento.

Aqui o dado bruto vira dado confiável:
  1. nomes de coluna padronizados (snake_case, sem acento, com unidade no nome)
  2. tipos corretos (número é número, Sim/Não vira booleano)
  3. textos normalizados (minúsculas, sem espaço sobrando)
  4. remoção de duplicatas pela chave da célula
  5. metadados do voo (chuva, semente, data) extraídos da aba "Sobre"
"""
import json
import logging
import re
import unicodedata
from pathlib import Path

import pandas as pd

from em_raizes import config

log = logging.getLogger(__name__)

# nome original no Excel -> nome padronizado
RENOMEAR = {
    "Célula": "celula_id",
    "Linha": "linha",
    "Coluna": "coluna",
    "Setor": "setor",
    "Altitude (m)": "altitude_m",
    "Inclinação (°)": "inclinacao_graus",
    "Umidade do solo (%)": "umidade_solo_pct",
    "Vegetação": "vegetacao_fracao",
    "Tipo de solo (amostra)": "tipo_solo_amostra",
    "Casas": "casas",
    "Moradores (estim.)": "moradores_estimados",
    "Vazamento": "tem_vazamento",
    "Erosão (0 a 1)": "erosao_indice",
    "Prob. de fissura": "prob_fissura",
    "Fissura detectada": "fissura_detectada",
    "Tipo de solo (visão)": "tipo_solo_visao",
    "Confiança da visão": "confianca_visao",
    "Risco agora (0–100)": "risco_agora",
    "Classe agora": "classe_agora",
    "Risco em 24 h (0–100)": "risco_24h",
    "Classe em 24 h": "classe_24h",
    "Tendência": "tendencia",
    "Plantar capim?": "plantar_capim",
    "Mudas sugeridas": "mudas_sugeridas",
    "Irrigar?": "irrigar",
    "Água sugerida (L)": "agua_sugerida_l",
}

INTEIRAS = ["linha", "coluna", "casas", "mudas_sugeridas", "agua_sugerida_l"]
DECIMAIS = [
    "altitude_m", "inclinacao_graus", "umidade_solo_pct", "vegetacao_fracao",
    "moradores_estimados", "erosao_indice", "prob_fissura", "confianca_visao",
    "risco_agora", "risco_24h",
]
BOOLEANAS = ["tem_vazamento", "fissura_detectada", "plantar_capim", "irrigar"]
TEXTO_MINUSCULO = ["tipo_solo_amostra", "tipo_solo_visao", "tendencia"]
CLASSES = ["classe_agora", "classe_24h"]


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )


def _sim_nao(serie: pd.Series) -> pd.Series:
    """'Sim'/'Não' -> True/False. Qualquer outro valor é erro explícito."""
    limpo = serie.str.strip().str.lower().map(_sem_acento)
    invalidos = sorted(set(limpo.dropna()) - {"sim", "nao"})
    if invalidos:
        raise ValueError(f"Valores inesperados em {serie.name}: {invalidos}")
    return limpo == "sim"


def extrair_metadados_voo(sobre: pd.DataFrame) -> dict:
    """Lê a aba 'Sobre' (rótulo na 2ª coluna, valor na 3ª) e extrai os
    parâmetros do voo: quando foi gerado, semente e a chuva usada."""
    pares = {
        str(rotulo).strip(): str(valor).strip()
        for rotulo, valor in zip(sobre.iloc[:, 1], sobre.iloc[:, 2])
        if pd.notna(rotulo) and pd.notna(valor)
    }

    def buscar(padrao: str, texto: str, obrigatorio: bool = True):
        achou = re.search(padrao, texto)
        if not achou and obrigatorio:
            raise ValueError(f"Não encontrei '{padrao}' em: {texto!r}")
        return achou.group(1) if achou else None

    gerado = pd.to_datetime(
        buscar(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2})", pares["Gerado em"]),
        format="%d/%m/%Y %H:%M",
    )
    chuva = pares["Chuva usada"]
    return {
        # um voo = uma geração do simulador; o horário identifica o voo
        "voo_id": "voo_" + gerado.strftime("%Y%m%d_%H%M"),
        "gerado_em": gerado.strftime("%Y-%m-%d %H:%M:%S"),
        "semente": int(buscar(r"^(\d+)", pares["Semente"])),
        "chuva_72h_mm": float(buscar(r"([\d.]+)\s*mm em 72 h", chuva)),
        "chuva_prevista_24h_mm": float(buscar(r"([\d.]+)\s*mm previstos", chuva)),
        "chuva_e_real": "REAL" in chuva,
        "local_chuva": buscar(r"Chuva REAL de ([^ ]+)", chuva, obrigatorio=False),
        "descricao_area": pares.get("Área"),
    }


def tratar(dir_bronze: str) -> str:
    """Lê a partição bronze, limpa e grava em silver/dt=<data>/. Devolve o caminho."""
    bronze = Path(dir_bronze)
    manifesto = json.loads((bronze / "_manifesto.json").read_text(encoding="utf-8"))
    destino = config.DIR_SILVER / bronze.name
    destino.mkdir(parents=True, exist_ok=True)

    # ---- metadados do voo ---------------------------------------------------
    sobre = pd.read_csv(bronze / "sobre.csv", dtype=str)
    voo = extrair_metadados_voo(sobre)
    voo["arquivo_origem"] = manifesto["arquivo_origem"]
    voo["sha256_origem"] = manifesto["sha256"]
    voo["ingerido_em_utc"] = manifesto["ingerido_em_utc"]
    log.info("silver: voo identificado -> %s", voo)

    # ---- medições por célula --------------------------------------------------
    df = pd.read_csv(bronze / "dados.csv", dtype=str)
    faltando = set(RENOMEAR) - set(df.columns)
    if faltando:
        raise ValueError(f"Colunas esperadas ausentes na fonte: {sorted(faltando)}")
    df = df[list(RENOMEAR)].rename(columns=RENOMEAR)

    antes = len(df)
    for col in df.columns:  # tira espaços sobrando de todos os textos
        df[col] = df[col].str.strip()
    df = df.drop_duplicates(subset="celula_id", keep="last")
    log.info("silver: %d linhas lidas, %d duplicatas removidas", antes, antes - len(df))

    for col in INTEIRAS:
        df[col] = pd.to_numeric(df[col], errors="raise").astype("int64")
    for col in DECIMAIS:
        df[col] = pd.to_numeric(df[col], errors="raise").astype("float64")
    for col in BOOLEANAS:
        df[col] = _sim_nao(df[col])
    for col in TEXTO_MINUSCULO:
        df[col] = df[col].str.lower().map(_sem_acento)
    for col in CLASSES:
        df[col] = df[col].str.capitalize()

    df.insert(0, "voo_id", voo["voo_id"])
    df = df.sort_values(["linha", "coluna"]).reset_index(drop=True)

    df.to_parquet(destino / "medicoes_celula.parquet", index=False)
    (destino / "voo.json").write_text(
        json.dumps(voo, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("silver: %d células gravadas em %s", len(df), destino)
    return str(destino)
