#!/usr/bin/env python3
"""
Script para calcular e armazenar centroides de personalização
Este script pode ser executado como CronJob no Kubernetes ou via Makefile
"""

import asyncio
import numpy as np
import redis
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import os
import sys

# Adicionar o diretório raiz do projeto ao Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_redis_url
from app.core.rag_bridge import get_vectors_by_tenant_and_tag
from app.db.database import get_db_session

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CentroidCalculator:
    """Calculadora de centroides para personalização de busca"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or get_redis_url()
        self.redis_client = redis.from_url(self.redis_url)
        
    async def get_tenant_tags(self, tenant_id: str) -> List[str]:
        """Obtém todas as tags temáticas para um tenant"""
        # TODO: Implementar consulta real no banco
        # Por enquanto, retorna tags padrão
        return [
            "contratos_imobiliarios",
            "litigios_tributarios", 
            "direito_trabalhista",
            "direito_civil",
            "direito_penal",
            "direito_empresarial"
        ]
    
    async def get_vectors_for_tag(self, tenant_id: str, tag: str) -> List[np.ndarray]:
        """Busca todos os vetores para uma tag/tenant específica"""
        try:
            # TODO: Implementar consulta real no banco de vetores
            # Por enquanto, simula vetores (em produção, buscaria do Qdrant/PostgreSQL)
            vectors = []
            
            # Simulação: gerar vetores aleatórios para teste
            # Em produção, isso viria do banco de dados
            num_vectors = np.random.randint(50, 200)  # Simula variação por tag
            for _ in range(num_vectors):
                vector = np.random.rand(768)  # Dimensão padrão OpenAI
                vectors.append(vector)
            
            logger.info(f"Encontrados {len(vectors)} vetores para {tenant_id}:{tag}")
            return vectors
            
        except Exception as e:
            logger.error(f"Erro ao buscar vetores para {tenant_id}:{tag}: {e}")
            return []
    
    def calculate_centroid(self, vectors: List[np.ndarray]) -> Optional[np.ndarray]:
        """Calcula o centroide (média) dos vetores e normaliza"""
        if not vectors:
            return None
            
        try:
            # Converter para array numpy se necessário
            if isinstance(vectors[0], list):
                vectors = [np.array(v) for v in vectors]
            
            # Calcular média
            centroid = np.mean(vectors, axis=0)
            
            # Normalizar
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            
            return centroid
            
        except Exception as e:
            logger.error(f"Erro ao calcular centroide: {e}")
            return None
    
    def store_centroid(self, tenant_id: str, tag: str, centroid: np.ndarray) -> bool:
        """Armazena o centroide no Redis"""
        try:
            key = f"centroid:{tenant_id}:{tag}"
            
            # Serializar como bytes
            centroid_bytes = centroid.astype(np.float32).tobytes()
            
            # Armazenar no Redis com TTL de 7 dias
            self.redis_client.setex(key, 7 * 24 * 3600, centroid_bytes)
            
            # Armazenar metadados
            metadata_key = f"centroid_meta:{tenant_id}:{tag}"
            metadata = {
                "updated_at": datetime.now().isoformat(),
                "dimension": len(centroid),
                "norm": float(np.linalg.norm(centroid))
            }
            self.redis_client.setex(metadata_key, 7 * 24 * 3600, str(metadata))
            
            logger.info(f"Centroide armazenado para '{key}' (dim={len(centroid)})")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao armazenar centroide {tenant_id}:{tag}: {e}")
            return False
    
    async def calculate_and_store_centroids(self, tenant_id: str) -> Dict[str, bool]:
        """Calcula e armazena centroides para todos as tags de um tenant"""
        results = {}
        
        logger.info(f"Iniciando cálculo de centroides para tenant: {tenant_id}")
        
        # Obter todas as tags do tenant
        tags = await self.get_tenant_tags(tenant_id)
        
        for tag in tags:
            logger.info(f"Processando tag: {tag}")
            
            # Buscar vetores para esta tag
            vectors = await self.get_vectors_for_tag(tenant_id, tag)
            
            if not vectors:
                logger.warning(f"Nenhum vetor encontrado para {tenant_id}:{tag}")
                results[tag] = False
                continue
            
            # Calcular centroide
            centroid = self.calculate_centroid(vectors)
            
            if centroid is None:
                logger.error(f"Falha ao calcular centroide para {tenant_id}:{tag}")
                results[tag] = False
                continue
            
            # Armazenar no Redis
            success = self.store_centroid(tenant_id, tag, centroid)
            results[tag] = success
            
            if success:
                logger.info(f"✅ Centroide para '{tenant_id}:{tag}' atualizado com sucesso")
            else:
                logger.error(f"❌ Falha ao armazenar centroide para '{tenant_id}:{tag}'")
        
        return results
    
    async def calculate_all_tenants(self, tenant_ids: List[str] = None) -> Dict[str, Dict[str, bool]]:
        """Calcula centroides para múltiplos tenants"""
        if not tenant_ids:
            # TODO: Buscar lista de tenants do banco
            tenant_ids = ["cliente_acme", "cliente_beta", "cliente_gamma"]
        
        all_results = {}
        
        for tenant_id in tenant_ids:
            try:
                results = await self.calculate_and_store_centroids(tenant_id)
                all_results[tenant_id] = results
            except Exception as e:
                logger.error(f"Erro ao processar tenant {tenant_id}: {e}")
                all_results[tenant_id] = {"error": str(e)}
        
        return all_results
    
    def get_centroid_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas dos centroides armazenados"""
        try:
            # Buscar todas as chaves de centroides
            keys = self.redis_client.keys("centroid:*")
            
            stats = {
                "total_centroids": len(keys),
                "by_tenant": {},
                "by_tag": {},
                "last_updated": None
            }
            
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                parts = key_str.split(":")
                
                if len(parts) >= 3:
                    tenant_id = parts[1]
                    tag = parts[2]
                    
                    # Contar por tenant
                    if tenant_id not in stats["by_tenant"]:
                        stats["by_tenant"][tenant_id] = 0
                    stats["by_tenant"][tenant_id] += 1
                    
                    # Contar por tag
                    if tag not in stats["by_tag"]:
                        stats["by_tag"][tag] = 0
                    stats["by_tag"][tag] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {"error": str(e)}


async def main():
    """Função principal para execução do script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Calculadora de Centroides")
    parser.add_argument("--tenant", type=str, help="ID específico do tenant")
    parser.add_argument("--all", action="store_true", help="Processar todos os tenants")
    parser.add_argument("--stats", action="store_true", help="Mostrar estatísticas")
    
    args = parser.parse_args()
    
    calculator = CentroidCalculator()
    
    if args.stats:
        stats = calculator.get_centroid_stats()
        logger.info(f"Estatísticas dos centroides: {stats}")
        return
    
    if args.tenant:
        # Processar tenant específico
        results = await calculator.calculate_and_store_centroids(args.tenant)
        logger.info(f"Resultados para {args.tenant}: {results}")
        
        # Mostrar estatísticas
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        logger.info(f"✅ {success_count}/{total_count} centroides processados com sucesso")
        
    elif args.all:
        # Processar todos os tenants
        all_results = await calculator.calculate_all_tenants()
        logger.info(f"Resultados para todos os tenants: {all_results}")
        
    else:
        # Exemplo padrão
        logger.info("Executando exemplo com cliente_acme...")
        results = await calculator.calculate_and_store_centroids("cliente_acme")
        logger.info(f"Resultados: {results}")
        
        # Mostrar estatísticas finais
        stats = calculator.get_centroid_stats()
        logger.info(f"Estatísticas finais: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
