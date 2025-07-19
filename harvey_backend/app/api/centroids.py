"""
API para gerenciamento de centroides de personalização
Endpoints para monitorar, calcular e gerenciar centroides
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from app.core.personalization import get_personalizer
from app.core.rag_bridge import get_rag_bridge
from app.auth.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/centroids", tags=["centroids"])

@router.get("/stats/{tenant_id}")
async def get_centroids_stats(
    tenant_id: str,
    current_user: User = Depends(get_current_user)
):
    """Retorna estatísticas dos centroides para um tenant"""
    try:
        # Verificar se o usuário tem acesso ao tenant
        if not current_user.has_tenant_access(tenant_id):
            raise HTTPException(status_code=403, detail="Acesso negado ao tenant")
        
        personalizer = get_personalizer()
        stats = await personalizer.get_personalization_stats(tenant_id)
        
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de centroides: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.post("/calculate/{tenant_id}")
async def calculate_centroids(
    tenant_id: str,
    background_tasks: BackgroundTasks,
    force_recalculate: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Inicia cálculo de centroides para um tenant"""
    try:
        # Verificar permissões
        if not current_user.has_tenant_access(tenant_id):
            raise HTTPException(status_code=403, detail="Acesso negado ao tenant")
        
        if not current_user.is_admin():
            raise HTTPException(status_code=403, detail="Permissão de admin necessária")
        
        # Importar aqui para evitar imports circulares
        from scripts.calculate_centroids import CentroidCalculator
        
        # Adicionar task em background
        background_tasks.add_task(
            _calculate_centroids_task,
            tenant_id,
            force_recalculate
        )
        
        return {
            "status": "success",
            "message": f"Cálculo de centroides iniciado para tenant {tenant_id}",
            "tenant_id": tenant_id,
            "force_recalculate": force_recalculate,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao iniciar cálculo de centroides: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.post("/calculate-all")
async def calculate_all_centroids(
    background_tasks: BackgroundTasks,
    force_recalculate: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Inicia cálculo de centroides para todos os tenants"""
    try:
        # Verificar permissões de super admin
        if not current_user.is_super_admin():
            raise HTTPException(status_code=403, detail="Permissão de super admin necessária")
        
        # Adicionar task em background
        background_tasks.add_task(
            _calculate_all_centroids_task,
            force_recalculate
        )
        
        return {
            "status": "success",
            "message": "Cálculo de centroides iniciado para todos os tenants",
            "force_recalculate": force_recalculate,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao iniciar cálculo global de centroides: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/health")
async def centroids_health_check():
    """Verificação de saúde do sistema de centroides"""
    try:
        personalizer = get_personalizer()
        
        # Verificar conectividade com Redis
        redis_status = "ok"
        try:
            personalizer.redis_client.ping()
        except Exception as e:
            redis_status = f"error: {str(e)}"
        
        # Verificar estatísticas gerais
        try:
            from scripts.calculate_centroids import CentroidCalculator
            calculator = CentroidCalculator()
            general_stats = calculator.get_centroid_stats()
        except Exception as e:
            general_stats = {"error": str(e)}
        
        return {
            "status": "ok",
            "redis_connection": redis_status,
            "general_stats": general_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro no health check de centroides: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.delete("/clear-cache")
async def clear_centroids_cache(
    current_user: User = Depends(get_current_user)
):
    """Limpa o cache local de centroides"""
    try:
        if not current_user.is_admin():
            raise HTTPException(status_code=403, detail="Permissão de admin necessária")
        
        personalizer = get_personalizer()
        personalizer.clear_cache()
        
        return {
            "status": "success",
            "message": "Cache de centroides limpo",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao limpar cache de centroides: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/search-stats/{tenant_id}")
async def get_search_stats(
    tenant_id: str,
    current_user: User = Depends(get_current_user)
):
    """Retorna estatísticas de busca e personalização"""
    try:
        if not current_user.has_tenant_access(tenant_id):
            raise HTTPException(status_code=403, detail="Acesso negado ao tenant")
        
        rag_bridge = get_rag_bridge()
        stats = await rag_bridge.get_search_stats(tenant_id)
        
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de busca: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.post("/warmup/{tenant_id}")
async def warmup_tenant(
    tenant_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Aquece o cache para um tenant específico"""
    try:
        if not current_user.has_tenant_access(tenant_id):
            raise HTTPException(status_code=403, detail="Acesso negado ao tenant")
        
        # Executar warmup em background
        background_tasks.add_task(_warmup_tenant_task, tenant_id)
        
        return {
            "status": "success",
            "message": f"Warmup iniciado para tenant {tenant_id}",
            "tenant_id": tenant_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao iniciar warmup: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.post("/test-personalization")
async def test_personalization(
    tenant_id: str,
    query: str,
    alpha: float = 0.25,
    current_user: User = Depends(get_current_user)
):
    """Testa a personalização com uma query específica"""
    try:
        if not current_user.has_tenant_access(tenant_id):
            raise HTTPException(status_code=403, detail="Acesso negado ao tenant")
        
        rag_bridge = get_rag_bridge()
        
        # Buscar com personalização
        results_personalized = await rag_bridge.federated_search(
            query=query,
            tenant_id=tenant_id,
            k_total=5,
            personalization_alpha=alpha,
            enable_personalization=True
        )
        
        # Buscar sem personalização
        results_standard = await rag_bridge.federated_search(
            query=query,
            tenant_id=tenant_id,
            k_total=5,
            enable_personalization=False
        )
        
        return {
            "status": "success",
            "data": {
                "query": query,
                "tenant_id": tenant_id,
                "alpha": alpha,
                "personalized_results": results_personalized,
                "standard_results": results_standard,
                "comparison": {
                    "personalized_count": len(results_personalized),
                    "standard_count": len(results_standard)
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro no teste de personalização: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

# Background tasks
async def _calculate_centroids_task(tenant_id: str, force_recalculate: bool = False):
    """Task em background para calcular centroides"""
    try:
        from scripts.calculate_centroids import CentroidCalculator
        
        calculator = CentroidCalculator()
        results = await calculator.calculate_and_store_centroids(tenant_id)
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        logger.info(f"Centroides calculados para {tenant_id}: {success_count}/{total_count}")
        
    except Exception as e:
        logger.error(f"Erro no cálculo de centroides para {tenant_id}: {e}")

async def _calculate_all_centroids_task(force_recalculate: bool = False):
    """Task em background para calcular centroides de todos os tenants"""
    try:
        from scripts.calculate_centroids import CentroidCalculator
        
        calculator = CentroidCalculator()
        results = await calculator.calculate_all_tenants()
        
        total_tenants = len(results)
        successful_tenants = sum(1 for tenant_results in results.values() 
                               if isinstance(tenant_results, dict) and 'error' not in tenant_results)
        
        logger.info(f"Centroides calculados para {successful_tenants}/{total_tenants} tenants")
        
    except Exception as e:
        logger.error(f"Erro no cálculo global de centroides: {e}")

async def _warmup_tenant_task(tenant_id: str):
    """Task em background para aquecimento de tenant"""
    try:
        rag_bridge = get_rag_bridge()
        result = await rag_bridge.warmup_tenant(tenant_id)
        
        logger.info(f"Warmup concluído para {tenant_id}: {result}")
        
    except Exception as e:
        logger.error(f"Erro no warmup de {tenant_id}: {e}")

# Incluir router nas rotas principais
def include_centroids_router(app):
    """Inclui o router de centroides na aplicação"""
    app.include_router(router)
