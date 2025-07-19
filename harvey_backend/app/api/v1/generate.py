"""
POST /generate - Geração síncrona
Endpoint para geração síncrona de documentos jurídicos
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from ...models.schema_api import (
    GenerationRequest, GenerationResponse, 
    ExternalDoc, DocumentConfig
)
from ...core.rag_bridge import get_federated_search
from ...orch.harvey_workflow import create_harvey_workflow
from ...config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["generation"])


class GenerationStatus(BaseModel):
    """Status da geração"""
    status: str  # pending, processing, completed, error
    progress: float = Field(ge=0.0, le=1.0)
    message: str = ""
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_details: Optional[str] = None


class GenerationMetrics(BaseModel):
    """Métricas da geração"""
    retrieval_time: float
    processing_time: float
    total_time: float
    documents_retrieved: int
    external_docs_used: int
    workflow_iterations: int
    tokens_used: Optional[int] = None


# Cache global para status de gerações
generation_status_cache: Dict[str, GenerationStatus] = {}
generation_results_cache: Dict[str, GenerationResponse] = {}


@router.post("/generate", response_model=GenerationResponse)
async def generate_document(
    request: GenerationRequest,
    background_tasks: BackgroundTasks
) -> GenerationResponse:
    """
    Gera documento jurídico usando o workflow Harvey
    
    Este endpoint executa o pipeline completo:
    1. Busca documentos relevantes (RAG)
    2. Executa workflow LangGraph com agentes especializados
    3. Retorna documento jurídico estruturado
    """
    import uuid
    import time
    
    generation_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        logger.info(f"Iniciando geração {generation_id} para query: {request.query[:100]}")
        
        # Registra status inicial
        generation_status_cache[generation_id] = GenerationStatus(
            status="processing",
            progress=0.0,
            message="Iniciando geração...",
            started_at=datetime.now()
        )
        
        # 1. Prepara contexto externo se fornecido
        external_context = None
        external_docs_used = []
        
        if request.context_docs_external:
            logger.info(f"Processando {len(request.context_docs_external)} documentos externos")
            
            # Valida documentos externos
            validated_docs = []
            for doc in request.context_docs_external:
                if isinstance(doc, dict):
                    validated_docs.append(ExternalDoc(**doc))
                else:
                    validated_docs.append(doc)
            
            # Prepara contexto externo para o workflow
            external_context = {
                'docs': validated_docs,
                'metadata': {
                    'context_type': 'external',
                    'doc_count': len(validated_docs),
                    'provided_at': datetime.now().isoformat()
                }
            }
            external_docs_used = validated_docs
        
        # Atualiza progresso
        generation_status_cache[generation_id].progress = 0.2
        generation_status_cache[generation_id].message = "Buscando documentos relevantes..."
        
        # 2. Busca federated (RAG + personalization)
        search_start = time.time()
        
        federated_search = get_federated_search()
        rag_results = await federated_search(
            query=request.query,
            user_id=request.user_id,
            limit=settings.max_docs_retrieval,
            external_docs=validated_docs if request.context_docs_external else None
        )
        
        search_time = time.time() - search_start
        
        logger.info(f"Busca federated concluída: {len(rag_results)} documentos em {search_time:.2f}s")
        
        # Atualiza progresso
        generation_status_cache[generation_id].progress = 0.4
        generation_status_cache[generation_id].message = "Executando workflow de geração..."
        
        # 3. Prepara configuração do documento
        doc_config = request.config or DocumentConfig()
        
        # 4. Cria e executa workflow Harvey
        workflow_start = time.time()
        
        workflow = create_harvey_workflow()
        
        # Estado inicial do workflow
        initial_state = {
            "initial_query": request.query,
            "rag_docs": [
                {
                    "content": doc.content,
                    "source": doc.metadata.source if hasattr(doc, 'metadata') else "unknown",
                    "score": getattr(doc, 'score', 1.0)
                }
                for doc in rag_results
            ],
            "config": {
                "document_type": doc_config.document_type,
                "style": doc_config.style,
                "sections": doc_config.sections,
                "max_length": doc_config.max_length,
                "include_citations": doc_config.include_citations,
                "abnt_formatting": doc_config.abnt_formatting
            },
            "user_id": request.user_id,
            "generation_id": generation_id,
            "external_context": external_context,
            "external_docs_used": [
                {
                    "src_id": doc.src_id,
                    "content": doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,
                    "score": getattr(doc, 'score', 1.0)
                }
                for doc in external_docs_used
            ],
            "context_metadata": external_context.get('metadata', {}) if external_context else {},
            "supervisor_notes": [],
            "critic_reports": []
        }
        
        # Callback para atualizar progresso
        def update_progress(step: str, progress: float):
            if generation_id in generation_status_cache:
                generation_status_cache[generation_id].progress = 0.4 + (progress * 0.5)
                generation_status_cache[generation_id].message = f"Workflow: {step}"
        
        # Executa workflow
        try:
            final_state = await workflow.ainvoke(
                initial_state,
                config={
                    "configurable": {
                        "thread_id": generation_id,
                        "progress_callback": update_progress
                    }
                }
            )
        except Exception as workflow_error:
            logger.error(f"Erro no workflow: {workflow_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro no workflow de geração: {str(workflow_error)}"
            )
        
        workflow_time = time.time() - workflow_start
        
        # Atualiza progresso
        generation_status_cache[generation_id].progress = 0.9
        generation_status_cache[generation_id].message = "Finalizando documento..."
        
        # 5. Extrai resultado do workflow
        final_text = final_state.get("final_text", "")
        if not final_text:
            # Fallback para texto do critic ou draft
            final_text = (
                final_state.get("critic_latest_markdown") or 
                final_state.get("draft_markdown") or
                "Erro: Não foi possível gerar o documento."
            )
        
        # 6. Prepara resposta
        total_time = time.time() - start_time
        
        # Extrai metadados do workflow
        workflow_metadata = {
            "supervisor_notes": final_state.get("supervisor_notes", []),
            "critic_reports": final_state.get("critic_reports", []),
            "analysis": final_state.get("analysis", {}),
            "workflow_iterations": len(final_state.get("supervisor_notes", [])),
            "external_context_used": bool(external_docs_used)
        }
        
        metrics = GenerationMetrics(
            retrieval_time=search_time,
            processing_time=workflow_time,
            total_time=total_time,
            documents_retrieved=len(rag_results),
            external_docs_used=len(external_docs_used),
            workflow_iterations=workflow_metadata["workflow_iterations"]
        )
        
        response = GenerationResponse(
            generation_id=generation_id,
            generated_text=final_text,
            query=request.query,
            config=doc_config,
            documents_used=[
                {
                    "source": doc.get("source", "unknown"),
                    "score": doc.get("score", 0.0),
                    "content_preview": doc.get("content", "")[:200] + "..." if len(doc.get("content", "")) > 200 else doc.get("content", "")
                }
                for doc in rag_results[:10]  # Limita a 10 para não sobrecarregar
            ],
            external_docs_used=[
                {
                    "src_id": doc.src_id,
                    "title": getattr(doc, 'title', ''),
                    "content_preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
                }
                for doc in external_docs_used
            ],
            metadata=workflow_metadata,
            metrics={
                "retrieval_time": metrics.retrieval_time,
                "processing_time": metrics.processing_time,
                "total_time": metrics.total_time,
                "documents_retrieved": metrics.documents_retrieved,
                "external_docs_used": metrics.external_docs_used,
                "workflow_iterations": metrics.workflow_iterations
            },
            created_at=datetime.now()
        )
        
        # Atualiza status final
        generation_status_cache[generation_id] = GenerationStatus(
            status="completed",
            progress=1.0,
            message="Documento gerado com sucesso",
            started_at=generation_status_cache[generation_id].started_at,
            completed_at=datetime.now()
        )
        
        # Cache resultado
        generation_results_cache[generation_id] = response
        
        # Limpa caches antigos em background
        background_tasks.add_task(cleanup_old_cache_entries)
        
        logger.info(f"Geração {generation_id} concluída em {total_time:.2f}s")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Erro na geração {generation_id}: {e}")
        
        # Atualiza status de erro
        if generation_id in generation_status_cache:
            generation_status_cache[generation_id].status = "error"
            generation_status_cache[generation_id].message = "Erro na geração"
            generation_status_cache[generation_id].error_details = str(e)
            generation_status_cache[generation_id].completed_at = datetime.now()
        
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno na geração: {str(e)}"
        )


@router.get("/generate/status/{generation_id}", response_model=GenerationStatus)
async def get_generation_status(generation_id: str) -> GenerationStatus:
    """
    Consulta status de uma geração em andamento
    """
    if generation_id not in generation_status_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Geração {generation_id} não encontrada"
        )
    
    return generation_status_cache[generation_id]


@router.get("/generate/result/{generation_id}", response_model=GenerationResponse)
async def get_generation_result(generation_id: str) -> GenerationResponse:
    """
    Recupera resultado de uma geração concluída
    """
    if generation_id not in generation_results_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Resultado da geração {generation_id} não encontrado ou expirado"
        )
    
    return generation_results_cache[generation_id]


@router.delete("/generate/{generation_id}")
async def cancel_generation(generation_id: str) -> JSONResponse:
    """
    Cancela uma geração em andamento (se possível)
    """
    if generation_id not in generation_status_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Geração {generation_id} não encontrada"
        )
    
    status = generation_status_cache[generation_id]
    if status.status in ["completed", "error"]:
        raise HTTPException(
            status_code=400,
            detail=f"Geração {generation_id} já foi concluída e não pode ser cancelada"
        )
    
    # Marca como cancelada
    generation_status_cache[generation_id].status = "cancelled"
    generation_status_cache[generation_id].message = "Geração cancelada pelo usuário"
    generation_status_cache[generation_id].completed_at = datetime.now()
    
    return JSONResponse(
        content={"message": f"Geração {generation_id} cancelada com sucesso"}
    )


@router.get("/generate/health")
async def generation_health() -> JSONResponse:
    """
    Verifica saúde do sistema de geração
    """
    try:
        # Testa componentes principais
        federated_search = get_federated_search()
        
        # Teste simples
        test_results = await federated_search(
            query="teste de saúde",
            user_id="health_check",
            limit=1
        )
        
        # Estatísticas dos caches
        active_generations = sum(
            1 for status in generation_status_cache.values()
            if status.status == "processing"
        )
        
        return JSONResponse(content={
            "status": "healthy",
            "components": {
                "federated_search": "ok",
                "workflow": "ok"
            },
            "cache_stats": {
                "active_generations": active_generations,
                "cached_statuses": len(generation_status_cache),
                "cached_results": len(generation_results_cache)
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


def cleanup_old_cache_entries():
    """
    Remove entradas antigas dos caches (executado em background)
    """
    try:
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=24)  # Remove entradas > 24h
        
        # Limpa status antigos
        old_status_keys = [
            key for key, status in generation_status_cache.items()
            if status.completed_at and status.completed_at < cutoff_time
        ]
        
        for key in old_status_keys:
            del generation_status_cache[key]
        
        # Limpa resultados antigos
        old_result_keys = [
            key for key, result in generation_results_cache.items()
            if result.created_at < cutoff_time
        ]
        
        for key in old_result_keys:
            del generation_results_cache[key]
        
        if old_status_keys or old_result_keys:
            logger.info(f"Cache cleanup: removidos {len(old_status_keys)} status e {len(old_result_keys)} resultados")
            
    except Exception as e:
        logger.error(f"Erro no cleanup do cache: {e}")


# Adiciona rota de exemplo para testes
@router.post("/generate/test")
async def test_generation() -> JSONResponse:
    """
    Endpoint de teste para verificar geração rápida
    """
    try:
        test_request = GenerationRequest(
            query="Qual é o limite de reajuste em contratos administrativos?",
            user_id="test_user",
            config=DocumentConfig(
                document_type="parecer",
                style="formal",
                max_length=1000
            )
        )
        
        # Executa geração simples
        result = await generate_document(test_request, BackgroundTasks())
        
        return JSONResponse(content={
            "status": "success",
            "generation_id": result.generation_id,
            "text_length": len(result.generated_text),
            "processing_time": result.metrics.get("total_time", 0)
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )
