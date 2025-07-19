# Harvey Backend - Sistema RAG Jurídico com Orquestração Dinâmica

## 🎯 Visão Geral

O Harvey Backend é um sistema RAG (Retrieval-Augmented Generation) jurídico que utiliza **orquestração dinâmica de agentes** para produzir documentos jurídicos de alta qualidade. Em vez de um pipeline linear, utiliza um grafo de estados inteligente que decide dinamicamente qual especialista chamar em cada etapa.

## 🏗️ Arquitetura - Onda 1: O Cérebro da Orquestração

### Componentes Principais

1. **GraphState** (`app/orch/state.py`)
   - Scratchpad compartilhado entre todos os agentes
   - Tracking completo de execução e auditoria
   - Métricas de qualidade integradas

2. **Agentes Especializados** (`app/orch/agents.py`)
   - **AnalyzerAgent**: Analisa requisitos e contexto
   - **ResearcherAgent**: Busca informações adicionais
   - **DrafterAgent**: Redige documentos jurídicos
   - **CriticAgent**: Revisa e sugere melhorias
   - **FormatterAgent**: Aplica formatação ABNT

3. **GraphSupervisor** (`app/orch/supervisor.py`)
   - Decide qual agente executar próximo
   - Roteamento inteligente baseado em contexto
   - Condições de parada e fallback

4. **Sistema de Ferramentas** (`app/orch/tools.py`)
   - Registry centralizado de ferramentas
   - Ferramentas para RAG, jurisprudência, formatação
   - Integração com function calling

5. **Integração LangGraph** (`app/orch/langgraph_integration.py`)
   - Wrapper para usar GraphState com LangGraph
   - Orquestração dinâmica de fluxo
   - Checkpointing e recuperação

## 🚀 Como Usar

### 1. Instalação

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações
```

### 2. Execução Básica

```python
from app.orch.state import GraphState, TaskType
from app.orch.langgraph_integration import create_harvey_workflow

# Criar estado inicial
state = GraphState(
    session_id="session_001",
    task_type=TaskType.DOCUMENT_DRAFT,
    tenant_id="advocacia_silva",
    user_id="usuario_123",
    user_query="Redija uma petição inicial para ação de cobrança"
)

# Executar workflow
workflow = create_harvey_workflow()
final_state = await workflow.execute(state)

print(f"Status: {final_state.status}")
print(f"Resultado: {final_state.final_output}")
```

### 3. API FastAPI

```python
# Executar servidor
uvicorn app.main:app --reload

# Fazer requisição
POST /v1/execute
{
    "query": "Redija uma petição inicial para ação de cobrança",
    "task_type": "document_draft",
    "tenant_id": "advocacia_silva",
    "user_id": "usuario_123",
    "requirements": {
        "document_type": "petição",
        "area_direito": "civil"
    }
}
```

### 4. Exemplo Completo

```bash
# Executar exemplo
python example_usage.py
```

## 🔄 Fluxo de Execução

O sistema decide dinamicamente o caminho baseado no contexto:

```
Supervisor → Analyzer → [Researcher?] → Drafter → Critic → [Drafter?] → Formatter → End
```

### Cenários de Execução

1. **Contexto Suficiente**:
   `Analyzer → Drafter → Critic → Formatter`

2. **Precisa Mais Informações**:
   `Analyzer → Researcher → Drafter → Critic → Formatter`

3. **Draft Precisa Revisão**:
   `Analyzer → Drafter → Critic → Drafter → Critic → Formatter`

## 📊 Monitoramento e Auditoria

### Métricas Disponíveis

- **Execução**: iterações, caminho, tempo
- **Qualidade**: context_recall, faithfulness, abnt_compliance
- **Auditoria**: logs forenses, cadeia de custódia

### Endpoints de Debug

- `GET /health` - Status do sistema
- `GET /debug/agents` - Agentes disponíveis
- `GET /debug/tools` - Ferramentas registradas

## 🛠️ Configuração

### Variáveis de Ambiente Principais

```bash
# LLM Configuration
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Vector Database
QDRANT_URL=http://localhost:6333

# Graph Execution
GRAPH_MAX_ITERATIONS=10
GRAPH_TIMEOUT_SECONDS=300
```

### Configuração de Agentes

```python
# Personalizar comportamento dos agentes
config = {
    "max_iterations": 10,
    "timeout": 300,
    "model_preferences": {
        "analyzer": "claude-3-sonnet",
        "drafter": "gpt-4",
        "critic": "claude-3-sonnet"
    }
}
```

## 🔧 Desenvolvimento

### Estrutura de Pastas

```
harvey_backend/
├── app/
│   ├── orch/              # Orquestração dinâmica
│   │   ├── state.py       # Estado compartilhado
│   │   ├── agents.py      # Agentes especializados
│   │   ├── supervisor.py  # Roteamento inteligente
│   │   ├── tools.py       # Sistema de ferramentas
│   │   └── langgraph_integration.py
│   ├── core/              # Módulos base (RAG, LLM, etc.)
│   ├── api/               # Endpoints FastAPI
│   └── main.py            # Aplicação principal
├── tests/
├── example_usage.py       # Exemplo de uso
└── requirements.txt
```

### Adicionando Novos Agentes

1. Criar classe herdando de `BaseAgent`
2. Implementar `_execute_logic`
3. Registrar no supervisor
4. Adicionar ao workflow

### Adicionando Novas Ferramentas

1. Criar classe herdando de `BaseTool`
2. Implementar `get_schema` e `execute`
3. Registrar no `ToolRegistry`

## 📈 Próximos Passos

### Onda 2 - Inteligência Ativa
- [ ] Implementar módulos `core/` completos
- [ ] Conectar ferramentas aos serviços reais
- [ ] Framework de avaliação automática

### Onda 3 - Feedback e Segurança
- [ ] Endpoint de feedback humano
- [ ] Auditoria forense avançada
- [ ] Detecção de PII e compliance

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---

**Harvey Backend** - Transformando a advocacia com IA multiagente 🚀
