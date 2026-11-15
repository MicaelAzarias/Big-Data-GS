-- Tabelas finais do Em Raízes (camada gold no banco que o MVP consulta).
-- SQL padrão: roda igual no PostgreSQL (Docker) e no SQLite (execução local).
-- O pipeline executa este arquivo a cada carga; IF NOT EXISTS torna isso seguro.

CREATE TABLE IF NOT EXISTS dim_voo (
    voo_id                 VARCHAR(30) PRIMARY KEY,
    gerado_em              TIMESTAMP NOT NULL,
    semente                INTEGER,
    chuva_72h_mm           DOUBLE PRECISION NOT NULL,
    chuva_prevista_24h_mm  DOUBLE PRECISION NOT NULL,
    chuva_e_real           BOOLEAN NOT NULL,
    local_chuva            VARCHAR(80),
    descricao_area         VARCHAR(200),
    arquivo_origem         VARCHAR(200) NOT NULL,
    sha256_origem          CHAR(64) NOT NULL,
    ingerido_em_utc        TIMESTAMP NOT NULL,
    n_celulas              INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_setor (
    setor_id       INTEGER PRIMARY KEY,
    setor          VARCHAR(30) NOT NULL UNIQUE,
    faixa_altura   VARCHAR(10) NOT NULL,
    faixa_lateral  VARCHAR(10) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_celula (
    celula_id          CHAR(6) PRIMARY KEY,
    linha              INTEGER NOT NULL,
    coluna             INTEGER NOT NULL,
    setor_id           INTEGER NOT NULL REFERENCES dim_setor (setor_id),
    altitude_m         DOUBLE PRECISION NOT NULL,
    inclinacao_graus   DOUBLE PRECISION NOT NULL,
    tipo_solo_amostra  VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS fato_medicao_celula (
    voo_id               VARCHAR(30) NOT NULL REFERENCES dim_voo (voo_id),
    celula_id            CHAR(6) NOT NULL REFERENCES dim_celula (celula_id),
    umidade_solo_pct     DOUBLE PRECISION NOT NULL,
    vegetacao_fracao     DOUBLE PRECISION NOT NULL,
    casas                INTEGER NOT NULL,
    moradores_estimados  DOUBLE PRECISION NOT NULL,
    tem_vazamento        BOOLEAN NOT NULL,
    erosao_indice        DOUBLE PRECISION NOT NULL,
    prob_fissura         DOUBLE PRECISION NOT NULL,
    fissura_detectada    BOOLEAN NOT NULL,
    tipo_solo_visao      VARCHAR(20) NOT NULL,
    confianca_visao      DOUBLE PRECISION NOT NULL,
    visao_acertou_solo   BOOLEAN NOT NULL,
    risco_agora          DOUBLE PRECISION NOT NULL,
    classe_agora         VARCHAR(10) NOT NULL,
    risco_24h            DOUBLE PRECISION NOT NULL,
    classe_24h           VARCHAR(10) NOT NULL,
    tendencia            VARCHAR(10) NOT NULL,
    plantar_capim        BOOLEAN NOT NULL,
    mudas_sugeridas      INTEGER NOT NULL,
    irrigar              BOOLEAN NOT NULL,
    agua_sugerida_l      INTEGER NOT NULL,
    PRIMARY KEY (voo_id, celula_id)
);

CREATE TABLE IF NOT EXISTS mart_risco_setor (
    voo_id                   VARCHAR(30) NOT NULL REFERENCES dim_voo (voo_id),
    setor_id                 INTEGER NOT NULL REFERENCES dim_setor (setor_id),
    setor                    VARCHAR(30) NOT NULL,
    prioridade               INTEGER NOT NULL,
    classe_setor             VARCHAR(10) NOT NULL,
    n_celulas                INTEGER NOT NULL,
    risco_medio_agora        DOUBLE PRECISION NOT NULL,
    risco_maximo_agora       DOUBLE PRECISION NOT NULL,
    risco_medio_24h          DOUBLE PRECISION NOT NULL,
    celulas_risco_alto       INTEGER NOT NULL,
    pct_celulas_risco_alto   DOUBLE PRECISION NOT NULL,
    casas                    INTEGER NOT NULL,
    moradores_estimados      DOUBLE PRECISION NOT NULL,
    moradores_em_risco_alto  DOUBLE PRECISION NOT NULL,
    vazamentos               INTEGER NOT NULL,
    fissuras                 INTEGER NOT NULL,
    celulas_para_plantio     INTEGER NOT NULL,
    mudas_sugeridas          INTEGER NOT NULL,
    PRIMARY KEY (voo_id, setor_id)
);

CREATE TABLE IF NOT EXISTS mart_avaliacao_visao (
    voo_id             VARCHAR(30) NOT NULL REFERENCES dim_voo (voo_id),
    tipo_solo_amostra  VARCHAR(20) NOT NULL,
    n_celulas          INTEGER NOT NULL,
    acertos            INTEGER NOT NULL,
    acuracia           DOUBLE PRECISION NOT NULL,
    confianca_media    DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (voo_id, tipo_solo_amostra)
);

CREATE TABLE IF NOT EXISTS log_qualidade (
    voo_id            VARCHAR(30) NOT NULL REFERENCES dim_voo (voo_id),
    regra             VARCHAR(60) NOT NULL,
    severidade        VARCHAR(5) NOT NULL,
    passou            BOOLEAN NOT NULL,
    linhas_com_falha  INTEGER NOT NULL,
    detalhe           VARCHAR(200),
    PRIMARY KEY (voo_id, regra)
);
