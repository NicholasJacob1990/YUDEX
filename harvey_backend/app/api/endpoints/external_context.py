"""
Endpoints para gerenciamento de contexto externo
Permite que clientes enviem documentos específicos do caso junto com consultas
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from app.models.schema_api import (
    ExternalDoc, 
    ExternalDocValidationResult, 
    ExternalDocProcessor,
    GenerationRequest, 
    GenerationResponse
)
from app.core.rag_bridge import get_rag_bridge
from app.core.auth import get_current_tenant_id

router = APIRouter(prefix="/external-context", tags=["external-context"])
security = HTTPBearer()
logger = logging.getLogger(__name__)

@router.post("/validate", response_model=ExternalDocValidationResult)
async def validate_external_docs(
    docs: List[ExternalDoc],
    tenant_id: str = Security(get_current_tenant_id),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Valida documentos externos antes de processamento
    
    Args:
        docs: Lista de documentos externos para validação
        tenant_id: ID do tenant (extraído do token)
        credentials: Credenciais de autenticação
        
    Returns:
        Resultado da validação com estatísticas e possíveis erros
    """
    try:
        logger.info(f"Validando {len(docs)} documentos externos para tenant {tenant_id}")
        
        # Validar documentos
        validation_result = ExternalDocProcessor.validate_docs(docs)
        
        if not validation_result.valid:
            logger.warning(f"Documentos inválidos: {validation_result.validation_errors}")
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Erro na validação de documentos externos: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Erro na validação: {str(e)}"
        )

@router.post("/test-search")
async def test_search_with_external_context(
    request: Dict[str, Any],
    tenant_id: str = Security(get_current_tenant_id),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Testa busca com contexto externo sem gerar documento completo
    
    Args:
        request: Requisição contendo query e documentos externos
        tenant_id: ID do tenant
        credentials: Credenciais de autenticação
        
    Returns:
        Resultados da busca federada com contexto externo
    """
    try:
        query = request.get("query")
        external_docs = request.get("external_docs", [])
        
        if not query:
            raise HTTPException(
                status_code=400,
                detail="Query é obrigatória"
            )
        
        # Converter para objetos ExternalDoc
        external_doc_objs = [ExternalDoc(**doc) for doc in external_docs]
        
        # Validar documentos
        validation_result = ExternalDocProcessor.validate_docs(external_doc_objs)
        if not validation_result.valid:
            raise HTTPException(
                status_code=400,
                detail=f"Documentos inválidos: {validation_result.validation_errors}"
            )
        
        # Preparar para RAG
        processed_docs = ExternalDocProcessor.prepare_for_rag(external_doc_objs)
        
        # Executar busca
        rag_bridge = get_rag_bridge()
        results = await rag_bridge.federated_search(
            query=query,
            tenant_id=tenant_id,
            k_total=20,
            external_docs=processed_docs,
            use_internal_rag=True
        )
        
        # Preparar resposta
        response = {
            "query": query,
            "total_results": len(results),
            "external_docs_provided": len(external_doc_objs),
            "external_docs_used": len([r for r in results if r.get("source") == "external"]),
            "internal_docs_used": len([r for r in results if r.get("source") != "external"]),
            "results": results[:10],  # Limitar para teste
            "validation_info": validation_result.dict()
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no teste de busca: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )

@router.post("/generate", response_model=GenerationResponse)
async def generate_with_external_context(
    request: GenerationRequest,
    tenant_id: str = Security(get_current_tenant_id),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Gera documento jurídico usando contexto externo
    
    Args:
        request: Requisição completa com query, configurações e documentos externos
        tenant_id: ID do tenant
        credentials: Credenciais de autenticação
        
    Returns:
        Resposta com documento gerado e metadados de contexto
    """
    try:
        logger.info(f"Gerando documento com contexto externo para tenant {tenant_id}")
        logger.info(f"Query: {request.query}")
        logger.info(f"Documentos externos: {len(request.context_docs_external or [])}")
        
        # Validar documentos externos se fornecidos
        if request.context_docs_external:
            validation_result = ExternalDocProcessor.validate_docs(request.context_docs_external)
            if not validation_result.valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Documentos externos inválidos: {validation_result.validation_errors}"
                )
        
        # Montar configuração para o workflow
        config = {
            "context_docs_external": request.context_docs_external,
            "use_internal_rag": request.use_internal_rag,
            "rag_config": {
                "k_total": request.k_total,
                "enable_personalization": request.enable_personalization,
                "personalization_alpha": request.personalization_alpha
            },
            "doc_type": request.doc_type,
            "format_style": request.format_style,
            "additional_instructions": request.additional_instructions
        }
        
        # TODO: Integrar com o workflow LangGraph
        # Por enquanto, simular resposta
        
        # Estatísticas simuladas
        context_summary = {
            "context_type": "hybrid" if request.context_docs_external and request.use_internal_rag else
                           "external_only" if request.context_docs_external else "internal_only",
            "total_documents": 15,
            "internal_documents": 10,
            "external_documents": len(request.context_docs_external or []),
            "personalization_enabled": request.enable_personalization,
            "execution_time": 2.5
        }
        
        # Documentos externos usados (simulado)
        external_docs_used = []
        if request.context_docs_external:
            external_docs_used = [
                {
                    "src_id": doc.src_id,
                    "score": 0.85,
                    "rank": i + 1,
                    "text_overlap": 0.3
                }
                for i, doc in enumerate(request.context_docs_external[:3])
            ]
        
        # Simular resultado
        response = GenerationResponse(
            run_id=f"run_{tenant_id}_{hash(request.query) % 10000}",
            query=request.query,
            doc_type=request.doc_type,
            generated_text=f"""# PARECER JURÍDICO

## I. Consulta
{request.query}

## II. Análise
Com base nos documentos fornecidos e na base de conhecimento jurídica, análise detalhada...

## III. Fundamentação
[Contexto externo considerado: {len(request.context_docs_external or [])} documentos]

## IV. Conclusão
Conclusão baseada em análise híbrida de fontes internas e externas.

---
*Documento gerado com contexto externo*
""",
            context_summary=context_summary,
            external_docs_used=external_docs_used,
            supervisor_notes=[
                "Análise macro concluída. Complexidade: média",
                f"Contexto externo considerado: {len(request.context_docs_external or [])} documentos",
                "RAG Bridge executado em 2.5s",
                "Personalização aplicada (α=0.25)"
            ],
            execution_time=2.5
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na geração com contexto externo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )

@router.get("/stats/{tenant_id}")
async def get_external_context_stats(
    tenant_id: str,
    current_tenant: str = Security(get_current_tenant_id),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Obtém estatísticas de uso de contexto externo
    
    Args:
        tenant_id: ID do tenant para consulta
        current_tenant: Tenant atual (validação)
        credentials: Credenciais de autenticação
        
    Returns:
        Estatísticas de uso de contexto externo
    """
    try:
        # Validar acesso
        if current_tenant != tenant_id:
            raise HTTPException(
                status_code=403,
                detail="Acesso negado"
            )
        
        # TODO: Implementar busca real de estatísticas
        # Por enquanto, retornar dados simulados
        
        stats = {
            "tenant_id": tenant_id,
            "total_requests_with_external_context": 45,
            "total_external_docs_processed": 234,
            "avg_external_docs_per_request": 5.2,
            "most_used_doc_types": ["contrato", "lei", "jurisprudencia"],
            "avg_processing_time": 3.2,
            "success_rate": 0.98,
            "last_30_days": {
                "requests": 12,
                "docs": 67,
                "avg_time": 2.8
            }
        }
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )

@router.post("/preview")
async def preview_external_context_processing(
    docs: List[ExternalDoc],
    tenant_id: str = Security(get_current_tenant_id),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Pré-visualiza como os documentos externos serão processados
    
    Args:
        docs: Lista de documentos externos
        tenant_id: ID do tenant
        credentials: Credenciais de autenticação
        
    Returns:
        Preview do processamento com estatísticas e amostras
    """
    try:
        logger.info(f"Gerando preview de {len(docs)} documentos para tenant {tenant_id}")
        
        # Validar documentos
        validation_result = ExternalDocProcessor.validate_docs(docs)
        
        # Preparar para RAG
        processed_docs = ExternalDocProcessor.prepare_for_rag(docs)
        
        # Gerar preview
        preview = {
            "validation": validation_result.dict(),
            "processing_preview": {
                "total_documents": len(processed_docs),
                "total_chunks": sum(len(doc.get("chunks", [])) for doc in processed_docs),
                "estimated_tokens": sum(doc.get("estimated_tokens", 0) for doc in processed_docs),
                "processing_time_estimate": len(processed_docs) * 0.5,  # Estimativa
                "document_samples": [
                    {
                        "src_id": doc.get("src_id"),
                        "chunks_count": len(doc.get("chunks", [])),
                        "first_chunk_preview": doc.get("chunks", [{}])[0].get("text", "")[:200] + "..." if doc.get("chunks") else "",
                        "metadata": doc.get("metadata", {})
                    }
                    for doc in processed_docs[:3]  # Primeiros 3 para preview
                ]
            }
        }
        
        return preview
        
    except Exception as e:
        logger.error(f"Erro no preview: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )

# Função auxiliar para testing
async def test_external_context_endpoint():
    """
    Testa endpoints de contexto externo
    """
    from app.models.schema_api import ExternalDoc
    
    test_docs = [
        ExternalDoc(
            src_id="contract_001",
            text="Contrato de prestação de serviços com cláusula de confidencialidade...",
            meta={"tipo": "contrato", "data": "2024-01-15"}
        ),
        ExternalDoc(
            src_id="incident_report",
            text="Relatório de incidente de segurança com vazamento de dados...",
            meta={"tipo": "incidente", "gravidade": "alta"}
        )
    ]
    
    # Testar validação
    validation_result = ExternalDocProcessor.validate_docs(test_docs)
    print(f"Validação: {validation_result.valid}")
    print(f"Erros: {validation_result.validation_errors}")
    
    # Testar processamento
    processed = ExternalDocProcessor.prepare_for_rag(test_docs)
    print(f"Processados: {len(processed)} documentos")
    
    return {"validation": validation_result, "processed": processed}

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_external_context_endpoint())
