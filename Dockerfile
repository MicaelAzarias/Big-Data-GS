# Imagem oficial do Airflow + as bibliotecas que o pipeline usa.
# O arquivo de constraints garante versões compatíveis com o Airflow 2.10.5.
FROM apache/airflow:2.10.5-python3.12
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt" \
    pandas openpyxl pyarrow psycopg2-binary
