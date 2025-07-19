-- Inicialização do banco PostgreSQL para Harvey Backend
-- Este script configura o banco de dados inicial

-- Configurações de segurança
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 1000;
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';

-- Configurações de performance
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';

-- Configurações de conexão
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET idle_in_transaction_session_timeout = '10min';

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Configurações de locale para português brasileiro
SET lc_messages = 'pt_BR.UTF-8';
SET lc_monetary = 'pt_BR.UTF-8';
SET lc_numeric = 'pt_BR.UTF-8';
SET lc_time = 'pt_BR.UTF-8';

-- Recarregar configurações
SELECT pg_reload_conf();

-- Mensagem de confirmação
SELECT 'Banco PostgreSQL configurado com sucesso para Harvey Backend!' as status;
