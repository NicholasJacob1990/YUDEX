# Sistema de Personalização por Centroides

Este documento explica como usar o sistema de personalização por centroides implementado no Harvey Backend.

## Visão Geral

O sistema de personalização por centroides permite ajustar os resultados de busca baseado no histórico de documentos de cada tenant, melhorando a relevância dos resultados para o contexto específico do cliente.

### Como Funciona

1. **Cálculo de Centroides**: Para cada tenant e tag temática, calculamos o centroide (vetor médio) dos documentos relevantes
2. **Armazenamento**: Os centroides são armazenados no Redis para acesso rápido
3. **Personalização**: Na busca, o vetor da query é ajustado na direção do centroide do tenant
4. **Busca Híbrida**: Aplicamos RRF (Reciprocal Rank Fusion) combinando busca semântica e lexical

## Instalação e Configuração

### 1. Dependências

```bash
pip install numpy redis pydantic
```

### 2. Configuração do Redis

```bash
# Instalar Redis
brew install redis  # macOS
# ou
sudo apt-get install redis-server  # Ubuntu

# Iniciar Redis
redis-server
```

### 3. Variáveis de Ambiente

Adicione ao seu `.env`:

```env
# Redis
REDIS_URL=redis://localhost:6379

# Personalização
DEFAULT_PERSONALIZATION_ALPHA=0.25
MIN_PERSONALIZATION_ALPHA=0.0
MAX_PERSONALIZATION_ALPHA=1.0

# Busca
DEFAULT_K_TOTAL=20
MAX_K_TOTAL=100
RRF_K_PARAMETER=60

# Cálculo de centroides
MIN_VECTORS_FOR_CENTROID=10
MAX_VECTORS_FOR_CENTROID=10000
CENTROID_CALCULATION_BATCH_SIZE=1000

# Embedding
EMBEDDING_DIMENSION=768

# Monitoramento
ENABLE_PERSONALIZATION_METRICS=true
PERSONALIZATION_LOG_LEVEL=INFO
```

## Uso Básico

### 1. Calcular Centroides

```bash
# Para um tenant específico
make centroids-calculate TENANT=cliente_acme

# Para todos os tenants
make centroids-calculate-all

# Ver estatísticas
make centroids-stats
```

### 2. Usar na Busca

```python
from app.core.rag_bridge import search_documents

# Busca com personalização
results = await search_documents(
    query="Contrato de locação comercial",
    tenant_id="cliente_acme",
    k=20,
    personalization_alpha=0.3,
    enable_personalization=True
)

# Busca sem personalização
results = await search_documents(
    query="Contrato de locação comercial",
    tenant_id="cliente_acme",
    k=20,
    enable_personalization=False
)
```

### 3. API Endpoints

```bash
# Estatísticas de centroides
GET /api/v1/centroids/stats/{tenant_id}

# Calcular centroides
POST /api/v1/centroids/calculate/{tenant_id}

# Testar personalização
POST /api/v1/centroids/test-personalization
{
    "tenant_id": "cliente_acme",
    "query": "Contrato de aluguel",
    "alpha": 0.25
}

# Health check
GET /api/v1/centroids/health
```

## Configuração Avançada

### 1. Automatização com Kubernetes

O sistema inclui CronJobs para automatizar o cálculo de centroides:

```bash
# Aplicar CronJob
kubectl apply -f k8s/cronjob-centroids.yaml

# Verificar status
kubectl get cronjobs -n production
```

### 2. Tags Temáticas Customizadas

```python
from app.config.personalization import get_personalization_settings

settings = get_personalization_settings()

# Adicionar novas tags
settings.default_tags.extend([
    "direito_ambiental",
    "direito_digital",
    "compliance"
])

# Adicionar palavras-chave
settings.tag_keywords["direito_ambiental"] = [
    "meio ambiente", "sustentabilidade", "licença ambiental"
]
```

### 3. Configuração de Performance

```python
# Ajustar parâmetros de personalização
settings.default_personalization_alpha = 0.3  # Personalização mais forte
settings.rrf_k_parameter = 80  # RRF mais conservador
settings.centroid_cache_ttl_seconds = 600  # Cache por 10 minutos
```

## Monitoramento

### 1. Métricas de Sistema

```python
from app.core.personalization import get_personalizer

personalizer = get_personalizer()

# Estatísticas de um tenant
stats = await personalizer.get_personalization_stats("cliente_acme")
print(f"Centroides disponíveis: {stats['total_centroids']}")
print(f"Tags: {[tag['tag'] for tag in stats['tags']]}")
```

### 2. Teste de Carga

```bash
# Teste básico
make centroids-load-test

# Teste completo
make centroids-load-test-full

# Teste customizado
python scripts/test_personalization_load.py \
    --tenants 10 \
    --queries 200 \
    --concurrency 20 \
    --test-centroids \
    --output performance_report.txt
```

### 3. Logs e Debugging

```python
import logging

# Habilitar logs detalhados
logging.getLogger('app.core.personalization').setLevel(logging.DEBUG)
logging.getLogger('app.core.rag_bridge').setLevel(logging.DEBUG)

# Ou via variável de ambiente
PERSONALIZATION_LOG_LEVEL=DEBUG
ENABLE_PERSONALIZATION_DEBUG=true
```

## Troubleshooting

### 1. Problemas Comuns

**Redis não conecta:**
```bash
# Verificar se Redis está rodando
redis-cli ping
# Deve retornar PONG

# Verificar configuração
echo $REDIS_URL
```

**Centroides não encontrados:**
```bash
# Verificar se centroides foram calculados
make centroids-stats

# Recalcular para um tenant
make centroids-calculate TENANT=seu_tenant
```

**Performance lenta:**
```bash
# Verificar métricas
curl http://localhost:8000/api/v1/centroids/health

# Executar teste de carga
make centroids-load-test
```

### 2. Debugging Avançado

```python
# Testar personalização diretamente
from app.core.personalization import test_personalization
await test_personalization()

# Verificar centroide específico
personalizer = get_personalizer()
centroid = await personalizer.get_centroid("tenant_id", "tag")
print(f"Centroide encontrado: {centroid is not None}")

# Testar inferência de tags
tag = await personalizer.infer_query_tag("sua query aqui")
print(f"Tag inferida: {tag}")
```

## Otimização

### 1. Configuração de Produção

```env
# Redis com cluster
REDIS_URL=redis://redis-cluster:6379

# Cache mais agressivo
CENTROID_CACHE_TTL_SECONDS=900

# Batch maior para centroides
CENTROID_CALCULATION_BATCH_SIZE=2000

# Menos logs
PERSONALIZATION_LOG_LEVEL=WARNING
ENABLE_PERSONALIZATION_DEBUG=false
```

### 2. Tuning de Performance

```python
# Ajustar parâmetros baseado no uso
settings.default_personalization_alpha = 0.15  # Menos agressivo
settings.max_k_total = 50  # Limite menor
settings.rrf_k_parameter = 40  # RRF mais agressivo
```

### 3. Monitoramento Contínuo

```bash
# Configurar métricas no Prometheus
# Verificar performance regularmente
make centroids-load-test

# Ajustar configurações baseado nos resultados
```

## Integração com Outros Sistemas

### 1. Sistema de Feedback

```python
# Usar feedback para melhorar centroides
from app.api.v1.feedback import process_feedback

# Feedback positivo aumenta peso do documento no centroide
# Feedback negativo diminui peso ou remove do cálculo
```

### 2. Sistema de Auditoria

```python
# Todas as operações de personalização são auditadas
from app.core.audit import build_and_save_audit_record

# Logs incluem:
# - Tenant ID
# - Query original
# - Parâmetros de personalização
# - Resultados retornados
```

## Exemplo Completo

```python
import asyncio
from app.core.rag_bridge import get_rag_bridge
from scripts.calculate_centroids import CentroidCalculator

async def exemplo_completo():
    # 1. Calcular centroides para um tenant
    calculator = CentroidCalculator()
    results = await calculator.calculate_and_store_centroids("cliente_exemplo")
    print(f"Centroides calculados: {results}")
    
    # 2. Executar busca personalizada
    rag_bridge = get_rag_bridge()
    
    results_personalized = await rag_bridge.federated_search(
        query="Contrato de prestação de serviços",
        tenant_id="cliente_exemplo",
        k_total=10,
        personalization_alpha=0.25,
        enable_personalization=True
    )
    
    # 3. Comparar com busca padrão
    results_standard = await rag_bridge.federated_search(
        query="Contrato de prestação de serviços",
        tenant_id="cliente_exemplo",
        k_total=10,
        enable_personalization=False
    )
    
    # 4. Analisar diferenças
    print(f"Resultados personalizados: {len(results_personalized)}")
    print(f"Resultados padrão: {len(results_standard)}")
    
    if results_personalized:
        print(f"Top resultado personalizado: {results_personalized[0]['rrf_score']:.4f}")
    
    if results_standard:
        print(f"Top resultado padrão: {results_standard[0]['rrf_score']:.4f}")

# Executar exemplo
asyncio.run(exemplo_completo())
```

## Conclusão

O sistema de personalização por centroides permite:

- **Melhor relevância**: Resultados ajustados ao contexto do cliente
- **Flexibilidade**: Parâmetros ajustáveis por tenant
- **Performance**: Cache Redis para acesso rápido
- **Escalabilidade**: Processamento em batch via Kubernetes
- **Monitoramento**: Métricas detalhadas e testes de carga

Para mais informações, consulte o código-fonte em:
- `app/core/personalization.py`
- `app/core/rag_bridge.py`
- `scripts/calculate_centroids.py`
