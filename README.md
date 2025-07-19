# YUDEX - Sistema de Geração de Documentos Jurídicos

🏛️ **Sistema avançado de RAG jurídico com workflow multiagente para geração inteligente de documentos legais**

## 📋 Visão Geral

O YUDEX é uma plataforma completa para geração automatizada de documentos jurídicos, utilizando tecnologias de ponta como RAG (Retrieval-Augmented Generation), LangGraph workflows e agentes especializados. O sistema combina busca federada, personalização por usuário e processamento multiagente para criar documentos jurídicos de alta qualidade.

## 🚀 Funcionalidades Principais

### 🔍 Sistema RAG Avançado
- **Busca Federada**: Combinação inteligente de multiple sources
- **Personalização**: Contexto adaptado por usuário/organização
- **Reranking**: Otimização da relevância dos documentos
- **Embeddings**: Busca semântica de alta precisão

### 🤖 Workflow Multiagente (LangGraph)
- **Agente Analista**: Análise inicial da consulta e contexto
- **Agente Redator**: Criação do documento base
- **Agente Crítico**: Revisão e refinamento
- **Supervisor**: Coordenação e controle de qualidade

### 📄 Geração de Documentos
- **Tipos Suportados**: Pareceres, contratos, petições, memorandos
- **Formatação ABNT**: Citações e referências automáticas
- **Personalização**: Estilos e seções configuráveis
- **Streaming**: Geração em tempo real com progresso

### 🔐 Segurança e Multi-tenancy
- **Controle de Acesso**: Autenticação e autorização robustas
- **Isolamento**: Dados separados por tenant
- **Auditoria**: Log completo de operações
- **PII Protection**: Proteção de dados sensíveis

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Frontend     │    │     Server      │    │ Harvey Backend  │
│   (UI/UX)      │◄───┤   (Business)    │◄───┤   (RAG/AI)     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Harvey Backend (Core)
- **API REST**: Endpoints para geração e gestão
- **Pipeline RAG**: Chunking, embeddings, retrieval
- **Workflows**: LangGraph para orquestração de agentes
- **LLM Router**: Suporte múltiplos providers (OpenAI, Anthropic, etc.)
- **Vector Database**: Armazenamento e busca de embeddings

## 🛠️ Tecnologias

- **Backend**: Python 3.11+, FastAPI, Pydantic
- **AI/ML**: LangChain, LangGraph, OpenAI, Anthropic
- **Database**: PostgreSQL, Pinecone/Chroma (vetores)
- **Cache**: Redis
- **Container**: Docker, Kubernetes
- **Monitoring**: Prometheus, Grafana

## 📁 Estrutura do Projeto

```
yudex/
├── harvey_backend/          # Core RAG/AI Backend
│   ├── app/
│   │   ├── api/            # REST API endpoints
│   │   ├── core/           # Business logic
│   │   ├── orch/           # LangGraph workflows
│   │   ├── models/         # Data schemas
│   │   └── security/       # Auth & security
│   ├── configs/            # Configurations
│   ├── docs/              # Documentation
│   ├── scripts/           # Utility scripts
│   └── tests/             # Test suites
├── frontend/               # Web interface
├── server/                # Business backend
└── yudex_backend/         # Legacy/migration
```

## 🚀 Quick Start

### 1. Clone e Setup
```bash
git clone https://github.com/NicholasJacob1990/YUDEX.git
cd YUDEX/harvey_backend
```

### 2. Configuração de Ambiente
```bash
# Copie o arquivo de configuração
cp .env.example .env

# Configure as variáveis necessárias
# - API keys (OpenAI, Anthropic, etc.)
# - Database URLs
# - Vector database config
```

### 3. Instalação de Dependências
```bash
# Via pip
pip install -r requirements.txt

# Via Docker
docker-compose -f docker-compose.dev.yml up -d
```

### 4. Executar o Sistema
```bash
# Desenvolvimento
uvicorn app.main:app --reload --port 8000

# Produção
docker-compose up -d
```

## 📚 API Endpoints

### Geração de Documentos
- `POST /api/v1/generate` - Geração síncrona
- `POST /api/v1/stream` - Geração com streaming
- `GET /api/v1/generate/status/{id}` - Status da geração
- `GET /api/v1/generate/result/{id}` - Resultado da geração

### Ingestão de Documentos
- `POST /api/v1/ingest/document` - Upload de documento
- `POST /api/v1/ingest/batch` - Upload em lote
- `GET /api/v1/ingest/status/{id}` - Status da ingestão

### Feedback e Melhoria
- `POST /api/v1/feedback` - Feedback do usuário
- `GET /api/v1/feedback/analytics` - Análise de feedback

## 🔧 Configuração

### Variáveis de Ambiente Principais
```env
# API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Database
DATABASE_URL=postgresql://user:pass@localhost/yudex
VECTOR_DATABASE_URL=your_vector_db_url

# Redis
REDIS_URL=redis://localhost:6379

# Security
JWT_SECRET_KEY=your_secret_key
ENCRYPTION_KEY=your_encryption_key
```

### Configuração de Modelos
Edite `configs/models_catalog.json` para configurar os LLMs disponíveis.

## 📖 Documentação

- [Runbook Operacional](harvey_backend/docs/RUNBOOK.md)
- [Personalização](harvey_backend/docs/personalization.md)
- [Contexto Externo](harvey_backend/docs/external_context.md)

## 🧪 Testes

```bash
# Executar todos os testes
pytest

# Testes específicos
pytest tests/test_generation.py
pytest tests/test_rag_pipeline.py

# Teste de integração
python test_real_system.py
```

## 🚀 Deploy

### Docker
```bash
docker build -t yudex-harvey .
docker run -p 8000:8000 yudex-harvey
```

### Kubernetes
```bash
kubectl apply -f k8s/
```

### Helm
```bash
helm install yudex ./helm/harvey
```

## 🤝 Contribuição

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para detalhes.

## 📞 Contato

Nicholas Jacob - [@NicholasJacob1990](https://github.com/NicholasJacob1990)

Project Link: [https://github.com/NicholasJacob1990/YUDEX](https://github.com/NicholasJacob1990/YUDEX)

## 🏆 Status do Projeto

- ✅ **Core RAG Pipeline**: Implementado
- ✅ **LangGraph Workflows**: Implementado  
- ✅ **API REST**: Implementado
- ✅ **Multi-tenancy**: Implementado
- 🔄 **Frontend Web**: Em desenvolvimento
- 🔄 **Mobile App**: Planejado
- 🔄 **Plugins IDE**: Planejado

## 📊 Roadmap

### v1.0 (Atual)
- [x] Sistema RAG básico
- [x] Workflow multiagente
- [x] API REST completa
- [x] Containerização

### v1.1 (Próximo)
- [ ] Interface web
- [ ] Métricas avançadas
- [ ] Otimizações de performance
- [ ] Testes automatizados

### v2.0 (Futuro)
- [ ] Mobile apps
- [ ] Plugins para IDEs jurídicos
- [ ] Integração com sistemas legais
- [ ] AI features avançadas
