# 📚 RUNBOOK DE OPERAÇÕES - HARVEY BACKEND

> **Guia completo para operação, monitoramento e troubleshooting do Harvey Backend**

## 🚨 RESPOSTA A INCIDENTES

### SEV-1: Respostas com Alucinação / Factualmente Incorretas

**🔍 Diagnóstico:**
1. **Identifique o run_id** no log de auditoria:
   ```bash
   kubectl logs -n production deployment/harvey-backend | grep "run_id"
   ```

2. **Analise o relatório de faithfulness**:
   ```bash
   psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
   SELECT run_id, faithfulness_report, sources_used, agent_trace 
   FROM run_audit 
   WHERE run_id = 'UUID_AQUI';"
   ```

3. **Verifique qualidade do contexto RAG**:
   ```bash
   # Acesse o Qdrant para verificar os documentos retornados
   curl -X GET "http://qdrant:6333/collections/legal_docs/points/search" \
     -H "Content-Type: application/json" \
     -d '{"vector": [...], "limit": 10}'
   ```

**⚡ Ação Imediata:**
1. **Ative o modo "apenas logs"** para o agente problemático:
   ```bash
   kubectl patch configmap harvey-config -n production -p '{"data":{"AGENT_MODE":"log_only"}}'
   kubectl rollout restart deployment/harvey-backend -n production
   ```

2. **Remova documento mal indexado** (se identificado):
   ```bash
   curl -X DELETE "http://qdrant:6333/collections/legal_docs/points/POINT_ID"
   ```

**✅ Resolução:**
1. **Adicione ao golden dataset**:
   ```bash
   echo "run_id,expected_output,actual_output,issue_type" >> tests/golden_dataset.csv
   echo "UUID_AQUI,OUTPUT_ESPERADO,OUTPUT_ATUAL,hallucination" >> tests/golden_dataset.csv
   ```

2. **Ajuste o prompt do agente**:
   - Edite `app/agents/document_writer.py`
   - Adicione restrições mais específicas
   - Teste com `pytest tests/test_prompts.py`

3. **Verifique configuração do reranker**:
   ```python
   # app/core/rag.py
   reranker_config = {
       "model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
       "top_k": 5,  # Reduza se necessário
       "score_threshold": 0.7  # Aumente para maior qualidade
   }
   ```

---

### SEV-2: API com Latência Alta (p95 > 5s)

**🔍 Diagnóstico:**
1. **Verifique métricas no Grafana**:
   - Acesse `http://grafana.exemplo.com:3000`
   - Dashboard: "Harvey Backend - Performance"
   - Métricas: `harvey_api_req_rate`, `harvey_llm_latency_seconds`

2. **Identifique gargalos**:
   ```bash
   # Logs de performance
   kubectl logs -n production deployment/harvey-backend | grep "PERFORMANCE"
   
   # Métricas de CPU/Memory
   kubectl top pods -n production
   ```

3. **Análise de traces**:
   ```bash
   # Logs do LangGraph
   kubectl logs -n production deployment/harvey-backend | grep "langgraph"
   ```

**⚡ Ação Imediata:**
1. **Scale horizontal**:
   ```bash
   kubectl scale deployment harvey-backend --replicas=5 -n production
   ```

2. **Ative fallback de LLM**:
   ```bash
   kubectl patch configmap harvey-config -n production -p '{"data":{"LLM_FALLBACK_ENABLED":"true"}}'
   ```

3. **Ajuste timeout temporariamente**:
   ```bash
   kubectl patch configmap harvey-config -n production -p '{"data":{"API_TIMEOUT":"30"}}'
   ```

**✅ Resolução:**
1. **Otimize prompts**:
   - Reduza tamanho dos prompts
   - Simplifique instruções
   - Teste com `pytest tests/test_performance.py`

2. **Otimize RAG**:
   ```python
   # app/core/rag.py
   rag_config = {
       "chunk_size": 1000,  # Reduza para chunks menores
       "chunk_overlap": 200,
       "top_k": 3,  # Reduza número de documentos
       "embedding_cache_ttl": 3600  # Cache embeddings
   }
   ```

3. **Configure cache Redis**:
   ```python
   # app/core/cache.py
   cache_config = {
       "ttl": 3600,  # 1 hora
       "max_size": 1000,  # Máximo de entradas
       "compression": True  # Compressão de dados
   }
   ```

---

### SEV-3: Falha na Auditoria ou Compliance

**🔍 Diagnóstico:**
1. **Verifique integridade dos hashes**:
   ```sql
   SELECT run_id, input_hash, output_hash, 
          CASE WHEN input_hash IS NULL THEN 'MISSING HASH' ELSE 'OK' END as status
   FROM run_audit 
   WHERE created_at >= NOW() - INTERVAL '1 hour';
   ```

2. **Verifique detecção de PII**:
   ```sql
   SELECT run_id, pii_report->>'pii_detected' as pii_detected,
          pii_report->>'pii_types' as pii_types
   FROM run_audit 
   WHERE pii_report->>'pii_detected' = 'true';
   ```

3. **Verifique políticas de segurança**:
   ```bash
   kubectl logs -n production deployment/harvey-backend | grep "POLICY_VIOLATION"
   ```

**⚡ Ação Imediata:**
1. **Pare processamento se necessário**:
   ```bash
   kubectl patch configmap harvey-config -n production -p '{"data":{"AUDIT_REQUIRED":"true"}}'
   ```

2. **Ative modo strict de PII**:
   ```bash
   kubectl patch configmap harvey-config -n production -p '{"data":{"PII_STRICT_MODE":"true"}}'
   ```

**✅ Resolução:**
1. **Reprocesse execuções sem auditoria**:
   ```python
   # scripts/reprocess_audit.py
   from app.core.audit import build_and_save_audit_record
   
   # Busca runs sem auditoria
   missing_audits = await db.fetch_all(
       "SELECT run_id FROM runs WHERE run_id NOT IN (SELECT run_id FROM run_audit)"
   )
   
   for run in missing_audits:
       # Reprocessa auditoria
       await build_and_save_audit_record(run.run_id)
   ```

---

## 🔍 MONITORAMENTO E ALERTAS

### Métricas Críticas

**1. Disponibilidade da API**
```promql
# Uptime da API
up{job="harvey-backend"} * 100

# Taxa de erro
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100
```

**2. Performance**
```promql
# Latência P95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Throughput
rate(http_requests_total[5m])
```

**3. Recursos**
```promql
# CPU Usage
rate(container_cpu_usage_seconds_total[5m]) * 100

# Memory Usage
container_memory_working_set_bytes / container_spec_memory_limit_bytes * 100
```

**4. Negócio**
```promql
# Documentos gerados por hora
rate(documents_generated_total[1h])

# Taxa de feedback positivo
rate(feedback_positive_total[1h]) / rate(feedback_total[1h]) * 100
```

### Alertas no Prometheus

```yaml
# alerts/harvey-backend.yml
groups:
  - name: harvey-backend
    rules:
      - alert: HarveyBackendDown
        expr: up{job="harvey-backend"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Harvey Backend está fora do ar"
          description: "A API do Harvey Backend não está respondendo"

      - alert: HarveyHighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Alta latência no Harvey Backend"
          description: "P95 de latência está acima de 5s: {{ $value }}s"

      - alert: HarveyHighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Alta taxa de erro no Harvey Backend"
          description: "Taxa de erro está acima de 5%: {{ $value }}%"
```

---

## 🛠️ PROCEDIMENTOS DE MANUTENÇÃO

### Deploy de Nova Versão

**1. Preparação**
```bash
# Backup da base de dados
pg_dump -h $DB_HOST -U $DB_USER $DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql

# Verificar health dos serviços
kubectl get pods -n production
kubectl get svc -n production
```

**2. Deploy**
```bash
# Deploy com Helm
helm upgrade harvey-production ./helm/harvey \
  --set image.tag=v1.2.3 \
  --namespace production \
  --wait \
  --timeout=600s

# Verificar rollout
kubectl rollout status deployment/harvey-backend -n production
```

**3. Verificação**
```bash
# Smoke tests
curl -f https://harvey-api.exemplo.com/health
curl -f https://harvey-api.exemplo.com/metrics

# Verificar logs
kubectl logs -n production deployment/harvey-backend --tail=100
```

**4. Rollback (se necessário)**
```bash
# Rollback para versão anterior
helm rollback harvey-production -n production

# Verificar status
kubectl get pods -n production
```

### Manutenção da Base de Dados

**1. Backup Automático**
```bash
#!/bin/bash
# scripts/backup_db.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="harvey_backup_${DATE}.sql"

pg_dump -h $DB_HOST -U $DB_USER $DB_NAME > /backups/$BACKUP_FILE
gzip /backups/$BACKUP_FILE

# Upload para S3
aws s3 cp /backups/${BACKUP_FILE}.gz s3://harvey-backups/database/
```

**2. Limpeza de Dados Antigos**
```sql
-- Limpar dados de auditoria > 7 anos
DELETE FROM run_audit 
WHERE created_at < NOW() - INTERVAL '7 years';

-- Limpar dados temporários > 30 dias
DELETE FROM temp_data 
WHERE created_at < NOW() - INTERVAL '30 days';

-- Reindexar tabelas
REINDEX TABLE run_audit;
REINDEX TABLE feedback_events;
```

### Rotação de Logs

**1. Configuração do Logrotate**
```bash
# /etc/logrotate.d/harvey-backend
/var/log/harvey-backend/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 harvey harvey
    postrotate
        systemctl reload harvey-backend
    endscript
}
```

---

## 🚀 PROCEDIMENTOS DE SCALE

### Scale Horizontal

**1. Aumentar Réplicas**
```bash
# Via kubectl
kubectl scale deployment harvey-backend --replicas=5 -n production

# Via Helm
helm upgrade harvey-production ./helm/harvey \
  --set replicaCount=5 \
  --namespace production
```

**2. Configurar Autoscaling**
```yaml
# HPA Configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: harvey-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: harvey-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Scale Vertical

**1. Aumentar Recursos**
```bash
# Via Helm
helm upgrade harvey-production ./helm/harvey \
  --set resources.requests.cpu=1000m \
  --set resources.requests.memory=2Gi \
  --set resources.limits.cpu=2000m \
  --set resources.limits.memory=4Gi \
  --namespace production
```

---

## 📊 DASHBOARDS E RELATÓRIOS

### Dashboard Principal (Grafana)

**1. Métricas de Sistema**
- CPU Usage por pod
- Memory Usage por pod
- Network I/O
- Disk I/O

**2. Métricas de Aplicação**
- Requests per second
- Response time percentiles
- Error rates por endpoint
- Active connections

**3. Métricas de Negócio**
- Documentos gerados por hora
- Taxa de sucesso
- Feedback scores
- Usuários ativos

### Relatórios Automáticos

**1. Relatório Diário**
```python
# scripts/daily_report.py
import asyncio
from datetime import datetime, timedelta
from app.core.database import get_db

async def generate_daily_report():
    db = await get_db()
    yesterday = datetime.now() - timedelta(days=1)
    
    # Métricas do dia anterior
    stats = await db.fetch_one("""
        SELECT 
            COUNT(*) as total_runs,
            AVG(execution_time_ms) as avg_execution_time,
            COUNT(CASE WHEN pii_report->>'pii_detected' = 'true' THEN 1 END) as pii_detections,
            AVG(CASE WHEN rating > 0 THEN rating END) as avg_rating
        FROM run_audit ra
        LEFT JOIN feedback_events fe ON ra.run_id = fe.run_id
        WHERE ra.created_at >= %s
    """, yesterday)
    
    # Enviar relatório por email/Slack
    send_report(stats)
```

---

## 🔒 SEGURANÇA E COMPLIANCE

### Verificação de Segurança

**1. Scan de Vulnerabilidades**
```bash
# Scan da imagem Docker
trivy image ghcr.io/seu-usuario/harvey-backend:latest

# Scan do cluster
kube-bench run --check 4.2.1,4.2.2
```

**2. Verificação de Políticas**
```bash
# Verificar políticas de segurança
kubectl get networkpolicies -n production
kubectl get podsecuritypolicies
```

### Auditoria de Compliance

**1. Relatório de Conformidade LGPD**
```sql
-- Verificar processamento de PII
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_runs,
    COUNT(CASE WHEN pii_report->>'pii_detected' = 'true' THEN 1 END) as pii_runs,
    COUNT(CASE WHEN pii_report->>'pii_redacted' = 'true' THEN 1 END) as pii_redacted
FROM run_audit 
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

**2. Verificação de Integridade**
```python
# scripts/integrity_check.py
import hashlib
from app.core.database import get_db

async def verify_integrity():
    db = await get_db()
    
    # Verificar hashes
    records = await db.fetch_all("""
        SELECT run_id, input_text, input_hash, output_text, output_hash
        FROM run_audit
        WHERE created_at >= NOW() - INTERVAL '1 day'
    """)
    
    for record in records:
        # Verificar hash do input
        calculated_input_hash = hashlib.sha256(record.input_text.encode()).hexdigest()
        if calculated_input_hash != record.input_hash:
            print(f"INTEGRITY VIOLATION: Run {record.run_id} - Input hash mismatch")
            
        # Verificar hash do output
        calculated_output_hash = hashlib.sha256(record.output_text.encode()).hexdigest()
        if calculated_output_hash != record.output_hash:
            print(f"INTEGRITY VIOLATION: Run {record.run_id} - Output hash mismatch")
```

---

## 📞 CONTATOS DE EMERGÊNCIA

### Equipe de Plantão

**Desenvolvedor Principal**
- Nome: [Seu Nome]
- Email: dev@harvey.ai
- Telefone: +55 11 99999-9999
- Slack: @dev-principal

**DevOps/SRE**
- Nome: [Nome DevOps]
- Email: devops@harvey.ai
- Telefone: +55 11 88888-8888
- Slack: @devops-lead

**Compliance Officer**
- Nome: [Nome Compliance]
- Email: compliance@harvey.ai
- Telefone: +55 11 77777-7777
- Slack: @compliance-officer

### Fornecedores Críticos

**OpenAI**
- Status: https://status.openai.com/
- Suporte: platform.openai.com/support

**Anthropic**
- Status: https://status.anthropic.com/
- Suporte: support@anthropic.com

**AWS/Cloud Provider**
- Status: https://status.aws.amazon.com/
- Suporte: AWS Support Console

---

## 🎯 PROCEDIMENTOS DE TESTE

### Testes de Carga

**1. Teste com Artillery**
```yaml
# load-test.yml
config:
  target: 'https://harvey-api.exemplo.com'
  phases:
    - duration: 60
      arrivalRate: 10
    - duration: 120
      arrivalRate: 20
    - duration: 60
      arrivalRate: 50

scenarios:
  - name: "Generate Document"
    weight: 70
    flow:
      - post:
          url: "/api/v1/generate"
          json:
            tipo_documento: "peticao_inicial"
            contexto: "Ação de cobrança"
            partes: {...}
            
  - name: "Health Check"
    weight: 30
    flow:
      - get:
          url: "/health"
```

**2. Executar Teste**
```bash
# Instalar Artillery
npm install -g artillery

# Executar teste
artillery run load-test.yml
```

### Testes de Disaster Recovery

**1. Simulação de Falha de Pod**
```bash
# Deletar pod aleatório
kubectl delete pod -l app=harvey-backend -n production --force

# Verificar recuperação
kubectl get pods -n production -w
```

**2. Simulação de Falha de Banco**
```bash
# Parar banco temporariamente
kubectl scale deployment postgres --replicas=0 -n production

# Verificar comportamento da API
curl -f https://harvey-api.exemplo.com/health

# Restaurar banco
kubectl scale deployment postgres --replicas=1 -n production
```

---

## 📝 CHANGELOG E VERSIONING

### Formato de Versionamento

Seguimos **Semantic Versioning** (SemVer):
- **MAJOR**: Mudanças incompatíveis na API
- **MINOR**: Funcionalidades adicionadas de forma compatível
- **PATCH**: Correções de bugs compatíveis

### Exemplo de Changelog

```markdown
# Changelog

## [1.2.3] - 2024-01-15

### Added
- Nova funcionalidade de feedback estruturado
- Suporte para detecção de PII em documentos
- Auditoria forense com hashes SHA-256

### Changed
- Melhorada performance do RAG em 30%
- Atualizado LangGraph para versão 0.2.0

### Fixed
- Corrigido bug na geração de contratos
- Resolvido problema de memory leak

### Security
- Implementado mascaramento de dados sensíveis
- Adicionadas políticas de segurança por tenant
```

---

*Este runbook deve ser atualizado regularmente conforme o sistema evolui. Última atualização: Janeiro 2025*
