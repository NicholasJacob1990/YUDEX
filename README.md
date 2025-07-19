# YUDEX - Backend RAG Jurídico "Harvey-Like"

Sistema de RAG jurídico multiagente com API REST para terceiros.

## Estrutura do Projeto

### Frontend
- UI do advogado (web/desktop/plugin)

### Server  
- Backend de negócios (usuários, processos, templates)

### Harvey Backend
- API RAG jurídico para terceiros
- Ingestão de documentos com metadados
- Pipeline multiagente com chunking, embeddings, reranking
- Suporte a múltiplos LLMs (GPT/Claude/Gemini/Local)
- Formatação ABNT e citações automáticas
- Multi-tenant com controle de acesso

## Próximos Passos

1. Configurar dependências Python
2. Implementar schemas Pydantic
3. Configurar FastAPI e endpoints
4. Implementar pipeline RAG
5. Adicionar autenticação multi-tenant
6. Configurar Docker e deploy
