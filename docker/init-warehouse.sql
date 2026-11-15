-- Executado uma única vez, quando o volume do Postgres é criado.
-- Separa o banco do MVP (em_raizes) do banco interno do Airflow (airflow).
CREATE USER emraizes WITH PASSWORD 'emraizes';
CREATE DATABASE em_raizes OWNER emraizes;
