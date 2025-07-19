"""
Sistema de Personalização por Centroides
Módulo responsável por aplicar personalização baseada em centroides durante a busca
"""

import numpy as np
import redis
from typing import Optional, Dict, Any, List
import logging
import asyncio
from datetime import datetime

from app.config import get_redis_url

logger = logging.getLogger(__name__)

class CentroidPersonalizer:
    """Classe para aplicar personalização baseada em centroides"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or get_redis_url()
        self.redis_client = redis.from_url(self.redis_url)
        
        # Cache local para centroides acessados recentemente
        self._centroid_cache = {}
        self._cache_ttl = 300  # 5 minutos
    
    async def get_centroid(self, tenant_id: str, tag: str) -> Optional[np.ndarray]:
        """Recupera o centroide para um tenant/tag específico"""
        cache_key = f"{tenant_id}:{tag}"
        
        # Verificar cache local primeiro
        if cache_key in self._centroid_cache:
            cached_data = self._centroid_cache[cache_key]
            if datetime.now().timestamp() - cached_data['timestamp'] < self._cache_ttl:
                return cached_data['centroid']
        
        try:
            # Buscar no Redis
            redis_key = f"centroid:{tenant_id}:{tag}"
            centroid_bytes = self.redis_client.get(redis_key)
            
            if not centroid_bytes:
                logger.debug(f"Centroide não encontrado para {redis_key}")
                return None
            
            # Deserializar
            centroid = np.frombuffer(centroid_bytes, dtype=np.float32)
            
            # Armazenar no cache local
            self._centroid_cache[cache_key] = {
                'centroid': centroid,
                'timestamp': datetime.now().timestamp()
            }
            
            logger.debug(f"Centroide recuperado para {redis_key} (dim={len(centroid)})")
            return centroid
            
        except Exception as e:
            logger.error(f"Erro ao recuperar centroide {tenant_id}:{tag}: {e}")
            return None
    
    async def infer_query_tag(self, query: str) -> str:
        """Infere a tag temática da query"""
        # TODO: Implementar classificação mais sofisticada
        # Por enquanto, usa palavras-chave simples
        
        query_lower = query.lower()
        
        # Mapeamento de palavras-chave para tags
        tag_keywords = {
            "contratos_imobiliarios": ["imóvel", "casa", "apartamento", "aluguel", "compra", "venda", "propriedade"],
            "litigios_tributarios": ["imposto", "tributo", "fisco", "receita", "icms", "ipi", "irpf"],
            "direito_trabalhista": ["trabalho", "empregado", "salário", "férias", "rescisão", "clt"],
            "direito_civil": ["civil", "família", "divórcio", "sucessão", "herança", "responsabilidade"],
            "direito_penal": ["crime", "penal", "processo", "denúncia", "prisão", "sentença"],
            "direito_empresarial": ["empresa", "societário", "contrato", "negócio", "comercial", "cnpj"]
        }
        
        # Contar matches para cada tag
        tag_scores = {}
        for tag, keywords in tag_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                tag_scores[tag] = score
        
        # Retornar a tag com maior score
        if tag_scores:
            best_tag = max(tag_scores, key=tag_scores.get)
            logger.debug(f"Tag inferida para query '{query[:50]}...': {best_tag}")
            return best_tag
        
        # Fallback para tag genérica
        logger.debug(f"Nenhuma tag específica encontrada para query '{query[:50]}...', usando fallback")
        return "direito_civil"
    
    async def apply_personalization(
        self, 
        query_vector: np.ndarray, 
        tenant_id: str, 
        query: str = None,
        tag: str = None,
        alpha: float = 0.25
    ) -> np.ndarray:
        """
        Aplica personalização ao vetor da query
        
        Args:
            query_vector: Vetor original da query
            tenant_id: ID do tenant
            query: Texto da query (para inferir tag se não fornecida)
            tag: Tag temática específica (opcional)
            alpha: Força da personalização (0.0 = sem personalização, 1.0 = só centroide)
        
        Returns:
            Vetor da query personalizado
        """
        try:
            # Inferir tag se não fornecida
            if not tag and query:
                tag = await self.infer_query_tag(query)
            elif not tag:
                tag = "direito_civil"  # Fallback padrão
            
            # Buscar centroide
            centroid = await self.get_centroid(tenant_id, tag)
            
            if centroid is None:
                logger.debug(f"Centroide não encontrado para {tenant_id}:{tag}, retornando vetor original")
                return query_vector
            
            # Aplicar personalização
            logger.info(f"Aplicando personalização com centroide para '{tenant_id}:{tag}' (α={alpha})")
            
            # Combinar vetor original com centroide
            adjusted_vector = query_vector + alpha * centroid
            
            # Renormalizar
            norm = np.linalg.norm(adjusted_vector)
            if norm > 0:
                adjusted_vector = adjusted_vector / norm
            
            # Calcular similaridade para logging
            similarity = np.dot(query_vector, centroid)
            logger.debug(f"Similaridade query-centroide: {similarity:.3f}")
            
            return adjusted_vector
            
        except Exception as e:
            logger.error(f"Erro ao aplicar personalização: {e}")
            return query_vector
    
    async def get_personalization_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Retorna estatísticas de personalização para um tenant"""
        try:
            # Buscar todas as tags para este tenant
            pattern = f"centroid:{tenant_id}:*"
            keys = self.redis_client.keys(pattern)
            
            stats = {
                "tenant_id": tenant_id,
                "total_centroids": len(keys),
                "tags": [],
                "cache_hits": 0,
                "cache_total": len(self._centroid_cache)
            }
            
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                tag = key_str.split(":")[-1]
                
                # Buscar metadados
                meta_key = f"centroid_meta:{tenant_id}:{tag}"
                meta_data = self.redis_client.get(meta_key)
                
                tag_info = {"tag": tag}
                if meta_data:
                    try:
                        # Parse simples dos metadados
                        meta_str = meta_data.decode() if isinstance(meta_data, bytes) else meta_data
                        tag_info["metadata"] = meta_str
                    except:
                        pass
                
                stats["tags"].append(tag_info)
            
            # Contar cache hits
            cache_prefix = f"{tenant_id}:"
            stats["cache_hits"] = sum(1 for key in self._centroid_cache if key.startswith(cache_prefix))
            
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de personalização: {e}")
            return {"error": str(e)}
    
    def clear_cache(self):
        """Limpa o cache local de centroides"""
        self._centroid_cache.clear()
        logger.info("Cache de centroides limpo")


# Instância global para reutilização
_personalizer_instance = None

def get_personalizer() -> CentroidPersonalizer:
    """Retorna instância singleton do personalizador"""
    global _personalizer_instance
    if _personalizer_instance is None:
        _personalizer_instance = CentroidPersonalizer()
    return _personalizer_instance


# Função de conveniência para uso direto
async def personalize_query_vector(
    query_vector: np.ndarray,
    tenant_id: str,
    query: str = None,
    tag: str = None,
    alpha: float = 0.25
) -> np.ndarray:
    """
    Função de conveniência para personalizar um vetor de query
    
    Args:
        query_vector: Vetor original da query
        tenant_id: ID do tenant
        query: Texto da query (para inferir tag)
        tag: Tag temática específica (opcional)
        alpha: Força da personalização (0.0-1.0)
    
    Returns:
        Vetor personalizado
    """
    personalizer = get_personalizer()
    return await personalizer.apply_personalization(
        query_vector=query_vector,
        tenant_id=tenant_id,
        query=query,
        tag=tag,
        alpha=alpha
    )


# Função para testar personalização
async def test_personalization():
    """Função de teste para verificar o sistema de personalização"""
    personalizer = get_personalizer()
    
    # Vetor de teste
    test_vector = np.random.rand(768)
    test_vector = test_vector / np.linalg.norm(test_vector)
    
    # Testar personalização
    result = await personalizer.apply_personalization(
        query_vector=test_vector,
        tenant_id="cliente_acme",
        query="Contrato de aluguel de imóvel comercial",
        alpha=0.3
    )
    
    # Verificar resultado
    similarity = np.dot(test_vector, result)
    print(f"Similaridade original vs personalizado: {similarity:.3f}")
    
    # Obter estatísticas
    stats = await personalizer.get_personalization_stats("cliente_acme")
    print(f"Estatísticas: {stats}")
    
    return result


if __name__ == "__main__":
    # Executar teste
    asyncio.run(test_personalization())
