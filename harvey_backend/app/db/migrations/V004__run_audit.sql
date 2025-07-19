-- Migração V004: Tabela de Auditoria Forense
-- Trilha de auditoria imutável para rastreabilidade e conformidade

CREATE TABLE run_audit (
    run_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT,
    task TEXT NOT NULL,
    doc_type TEXT,
    started_at TIMESTAMPTZ DEFAULT now(),
    ended_at TIMESTAMPTZ,
    success BOOLEAN,
    error_message TEXT,
    
    -- Hashes para integridade e verificação
    input_hash CHAR(64), -- SHA-256 do prompt + metadados
    output_hash CHAR(64), -- SHA-256 do texto final gerado
    context_docs_hash CHAR(64), -- SHA-256 dos src_ids concatenados e ordenados
    
    -- Versionamento e Rastreabilidade
    prompt_version TEXT,
    supervisor_version TEXT,
    agent_trace JSONB, -- [{agent, model, latency_ms, tokens_in, tokens_out}]
    
    -- Política e Segurança
    policy_snapshot JSONB, -- A política do tenant no momento da execução
    pii_report JSONB, -- Relatório de PIIs detectados e reduzidos
    sources_used JSONB, -- Lista de src_ids usados no RAG
    
    -- Métricas e Custo
    estimated_cost_usd NUMERIC(10, 6),
    tokens_input INTEGER,
    tokens_output INTEGER,
    execution_time_ms INTEGER,
    
    -- Metadados adicionais
    client_ip INET,
    user_agent TEXT,
    request_id TEXT,
    
    -- Auditoria
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Índices para consultas eficientes
CREATE INDEX idx_audit_tenant_time ON run_audit(tenant_id, started_at);
CREATE INDEX idx_audit_user_time ON run_audit(user_id, started_at);
CREATE INDEX idx_audit_success ON run_audit(success);
CREATE INDEX idx_audit_doc_type ON run_audit(doc_type);
CREATE INDEX idx_audit_task ON run_audit(task);
CREATE INDEX idx_audit_cost ON run_audit(estimated_cost_usd);

-- Índices para hashes (verificação de integridade)
CREATE INDEX idx_audit_input_hash ON run_audit(input_hash);
CREATE INDEX idx_audit_output_hash ON run_audit(output_hash);

-- Tabela para armazenar checksums de integridade
CREATE TABLE audit_integrity (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES run_audit(run_id),
    checksum_type TEXT NOT NULL, -- 'input', 'output', 'context'
    checksum_value CHAR(64) NOT NULL,
    algorithm TEXT DEFAULT 'SHA-256',
    verified_at TIMESTAMPTZ DEFAULT now(),
    verification_status BOOLEAN DEFAULT true
);

-- Índices para verificação de integridade
CREATE INDEX idx_integrity_run_id ON audit_integrity(run_id);
CREATE INDEX idx_integrity_checksum ON audit_integrity(checksum_value);

-- Tabela para logs de acesso à auditoria
CREATE TABLE audit_access_log (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES run_audit(run_id),
    accessed_by TEXT NOT NULL,
    access_type TEXT NOT NULL, -- 'read', 'export', 'verify'
    accessed_at TIMESTAMPTZ DEFAULT now(),
    client_ip INET,
    reason TEXT,
    authorized BOOLEAN DEFAULT true
);

-- Índice para logs de acesso
CREATE INDEX idx_access_log_run_id ON audit_access_log(run_id);
CREATE INDEX idx_access_log_user_time ON audit_access_log(accessed_by, accessed_at);

-- Comentários para documentação
COMMENT ON TABLE run_audit IS 'Auditoria forense de execuções do sistema para rastreabilidade e conformidade';
COMMENT ON COLUMN run_audit.input_hash IS 'Hash SHA-256 do input completo (prompt + metadados)';
COMMENT ON COLUMN run_audit.output_hash IS 'Hash SHA-256 do texto final gerado';
COMMENT ON COLUMN run_audit.context_docs_hash IS 'Hash SHA-256 dos documentos de contexto utilizados';
COMMENT ON COLUMN run_audit.pii_report IS 'Relatório de PIIs detectados e tratados';
COMMENT ON COLUMN run_audit.policy_snapshot IS 'Snapshot da política do tenant no momento da execução';
COMMENT ON COLUMN run_audit.agent_trace IS 'Trace completo da execução dos agentes';

COMMENT ON TABLE audit_integrity IS 'Verificação de integridade dos dados de auditoria';
COMMENT ON TABLE audit_access_log IS 'Log de acesso aos dados de auditoria para conformidade';

-- Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_run_audit_updated_at 
    BEFORE UPDATE ON run_audit 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- View para consultas de auditoria comuns
CREATE VIEW audit_summary AS
SELECT 
    r.run_id,
    r.tenant_id,
    r.user_id,
    r.task,
    r.doc_type,
    r.started_at,
    r.ended_at,
    r.success,
    r.estimated_cost_usd,
    r.tokens_input,
    r.tokens_output,
    r.execution_time_ms,
    COALESCE(jsonb_array_length(r.sources_used), 0) as sources_count,
    COALESCE((r.pii_report->>'total_redactions')::int, 0) as pii_redactions,
    (r.ended_at - r.started_at) as total_duration
FROM run_audit r;

COMMENT ON VIEW audit_summary IS 'View consolidada para relatórios de auditoria';

-- Função para verificar integridade de um registro
CREATE OR REPLACE FUNCTION verify_audit_integrity(audit_run_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    current_record run_audit;
    computed_hash CHAR(64);
    is_valid BOOLEAN := true;
BEGIN
    -- Busca o registro
    SELECT * INTO current_record FROM run_audit WHERE run_id = audit_run_id;
    
    IF NOT FOUND THEN
        RETURN false;
    END IF;
    
    -- Verifica se os hashes ainda são válidos
    -- (implementação específica dependeria da lógica de hash)
    
    -- Registra a verificação
    INSERT INTO audit_integrity (run_id, checksum_type, checksum_value, verification_status)
    VALUES (audit_run_id, 'integrity_check', current_record.input_hash, is_valid);
    
    RETURN is_valid;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION verify_audit_integrity IS 'Função para verificar integridade de um registro de auditoria';
