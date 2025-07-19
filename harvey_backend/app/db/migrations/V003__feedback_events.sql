-- Migração V003: Tabela de Eventos de Feedback
-- Captura avaliações, correções e sugestões dos advogados

CREATE TABLE feedback_events (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    tenant_id TEXT NOT NULL,
    user_id TEXT, -- ID do usuário que deu o feedback
    rating INT, -- Ex: -1 (polegar para baixo), 0 (neutro), 1 (polegar para cima)
    comment TEXT,
    error_spans JSONB, -- Lista de {start, end, label}
    missing_sources JSONB, -- Lista de {raw, class}
    edited_text_md TEXT, -- O texto completo corrigido pelo advogado
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Índices para otimização de consultas
CREATE INDEX idx_feedback_run_id ON feedback_events(run_id);
CREATE INDEX idx_feedback_tenant_user ON feedback_events(tenant_id, user_id);
CREATE INDEX idx_feedback_rating ON feedback_events(rating);
CREATE INDEX idx_feedback_created_at ON feedback_events(created_at);

-- Comentários para documentação
COMMENT ON TABLE feedback_events IS 'Armazena feedback dos usuários sobre execuções do sistema';
COMMENT ON COLUMN feedback_events.run_id IS 'ID da execução que recebeu feedback';
COMMENT ON COLUMN feedback_events.rating IS 'Avaliação: -1 (negativo), 0 (neutro), 1 (positivo)';
COMMENT ON COLUMN feedback_events.error_spans IS 'Spans de erro identificados pelo usuário';
COMMENT ON COLUMN feedback_events.missing_sources IS 'Fontes que deveriam ter sido incluídas';
COMMENT ON COLUMN feedback_events.edited_text_md IS 'Texto corrigido pelo advogado';
