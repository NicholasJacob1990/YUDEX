# Sistema de Contexto Externo - Harvey Backend

## Visão Geral

O sistema de contexto externo permite que clientes enviem documentos específicos do caso junto com suas consultas, possibilitando análises mais precisas e personalizadas. O sistema processa documentos externos, os integra com a base de conhecimento interna e os utiliza na geração de documentos jurídicos.

## Funcionalidades Principais

### 1. Processamento de Documentos Externos
- **Validação automática** de documentos enviados
- **Chunking inteligente** para otimizar busca
- **Metadados estruturados** para contexto adicional
- **Verificação de limites** de tamanho e quantidade

### 2. Integração com RAG Bridge
- **Busca federada** entre fontes internas e externas
- **Pontuação híbrida** com RRF (Reciprocal Rank Fusion)
- **Priorização configurável** de fontes
- **Personalização baseada em centroides**

### 3. API Completa
- **Endpoints dedicados** para validação e processamento
- **Schemas Pydantic** para validação rigorosa
- **Respostas detalhadas** com metadados de contexto
- **Tratamento de erros** robusto

## Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Client    │───▶│  External Doc   │───▶│   RAG Bridge    │
│                 │    │   Processor     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LangGraph     │◀───│  Context Node   │◀───│  Federated      │
│   Workflow      │    │                 │    │   Search        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Modelos de Dados

### ExternalDoc
```python
from app.models.schema_api import ExternalDoc

doc = ExternalDoc(
    src_id="contract_001",
    text="Contrato de prestação de serviços...",
    meta={
        "tipo": "contrato",
        "data": "2024-01-15",
        "partes": ["Empresa A", "Empresa B"]
    }
)
```

### GenerationRequest
```python
from app.models.schema_api import GenerationRequest, ExternalDoc

request = GenerationRequest(
    query="Analisar cláusula de responsabilidade",
    context_docs_external=[
        ExternalDoc(
            src_id="contract_001",
            text="Contrato principal...",
            meta={"tipo": "contrato"}
        )
    ],
    use_internal_rag=True,
    k_total=20,
    enable_personalization=True,
    doc_type="parecer"
)
```

### GenerationResponse
```python
# Resposta automática com contexto externo
{
    "run_id": "run_cliente_abc_1234",
    "query": "Analisar cláusula de responsabilidade",
    "doc_type": "parecer",
    "generated_text": "# PARECER JURÍDICO\n\n...",
    "context_summary": {
        "context_type": "hybrid",
        "total_documents": 15,
        "internal_documents": 12,
        "external_documents": 3,
        "personalization_enabled": true
    },
    "external_docs_used": [
        {
            "src_id": "contract_001",
            "score": 0.85,
            "rank": 1,
            "text_overlap": 0.3
        }
    ],
    "execution_time": 2.5
}
```

## Exemplos de Uso

### 1. Validação de Documentos

```python
from app.models.schema_api import ExternalDoc, ExternalDocProcessor

# Preparar documentos
docs = [
    ExternalDoc(
        src_id="incident_report",
        text="Relatório de incidente de segurança...",
        meta={"tipo": "incidente", "gravidade": "alta"}
    ),
    ExternalDoc(
        src_id="policy_document",
        text="Política de segurança da empresa...",
        meta={"tipo": "politica", "versao": "2.1"}
    )
]

# Validar documentos
validation = ExternalDocProcessor.validate_docs(docs)

if validation.valid:
    print(f"✅ {validation.total_docs} documentos válidos")
    print(f"📊 {validation.total_characters} caracteres")
    print(f"🔤 {validation.estimated_tokens} tokens estimados")
else:
    print(f"❌ Erros: {validation.validation_errors}")
```

### 2. Busca com Contexto Externo

```python
from app.core.rag_bridge import get_rag_bridge
from app.models.schema_api import ExternalDocProcessor

# Processar documentos para RAG
processed_docs = ExternalDocProcessor.prepare_for_rag(docs)

# Executar busca federada
rag_bridge = get_rag_bridge()
results = await rag_bridge.federated_search(
    query="Responsabilidade por vazamento de dados",
    tenant_id="cliente_xyz",
    k_total=20,
    external_docs=processed_docs,
    use_internal_rag=True,
    enable_personalization=True
)

# Analisar resultados
for doc in results:
    print(f"📄 {doc['src_id']} - Score: {doc['score']:.3f}")
    print(f"   Fonte: {doc['source']}")
    print(f"   Rank: {doc['final_rank']}")
```

### 3. Workflow Completo

```python
from app.orch.harvey_workflow import HarveyToolsWorkflow
from app.models.schema_api import ExternalDoc

# Criar workflow
workflow = HarveyToolsWorkflow()

# Documentos do cliente
external_docs = [
    ExternalDoc(
        src_id="case_file_001",
        text="Processo judicial sobre...",
        meta={"tipo": "processo", "numero": "123456"}
    ),
    ExternalDoc(
        src_id="expert_opinion",
        text="Parecer técnico de especialista...",
        meta={"tipo": "parecer", "especialista": "Dr. João"}
    )
]

# Processar requisição
result = await workflow.process_request(
    request="Elaborar defesa baseada nos documentos fornecidos",
    external_docs=external_docs
)

print(f"📝 Documento gerado: {len(result['content'])} caracteres")
print(f"🎯 Qualidade: {result['quality_score']:.2f}")
print(f"📊 Contexto: {result['context_metadata']}")
```

### 4. API Endpoints

```python
# Endpoint para validação
POST /external-context/validate
{
    "docs": [
        {
            "src_id": "contract_001",
            "text": "Contrato de prestação...",
            "meta": {"tipo": "contrato"}
        }
    ]
}

# Endpoint para geração com contexto
POST /external-context/generate
{
    "query": "Analisar cláusula de responsabilidade",
    "context_docs_external": [
        {
            "src_id": "contract_001",
            "text": "Contrato principal...",
            "meta": {"tipo": "contrato"}
        }
    ],
    "use_internal_rag": true,
    "k_total": 20,
    "enable_personalization": true,
    "doc_type": "parecer"
}

# Endpoint para teste de busca
POST /external-context/test-search
{
    "query": "responsabilidade contratual",
    "external_docs": [
        {
            "src_id": "contract_001",
            "text": "Contrato com cláusulas...",
            "meta": {"tipo": "contrato"}
        }
    ]
}
```

## Configuração e Personalização

### Parâmetros de Busca
- `k_total`: Número total de documentos a recuperar (padrão: 20)
- `enable_personalization`: Ativar personalização baseada em centroides
- `personalization_alpha`: Peso da personalização (0.0-1.0, padrão: 0.25)
- `use_internal_rag`: Usar base de conhecimento interna junto com externos

### Limites e Validação
- **Tamanho máximo por documento**: 500KB
- **Número máximo de documentos**: 10 por requisição
- **Total de caracteres**: 2MB por requisição
- **Validação de ID**: IDs únicos obrigatórios

### Chunking Inteligente
```python
# Configuração de chunking
chunk_size = 1000        # Caracteres por chunk
chunk_overlap = 200      # Sobreposição entre chunks
min_chunk_size = 100     # Tamanho mínimo do chunk
```

## Integração com LangGraph

### Nó de Validação
```python
from app.orch.rag_node import context_validator_node

# Validar contexto externo
state = {
    "config": {
        "context_docs_external": external_docs
    }
}

result = await context_validator_node(state)
```

### Nó RAG
```python
from app.orch.rag_node import rag_node

# Executar busca com contexto
state = {
    "initial_query": "consulta do cliente",
    "tenant_id": "cliente_abc",
    "config": {
        "context_docs_external": external_docs,
        "use_internal_rag": True,
        "rag_config": {
            "k_total": 20,
            "enable_personalization": True
        }
    }
}

result = await rag_node(state)
```

## Monitoramento e Métricas

### Estatísticas de Uso
```python
# Obter estatísticas
GET /external-context/stats/{tenant_id}

{
    "total_requests_with_external_context": 45,
    "total_external_docs_processed": 234,
    "avg_external_docs_per_request": 5.2,
    "avg_processing_time": 3.2,
    "success_rate": 0.98
}
```

### Logs e Debugging
```python
import logging

logger = logging.getLogger(__name__)

# Logs automáticos incluem:
# - Validação de documentos
# - Processamento de chunks
# - Resultados de busca
# - Tempos de execução
# - Erros e warnings
```

## Tratamento de Erros

### Erros Comuns
- **Documentos inválidos**: Formato incorreto ou muito grandes
- **IDs duplicados**: Mesmo src_id em múltiplos documentos
- **Limite excedido**: Muito documentos ou caracteres
- **Falha na busca**: Problemas na integração com RAG

### Códigos de Erro
- `400`: Dados inválidos na requisição
- `413`: Payload muito grande
- `422`: Erro de validação
- `500`: Erro interno do servidor

## Testes

### Executar Testes
```bash
# Testes unitários
pytest tests/test_external_context.py -v

# Testes de integração
python tests/test_external_context.py

# Testes de performance
pytest tests/test_external_context.py::TestPerformance -v
```

### Casos de Teste
- ✅ Validação de documentos válidos
- ✅ Rejeição de documentos inválidos
- ✅ Processamento de chunks
- ✅ Integração com RAG Bridge
- ✅ Workflow completo
- ✅ Tratamento de erros

## Roadmap

### Fase 1 - Implementação Básica ✅
- [x] Processamento de documentos externos
- [x] Integração com RAG Bridge
- [x] Endpoints da API
- [x] Testes básicos

### Fase 2 - Melhorias (Próximas)
- [ ] Cache de documentos processados
- [ ] Análise de relevância melhorada
- [ ] Suporte a mais formatos (PDF, DOCX)
- [ ] Metrics detalhadas

### Fase 3 - Otimizações (Futuro)
- [ ] Processamento em background
- [ ] Compressão de contexto
- [ ] ML para relevância
- [ ] Dashboard de monitoramento

## Conclusão

O sistema de contexto externo do Harvey Backend fornece uma solução robusta e flexível para integração de documentos específicos do cliente no processo de geração de documentos jurídicos. Com validação rigorosa, processamento eficiente e integração seamless com o workflow existente, permite análises mais precisas e personalizadas.

Para dúvidas ou sugestões, consulte a documentação da API ou entre em contato com a equipe de desenvolvimento.
