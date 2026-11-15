"""Gera a documentação entregue no portal:

    docs/arquitetura.png                 diagrama de arquitetura
    docs/modelo_dados.png                diagrama do modelo dimensional
    docs/dicionario_dados.md             dicionário em Markdown (para o repositório)
    docs/arquitetura_e_dicionario.pdf    PDF único (arquitetura + dicionário)

Uso:  python docs/gerar_documentacao.py
Antes de gerar a versão final, preencha EQUIPE e REPOSITORIO abaixo.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from dicionario import TABELAS

# ----------------------------------------------------------------------------
# PREENCHA ANTES DE ENTREGAR
EQUIPE = ""        # ex.: "Ana Silva (RM 12345) · Bruno Souza (RM 67890)"
REPOSITORIO = ""   # ex.: "https://github.com/sua-equipe/em-raizes-pipeline"
# ----------------------------------------------------------------------------

DOCS = Path(__file__).resolve().parent

VERDE = "#1F5C4A"
VERDE_CLARO = "#E4EFEA"
TERRA = "#A8502B"
TERRA_CLARO = "#F6E9E1"
TINTA = "#1E2A27"
CINZA = "#5E6B67"
LINHA = "#C9D3CF"
FUNDO = "#F6F8F7"


# ============================== DIAGRAMAS ===================================
def _caixa(ax, x, y, w, h, titulo, linhas=(), face="white", borda=LINHA,
           cor_titulo=TINTA, tam=7.6, tam_sub=6.7):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
        facecolor=face, edgecolor=borda, linewidth=0.9, zorder=2))
    topo = y + h - 0.17
    ax.text(x + w / 2, topo, titulo, ha="center", va="top", fontsize=tam,
            fontweight="bold", color=cor_titulo, zorder=3)
    for i, linha in enumerate(linhas):
        ax.text(x + w / 2, topo - 0.27 - i * 0.2, linha, ha="center", va="top",
                fontsize=tam_sub, color=CINZA, zorder=3)


def _seta(ax, de, para, cor=CINZA, estilo="-"):
    ax.add_patch(FancyArrowPatch(
        de, para, arrowstyle="-|>", mutation_scale=9, linewidth=1.0,
        color=cor, linestyle=estilo, zorder=4, shrinkA=0, shrinkB=0))


def diagrama_arquitetura(destino: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 6.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10.55)
    ax.axis("off")

    def rotulo(y, texto):
        ax.text(0.15, y, texto, fontsize=6.6, fontweight="bold", color=CINZA, va="center")

    # ---- 1. fontes ----------------------------------------------------------
    rotulo(10.3, "1 · FONTES")
    _caixa(ax, 0.15, 8.75, 3.6, 1.3, "Chuva real", [
        "Cemaden: 72 h, 13 pluviômetros",
        "Open-Meteo: previsão de 24 h"], face=TERRA_CLARO, borda=TERRA, cor_titulo=TERRA)
    _caixa(ax, 4.2, 8.75, 3.6, 1.3, "Simulador do drone", [
        "sensores + visão computacional",
        "simulados (semente 42)"], face=TERRA_CLARO, borda=TERRA, cor_titulo=TERRA)
    _caixa(ax, 8.25, 8.75, 3.6, 1.3, "Zona de pouso · data/raw", [
        "dados_simulados_em_raizes.xlsx",
        "576 células · 26 colunas"])
    _seta(ax, (3.75, 9.4), (4.2, 9.4))
    _seta(ax, (7.8, 9.4), (8.25, 9.4))

    # ---- 2. airflow ---------------------------------------------------------
    ax.add_patch(FancyBboxPatch(
        (0.15, 3.35), 11.7, 4.8, boxstyle="round,pad=0,rounding_size=0.12",
        facecolor=FUNDO, edgecolor=VERDE, linewidth=1.2, zorder=1))
    ax.text(1.6, 7.85, "2 · ORQUESTRAÇÃO — Apache Airflow 2.10 · DAG em_raizes_pipeline · @daily",
            fontsize=7.2, fontweight="bold", color=VERDE, va="center")

    tarefas = [
        ("ingestao_\nbronze", "Extrai o Excel\nsem transformar"),
        ("tratamento_\nsilver", "Padroniza nomes,\ntipos e textos"),
        ("validacao_\nqualidade", "32 regras; erro\nbloqueia a carga"),
        ("modelagem_\ngold", "Esquema estrela\n+ marts"),
        ("carga_\nwarehouse", "Upsert em uma\ntransação"),
        ("verificacao_\nfinal", "Contagens e\nintegridade"),
    ]
    larg, vao = 1.7, 0.2
    x0 = 0.15 + (11.7 - (6 * larg + 5 * vao)) / 2
    xs = [x0 + i * (larg + vao) for i in range(6)]
    for x, (nome, desc) in zip(xs, tarefas):
        ax.add_patch(FancyBboxPatch(
            (x, 6.05), larg, 1.4, boxstyle="round,pad=0,rounding_size=0.08",
            facecolor=VERDE, edgecolor=VERDE, zorder=2))
        ax.text(x + larg / 2, 7.08, nome, ha="center", va="center", fontsize=6.9,
                fontweight="bold", color="white", zorder=3, linespacing=1.15)
        ax.text(x + larg / 2, 6.38, desc, ha="center", va="center", fontsize=6.3,
                color="#D6E6DF", zorder=3, linespacing=1.2)
    for a, b in zip(xs[:-1], xs[1:]):
        _seta(ax, (a + larg, 6.75), (b, 6.75), cor=VERDE)
    # arquivo de origem entra na primeira tarefa
    ax.plot([10.05, 10.05], [8.75, 8.42], color=CINZA, lw=1.0, zorder=4)
    ax.plot([10.05, xs[0] + larg / 2], [8.42, 8.42], color=CINZA, lw=1.0, zorder=4)
    _seta(ax, (xs[0] + larg / 2, 8.42), (xs[0] + larg / 2, 7.45))

    # ---- armazenamento por camada ---------------------------------------------
    ax.text(0.4, 3.68, "ARMAZENAMENTO — arquitetura medalhão, particionada por data de execução",
            fontsize=6.2, fontweight="bold", color=CINZA, va="center")
    camadas = [
        (xs[0], larg, "Bronze", ["CSV bruto", "+ manifesto", "(SHA-256)"]),
        (xs[1], 2 * larg + vao, "Silver", ["Parquet limpo e tipado", "voo.json (metadados do voo)", "qualidade.csv"]),
        (xs[3], larg, "Gold", ["Parquet", "7 tabelas", "modeladas"]),
        (xs[4], 2 * larg + vao, "Warehouse · PostgreSQL 16", ["banco em_raizes", "3 dimensões · 1 fato", "2 marts · 1 log"]),
    ]
    for x, w, titulo, linhas in camadas:
        _caixa(ax, x, 4.0, w, 1.35, titulo, linhas, cor_titulo=VERDE)
    for i in [0, 1, 2, 3, 4, 5]:
        _seta(ax, (xs[i] + larg / 2, 6.05), (xs[i] + larg / 2, 5.35), cor=VERDE, estilo=(0, (2, 2)))

    # ---- 3. consumo -----------------------------------------------------------
    rotulo(2.95, "3 · CONSUMO")
    _caixa(ax, 0.15, 0.95, 5.7, 1.35, "App Em Raízes (MVP)", [
        "mapa de risco por célula · alertas por setor",
        "lista de vistoria · plano de plantio"], face=TERRA_CLARO, borda=TERRA, cor_titulo=TERRA)
    _caixa(ax, 6.15, 0.95, 5.7, 1.35, "Modelos de IA", [
        "monitoramento da visão computacional",
        "(mart_avaliacao_visao) · base para treino"], face=TERRA_CLARO, borda=TERRA, cor_titulo=TERRA)
    cx = xs[4] + larg + vao / 2
    ax.plot([cx, cx], [4.0, 2.75], color=CINZA, lw=1.0, zorder=4)
    ax.plot([3.0, cx], [2.75, 2.75], color=CINZA, lw=1.0, zorder=4)
    _seta(ax, (3.0, 2.75), (3.0, 2.3))
    _seta(ax, (9.0, 2.75), (9.0, 2.3))
    ax.text(cx + 0.14, 3.05, "consultas SQL", fontsize=6, color=CINZA, va="center")

    # ---- infraestrutura ---------------------------------------------------------
    ax.add_patch(FancyBboxPatch(
        (0.15, 0.1), 11.7, 0.5, boxstyle="round,pad=0,rounding_size=0.08",
        facecolor="white", edgecolor=LINHA, linewidth=0.9))
    ax.text(6.0, 0.35, "INFRAESTRUTURA — Docker Compose: postgres · airflow-init · airflow-webserver · "
            "airflow-scheduler (LocalExecutor)", ha="center", va="center", fontsize=6.3, color=CINZA)

    fig.savefig(destino, dpi=220, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)


def diagrama_modelo(destino: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.3)
    ax.axis("off")

    def tabela(x, y, w, h, nome, linhas, destaque=False):
        _caixa(ax, x, y, w, h, nome, linhas,
               face=VERDE_CLARO if destaque else "white",
               borda=VERDE if destaque else LINHA, cor_titulo=VERDE, tam=7.2, tam_sub=6.1)

    tabela(0.2, 4.15, 3.0, 1.95, "dim_voo", ["PK voo_id", "gerado_em, semente", "chuva_72h_mm", "chuva_prevista_24h_mm", "sha256_origem ..."])
    tabela(0.2, 0.2, 3.0, 1.75, "dim_setor", ["PK setor_id", "setor", "faixa_altura", "faixa_lateral"])
    tabela(0.2, 2.25, 3.0, 1.6, "dim_celula", ["PK celula_id · FK setor_id", "linha, coluna, altitude_m", "inclinacao_graus, tipo_solo"])
    tabela(4.4, 1.55, 3.3, 3.2, "fato_medicao_celula", [
        "PK voo_id + celula_id", "umidade, vegetação, casas", "vazamento, erosão, fissura",
        "tipo_solo_visao, confiança", "risco_agora, risco_24h, classes",
        "plantio, mudas, irrigação", "", "grão: 1 célula por voo"], destaque=True)
    tabela(8.8, 4.15, 3.0, 1.95, "mart_risco_setor", ["PK voo_id + setor_id", "prioridade, classe_setor", "risco médio / máximo", "moradores_em_risco_alto ..."])
    tabela(8.8, 2.25, 3.0, 1.6, "mart_avaliacao_visao", ["PK voo_id + tipo_solo", "acertos, acuracia", "confianca_media"])
    tabela(8.8, 0.2, 3.0, 1.75, "log_qualidade", ["PK voo_id + regra", "severidade, passou", "linhas_com_falha", "detalhe"])

    _seta(ax, (4.4, 4.3), (3.2, 5.0), cor=VERDE)      # fato -> dim_voo
    _seta(ax, (4.4, 3.05), (3.2, 3.05), cor=VERDE)    # fato -> dim_celula
    _seta(ax, (1.7, 2.25), (1.7, 1.95), cor=VERDE)    # dim_celula -> dim_setor
    for y in (5.0, 3.05):                             # fato => marts (agregação)
        _seta(ax, (7.7, 3.6 if y > 4 else 3.05), (8.8, y), cor=TERRA, estilo=(0, (2, 2)))
    ax.text(3.8, 0.75, "FK (chave estrangeira)", fontsize=6.2, color=VERDE, va="center")
    _seta(ax, (3.25, 0.75), (3.7, 0.75), cor=VERDE)
    ax.text(3.8, 0.4, "agregação feita pelo pipeline", fontsize=6.2, color=TERRA, va="center")
    _seta(ax, (3.25, 0.4), (3.7, 0.4), cor=TERRA, estilo=(0, (2, 2)))

    fig.savefig(destino, dpi=220, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)


# ============================== MARKDOWN ====================================
def dicionario_markdown(destino: Path) -> None:
    linhas = ["# Dicionário de dados — tabelas entregues pelo pipeline", ""]
    for t in TABELAS:
        linhas += [
            f"## {t['nome']}", "",
            f"**{t['tipo']}** · {t['descricao']}", "",
            f"- Grão: {t['grao']}", f"- Chave primária: `{t['chave']}`", "",
            "| Coluna | Tipo | Descrição | Origem |", "|---|---|---|---|",
        ]
        linhas += [f"| `{c}` | {tp} | {d} | {o} |" for c, tp, d, o in t["colunas"]]
        linhas.append("")
    destino.write_text("\n".join(linhas), encoding="utf-8")


# ================================= PDF ======================================
def _fontes():
    pasta = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    pdfmetrics.registerFont(TTFont("Corpo", str(pasta / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("Corpo-Bold", str(pasta / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Mono", str(pasta / "DejaVuSansMono.ttf")))
    pdfmetrics.registerFontFamily("Corpo", normal="Corpo", bold="Corpo-Bold")


def gerar_pdf(destino: Path) -> None:
    _fontes()
    base = dict(fontName="Corpo", textColor=colors.HexColor(TINTA), alignment=TA_LEFT)
    titulo = ParagraphStyle("titulo", fontSize=20, leading=25, **{**base, "fontName": "Corpo-Bold"})
    sub = ParagraphStyle("sub", fontSize=10, leading=14, **{**base, "textColor": colors.HexColor(CINZA)})
    h1 = ParagraphStyle("h1", fontSize=13, leading=17, spaceBefore=14, spaceAfter=6,
                        **{**base, "fontName": "Corpo-Bold", "textColor": colors.HexColor(VERDE)})
    h2 = ParagraphStyle("h2", fontSize=10.5, leading=14, spaceBefore=10, spaceAfter=2,
                        **{**base, "fontName": "Mono", "textColor": colors.HexColor(TERRA)})
    corpo = ParagraphStyle("corpo", fontSize=9, leading=13.2, spaceAfter=6, **base)
    cel = ParagraphStyle("cel", fontSize=7.6, leading=10.2, **base)
    cel_mono = ParagraphStyle("cel_mono", fontSize=7.2, leading=10.2, **{**base, "fontName": "Mono"})
    cab = ParagraphStyle("cab", fontSize=7.6, leading=10.2,
                         **{**base, "fontName": "Corpo-Bold", "textColor": colors.white})

    def tabela(cabecalho, linhas, larguras, mono=(0,)):
        dados = [[Paragraph(c, cab) for c in cabecalho]]
        for linha in linhas:
            dados.append([Paragraph(str(v), cel_mono if i in mono else cel) for i, v in enumerate(linha)])
        t = Table(dados, colWidths=[l * cm for l in larguras], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(VERDE)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(FUNDO)]),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor(LINHA)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]))
        return t

    def rodape(canvas, doc):
        canvas.saveState()
        canvas.setFont("Corpo", 7.5)
        canvas.setFillColor(colors.HexColor(CINZA))
        canvas.drawString(2 * cm, 1.2 * cm, "Em Raízes · Pipeline de dados do MVP CitizenTech")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"{doc.page}")
        canvas.restoreState()

    h = []
    h.append(Paragraph("Em Raízes — Pipeline de dados do MVP", titulo))
    h.append(Spacer(1, 4))
    h.append(Paragraph("Big Data Architecture &amp; Data Integration · Arquitetura e dicionário de dados", sub))
    if EQUIPE:
        h.append(Paragraph(f"Equipe: {EQUIPE}", sub))
    if REPOSITORIO:
        h.append(Paragraph(f"Repositório: {REPOSITORIO}", sub))

    # ---- 1 ------------------------------------------------------------------
    h.append(Paragraph("1. Contexto e origem dos dados", h1))
    h.append(Paragraph(
        "O Em Raízes mapeia o risco de deslizamento em encostas ocupadas e recomenda ações "
        "(vistoria, plantio de capim-vetiver, irrigação). A fonte prevista é um drone com sensores e "
        "visão computacional que sobrevoa o morro e entrega medições por célula de 10 m x 10 m.", corpo))
    h.append(Paragraph(
        "<b>Por que dados simulados.</b> O drone e o morro-piloto ainda não existem. Um simulador gera o "
        "que o drone entregaria, com regras que imitam o comportamento real (casas no meio e na base, "
        "mata no topo, solo mais úmido onde a água escorre) e com semente fixa (42), o que torna os dados "
        "reprodutíveis. A visão computacional simulada erra o tipo de solo de propósito (cerca de 12% por "
        "projeto; 10,1% neste voo), para que o MVP mostre a necessidade de conferência humana.", corpo))
    h.append(Paragraph(
        "<b>O que é real.</b> A chuva: acumulado de 72 h do Cemaden (percentil 75 de 13 pluviômetros de "
        "Petrópolis/RJ) e previsão de 24 h do Open-Meteo, lidos em 10/11/2026 e embutidos na geração. "
        "Os pesos do índice de risco são ilustrativos e não foram calibrados com deslizamentos reais; "
        "os dados servem para demonstrar o app, não para avaliar risco de verdade.", corpo))

    h.append(Paragraph("O pipeline em números (execução de 15/11/2026)", h2))
    h.append(tabela(
        ["Item", "Valor"],
        [
            ["Arquivo de origem", "1 planilha Excel, 3 abas (Sobre, Dados, Dicionário)"],
            ["Volume por voo", "576 células (grade 24 x 24) x 26 colunas, cerca de 5,8 hectares"],
            ["Tarefas orquestradas", "6, em sequência, no DAG em_raizes_pipeline"],
            ["Regras de qualidade", "32 aplicadas: 0 erros e 4 avisos neste voo"],
            ["Tabelas entregues", "7: dim_voo (1 linha), dim_setor (9), dim_celula (576), fato_medicao_celula (576), mart_risco_setor (9), mart_avaliacao_visao (5), log_qualidade (32)"],
            ["Avisos registrados", "27 células com altitude negativa (abaixo da rua); tendencia, irrigar e agua_sugerida_l sem variação neste voo"],
            ["Acerto da visão", "89,9% no tipo de solo (518 de 576 células)"],
        ], [4.2, 12.8], mono=()))

    # ---- 2 ------------------------------------------------------------------
    h.append(PageBreak())
    h.append(Paragraph("2. Arquitetura", h1))
    h.append(Paragraph(
        "O pipeline segue a arquitetura medalhão (bronze, silver, gold) sobre um data lake local em "
        "arquivos, com carga final em PostgreSQL. O Apache Airflow orquestra as seis etapas; cada tarefa "
        "repassa à seguinte apenas o caminho da partição que gerou.", corpo))
    img = Image(str(DOCS / "arquitetura.png"))
    escala = (17 * cm) / img.imageWidth
    img.drawWidth, img.drawHeight = 17 * cm, img.imageHeight * escala
    h.append(img)

    h.append(Paragraph("Camadas", h2))
    h.append(tabela(
        ["Camada", "Onde fica", "O que acontece"],
        [
            ["raw", "data/raw/ (xlsx)", "Zona de pouso. O arquivo fica como chegou da fonte."],
            ["bronze", "data/bronze/dt=AAAA-MM-DD/ (CSV)", "Cópia fiel das três abas, tudo como texto, mais um manifesto com hash SHA-256, horário e contagem de linhas. Nenhuma transformação."],
            ["silver", "data/silver/dt=.../ (Parquet, JSON)", "Nomes em snake_case com unidade, tipos corretos, Sim/Não vira booleano, textos normalizados, duplicatas removidas. Metadados do voo (chuva, semente, data) extraídos da aba Sobre."],
            ["qualidade", "data/silver/dt=.../qualidade.csv", "32 regras: chaves, grade completa, faixas físicas, domínios e coerência com as regras de negócio. Regra de severidade ERRO interrompe o DAG antes da carga."],
            ["gold", "data/gold/dt=.../ (Parquet)", "Esquema estrela (3 dimensões e 1 fato), 2 marts de consumo e o log de qualidade."],
            ["warehouse", "PostgreSQL, banco em_raizes", "Tabelas com chave primária e estrangeira. É o que o app e os modelos de IA consultam."],
        ], [2.1, 4.9, 10.0]))

    h.append(Paragraph("Decisões de projeto", h2))
    for texto in [
        "<b>ETL, não ELT.</b> O volume é pequeno (576 células por voo) e as regras de qualidade precisam barrar o dado antes do banco; por isso a transformação acontece em Python, fora do warehouse.",
        "<b>Lógica fora do DAG.</b> As transformações ficam no pacote em_raizes; o DAG só chama funções. O mesmo código roda no Airflow e por linha de comando (python -m em_raizes.run_local).",
        "<b>Idempotência.</b> Reexecutar o mesmo dia sobrescreve a mesma partição. No banco, dimensões usam upsert e fatos e marts são substituídos por voo, tudo em uma única transação: reprocessar não duplica linhas.",
        "<b>Histórico por voo.</b> Toda linha de fato carrega voo_id. Quando houver um novo voo, basta trocar o arquivo em data/raw: o histórico anterior é preservado e o app passa a comparar voos.",
        "<b>Linhagem.</b> dim_voo guarda nome e hash do arquivo de origem e o horário da ingestão; log_qualidade guarda o resultado de cada regra em cada carga.",
    ]:
        h.append(Paragraph(texto, corpo))

    # ---- 3 ------------------------------------------------------------------
    h.append(Paragraph("3. Orquestração", h1))
    h.append(Paragraph(
        "DAG em_raizes_pipeline, agendado diariamente (@daily), sem catchup, uma execução por vez, "
        "uma nova tentativa automática em caso de falha (exceto na validação: dado ruim não melhora "
        "com repetição).", corpo))
    h.append(tabela(
        ["Tarefa", "Entrada", "Saída", "Função"],
        [
            ["ingestao_bronze", "data/raw/*.xlsx", "bronze/dt=.../", "em_raizes.bronze.ingerir"],
            ["tratamento_silver", "bronze/dt=.../", "silver/dt=.../", "em_raizes.silver.tratar"],
            ["validacao_qualidade", "silver/dt=.../", "qualidade.csv", "em_raizes.qualidade.validar"],
            ["modelagem_gold", "silver validada", "gold/dt=.../", "em_raizes.gold.modelar"],
            ["carga_warehouse", "gold/dt=.../", "7 tabelas no banco", "em_raizes.carga.carregar"],
            ["verificacao_final", "contagens da carga", "contagens do banco", "em_raizes.carga.verificar"],
        ], [3.6, 3.6, 3.7, 6.1], mono=(0, 3)))

    # ---- 4 ------------------------------------------------------------------
    sec4 = [Paragraph("4. Modelo de dados", h1), Paragraph(
        "O terreno (dim_celula) é separado das medições (fato_medicao_celula) porque altitude, "
        "inclinação e solo de referência não mudam entre voos, enquanto umidade, risco e recomendações "
        "mudam a cada voo. Os marts são agregações prontas para as telas do app e para o "
        "acompanhamento do modelo de visão.", corpo)]
    img2 = Image(str(DOCS / "modelo_dados.png"))
    escala = (15.5 * cm) / img2.imageWidth
    img2.drawWidth, img2.drawHeight = 15.5 * cm, img2.imageHeight * escala
    h.append(KeepTogether(sec4 + [img2]))

    # ---- 5 ------------------------------------------------------------------
    h.append(Paragraph("5. Dicionário de dados", h1))
    h.append(Paragraph(
        "Origem: <b>Simulado</b> = medição que o drone, os sensores ou a visão fariam; "
        "<b>Calculado</b> = regra de negócio do simulador; <b>Real</b> = chuva do Cemaden e do Open-Meteo; "
        "<b>Pipeline</b> = criado por este pipeline (chaves, derivações, agregações, auditoria). "
        "DOUBLE = DOUBLE PRECISION.", corpo))
    for t in TABELAS:
        cabecalho = [
            Paragraph(t["nome"], h2),
            Paragraph(f"<b>{t['tipo']}.</b> {t['descricao']} Grão: {t['grao']}. "
                      f"Chave primária: {t['chave']}.", corpo),
        ]
        corpo_tabela = tabela(["Coluna", "Tipo", "Descrição", "Origem"],
                              t["colunas"], [4.1, 2.7, 8.4, 1.8])
        h.append(KeepTogether(cabecalho))
        h.append(corpo_tabela)

    SimpleDocTemplate(
        str(destino), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=2 * cm,
        title="Em Raízes — Pipeline de dados do MVP", author=EQUIPE or "Equipe Em Raízes",
    ).build(h, onFirstPage=rodape, onLaterPages=rodape)


if __name__ == "__main__":
    diagrama_arquitetura(DOCS / "arquitetura.png")
    diagrama_modelo(DOCS / "modelo_dados.png")
    dicionario_markdown(DOCS / "dicionario_dados.md")
    gerar_pdf(DOCS / "arquitetura_e_dicionario.pdf")
    print("Documentação gerada em", DOCS)
