"""
API de Feedback do Usuário - Onda 3
Captura avaliações, correções e sugestões dos advogados
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json
import logging

# Importações internas (adaptadas para estrutura atual)
# from app.security.auth import get_api_identity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["Feedback"])

# --- Pydantic Schemas ---

class ErrorSpan(BaseModel):
    """Representa um span de erro identificado pelo usuário"""
    start: int = Field(..., description="Posição inicial do erro no texto")
    end: int = Field(..., description="Posição final do erro no texto")
    label: str = Field(..., description="Tipo/categoria do erro")
    suggestion: Optional[str] = Field(None, description="Sugestão de correção")

class MissingSource(BaseModel):
    """Representa uma fonte que deveria ter sido incluída"""
    raw: str = Field(..., description="Texto bruto da fonte")
    class_: Optional[str] = Field(None, alias="class", description="Classe/tipo da fonte")
    relevance_score: Optional[float] = Field(None, description="Score de relevância sugerido")

class FeedbackRequest(BaseModel):
    """Payload de feedback do usuário"""
    run_id: str = Field(..., description="ID da execução que recebeu feedback")
    rating: Optional[int] = Field(None, ge=-1, le=1, description="Avaliação: -1 (negativo), 0 (neutro), 1 (positivo)")
    comment: Optional[str] = Field(None, description="Comentário geral do usuário")
    error_spans: Optional[List[ErrorSpan]] = Field(None, description="Spans de erro identificados")
    missing_sources: Optional[List[MissingSource]] = Field(None, description="Fontes ausentes")
    edited_text_md: Optional[str] = Field(None, description="Texto corrigido pelo advogado")
    tags: Optional[List[str]] = Field(None, description="Tags/categorias do feedback")
    
    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "550e8400-e29b-41d4-a716-446655440000",
                "rating": 1,
                "comment": "Ótimo documento, mas faltou uma jurisprudência específica",
                "error_spans": [
                    {
                        "start": 150,
                        "end": 200,
                        "label": "fundamentacao_incompleta",
                        "suggestion": "Adicionar referência ao art. 186 CC"
                    }
                ],
                "missing_sources": [
                    {
                        "raw": "STJ REsp 1234567/SP",
                        "class": "jurisprudencia",
                        "relevance_score": 0.95
                    }
                ],
                "tags": ["jurisprudencia", "fundamentacao"]
            }
        }

class FeedbackResponse(BaseModel):
    """Resposta do endpoint de feedback"""
    status: str
    run_id: str
    feedback_id: int
    message: str
    timestamp: datetime

# --- Simulação de dependência de autenticação ---
async def get_api_identity():
    """Simulação de autenticação - substituir por implementação real"""
    return {
        "user_id": "user_123",
        "tenant_id": "tenant_abc",
        "permissions": ["feedback.write"]
    }

# --- Funções de persistência ---
async def store_feedback_in_db(tenant_id: str, user_id: str, data: FeedbackRequest) -> int:
    """Armazena o feedback no banco de dados"""
    try:
        # Simulação de inserção no banco - implementar com seu ORM/driver
        feedback_id = abs(hash(f"{data.run_id}_{tenant_id}_{user_id}")) % 1000000
        
        # Preparar dados para inserção
        feedback_data = {
            "run_id": data.run_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "rating": data.rating,
            "comment": data.comment,
            "error_spans": json.dumps([span.dict() for span in data.error_spans]) if data.error_spans else None,
            "missing_sources": json.dumps([source.dict() for source in data.missing_sources]) if data.missing_sources else None,
            "edited_text_md": data.edited_text_md,
            "tags": data.tags or [],
            "created_at": datetime.now()
        }
        
        logger.info(f"Feedback armazenado: run_id={data.run_id}, tenant={tenant_id}, rating={data.rating}")
        
        # TODO: Implementar inserção real no banco
        # query = """
        # INSERT INTO feedback_events 
        # (run_id, tenant_id, user_id, rating, comment, error_spans, missing_sources, edited_text_md, tags)
        # VALUES (%(run_id)s, %(tenant_id)s, %(user_id)s, %(rating)s, %(comment)s, %(error_spans)s, %(missing_sources)s, %(edited_text_md)s, %(tags)s)
        # RETURNING id
        # """
        # result = await db.execute(query, feedback_data)
        # return result.fetchone()[0]
        
        return feedback_id
        
    except Exception as e:
        logger.error(f"Erro ao armazenar feedback: {e}")
        raise

async def validate_run_exists(run_id: str, tenant_id: str) -> bool:
    """Valida se a execução existe e pertence ao tenant"""
    # TODO: Implementar validação real
    logger.info(f"Validando run_id={run_id} para tenant={tenant_id}")
    return True

async def update_run_feedback_metrics(run_id: str, rating: Optional[int]):
    """Atualiza métricas de feedback da execução"""
    if rating is not None:
        logger.info(f"Atualizando métricas de feedback: run_id={run_id}, rating={rating}")
        # TODO: Implementar atualização de métricas agregadas

# --- Endpoints ---

@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_feedback(
    data: FeedbackRequest,
    identity: dict = Depends(get_api_identity)
):
    """
    Recebe feedback de um usuário sobre uma execução específica.
    
    Este endpoint permite que advogados forneçam avaliações, correções e sugestões
    sobre documentos gerados pelo sistema, criando um ciclo de aprendizado contínuo.
    """
    try:
        user_id = identity.get("user_id", "unknown_user")
        tenant_id = identity["tenant_id"]
        
        # Validar se a execução existe
        if not await validate_run_exists(data.run_id, tenant_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execução {data.run_id} não encontrada para este tenant"
            )
        
        # Armazenar feedback
        feedback_id = await store_feedback_in_db(tenant_id, user_id, data)
        
        # Atualizar métricas
        await update_run_feedback_metrics(data.run_id, data.rating)
        
        # Log para auditoria
        logger.info(f"Feedback processado: feedback_id={feedback_id}, run_id={data.run_id}")
        
        return FeedbackResponse(
            status="feedback_received",
            run_id=data.run_id,
            feedback_id=feedback_id,
            message="Feedback recebido com sucesso",
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao processar feedback: {str(e)}"
        )

@router.get("/{run_id}/summary")
async def get_feedback_summary(
    run_id: str,
    identity: dict = Depends(get_api_identity)
):
    """
    Retorna um resumo do feedback recebido para uma execução específica.
    """
    try:
        tenant_id = identity["tenant_id"]
        
        # TODO: Implementar consulta de resumo
        summary = {
            "run_id": run_id,
            "total_feedback": 0,
            "avg_rating": 0.0,
            "rating_distribution": {"-1": 0, "0": 0, "1": 0},
            "common_tags": [],
            "error_patterns": []
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Erro ao obter resumo de feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter resumo: {str(e)}"
        )

@router.get("/analytics")
async def get_feedback_analytics(
    tenant_id: Optional[str] = None,
    days: int = 30,
    identity: dict = Depends(get_api_identity)
):
    """
    Retorna analytics de feedback para análise de qualidade do sistema.
    """
    try:
        effective_tenant_id = tenant_id or identity["tenant_id"]
        
        # TODO: Implementar analytics real
        analytics = {
            "period_days": days,
            "total_feedback": 0,
            "avg_rating": 0.0,
            "improvement_trends": [],
            "top_error_categories": [],
            "user_satisfaction_trend": []
        }
        
        return analytics
        
    except Exception as e:
        logger.error(f"Erro ao obter analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter analytics: {str(e)}"
        )

# --- Funções auxiliares para análise ---

def analyze_feedback_patterns(feedback_data: List[Dict]) -> Dict[str, Any]:
    """Analisa padrões no feedback recebido"""
    # TODO: Implementar análise de padrões
    return {
        "common_issues": [],
        "improvement_suggestions": [],
        "quality_trends": []
    }

def generate_learning_insights(feedback_data: List[Dict]) -> Dict[str, Any]:
    """Gera insights para melhoria do sistema"""
    # TODO: Implementar geração de insights
    return {
        "training_recommendations": [],
        "prompt_improvements": [],
        "knowledge_gaps": []
    }
