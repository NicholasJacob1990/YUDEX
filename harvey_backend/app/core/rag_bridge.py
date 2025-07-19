"""
RAG Bridge - Sistema de Busca Híbrida com Personalização por Centroides
Implementa busca federada com RRF e personalização baseada em centroides
"""

import asyncio
import numpy as np
import redis
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import json

from app.config import get_redis_url, get_qdrant_config
from app.core.personalization import get_personalizer, personalize_query_vector
from app.core.embedding import get_embedding_service
from app.db.qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

class RagBridge:
    """Bridge para integrar busca híbrida com personalização"""
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.qdrant_client = QdrantClient()
        self.personalizer = get_personalizer()
        self.redis_client = redis.from_url(get_redis_url())
        
        # Configurações de busca
        self.default_k = 20
        self.rrf_k = 60  # Parâmetro RRF
        self.personalization_alpha = 0.25
        
    async def get_query_embedding(self, query: str) -> np.ndarray:
        """Gera embedding para a query"""
        try:
            embedding = await self.embedding_service.embed_query(query)
            return np.array(embedding)
        except Exception as e:
            logger.error(f"Erro ao gerar embedding: {e}")
            # Fallback com vetor aleatório normalizado
            fallback = np.random.rand(768)
            return fallback / np.linalg.norm(fallback)
    
    async def semantic_search(
        self, 
        query_vector: np.ndarray, 
        tenant_id: str, 
        k: int = 20,
        collection_name: str = "legal_documents"
    ) -> List[Dict[str, Any]]:
        """Busca semântica no Qdrant"""
        try:
            # Preparar filtros por tenant
            filters = {
                "must": [
                    {"key": "tenant_id", "match": {"value": tenant_id}}
                ]
            }
            
            # Executar busca
            results = await self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_vector.tolist(),
                limit=k,
                filters=filters
            )
            
            # Converter resultados
            semantic_results = []
            for i, result in enumerate(results):
                semantic_results.append({
                    "id": result.id,
                    "score": float(result.score),
                    "semantic_rank": i + 1,
                    "content": result.payload.get("content", ""),
                    "metadata": result.payload.get("metadata", {}),
                    "source": "semantic"
                })
            
            logger.info(f"Busca semântica retornou {len(semantic_results)} resultados")
            return semantic_results
            
        except Exception as e:
            logger.error(f"Erro na busca semântica: {e}")
            return []
    
    async def lexical_search(
        self, 
        query: str, 
        tenant_id: str, 
        k: int = 20
    ) -> List[Dict[str, Any]]:
        """Busca lexical/textual (simulada - em produção usaria BM25)"""
        try:
            # TODO: Implementar busca lexical real (PostgreSQL FTS, Elasticsearch, etc.)
            # Por enquanto, simula resultados
            
            lexical_results = []
            
            # Simular busca por palavras-chave
            keywords = query.lower().split()
            
            # Gerar resultados simulados
            for i in range(min(k, 15)):  # Simula menos resultados que semântica
                doc_id = f"doc_{tenant_id}_{i}"
                score = max(0.1, 1.0 - (i * 0.1))  # Score decrescente
                
                lexical_results.append({
                    "id": doc_id,
                    "score": score,
                    "lexical_rank": i + 1,
                    "content": f"Documento {i+1} com palavras-chave: {' '.join(keywords[:2])}",
                    "metadata": {
                        "keywords_matched": keywords[:2],
                        "total_keywords": len(keywords)
                    },
                    "source": "lexical"
                })
            
            logger.info(f"Busca lexical retornou {len(lexical_results)} resultados")
            return lexical_results
            
        except Exception as e:
            logger.error(f"Erro na busca lexical: {e}")
            return []
    
    def reciprocal_rank_fusion(
        self, 
        semantic_results: List[Dict[str, Any]], 
        lexical_results: List[Dict[str, Any]], 
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """Implementa Reciprocal Rank Fusion (RRF)"""
        try:
            # Mapear resultados por ID
            all_docs = {}
            
            # Processar resultados semânticos
            for result in semantic_results:
                doc_id = result["id"]
                semantic_rank = result.get("semantic_rank", 999)
                
                if doc_id not in all_docs:
                    all_docs[doc_id] = result.copy()
                    all_docs[doc_id]["rrf_score"] = 0
                    all_docs[doc_id]["rank_sources"] = []
                
                # Calcular RRF score para busca semântica
                rrf_semantic = 1.0 / (k + semantic_rank)
                all_docs[doc_id]["rrf_score"] += rrf_semantic
                all_docs[doc_id]["rank_sources"].append({
                    "source": "semantic",
                    "rank": semantic_rank,
                    "rrf_contribution": rrf_semantic
                })
            
            # Processar resultados lexicais
            for result in lexical_results:
                doc_id = result["id"]
                lexical_rank = result.get("lexical_rank", 999)
                
                if doc_id not in all_docs:
                    all_docs[doc_id] = result.copy()
                    all_docs[doc_id]["rrf_score"] = 0
                    all_docs[doc_id]["rank_sources"] = []
                
                # Calcular RRF score para busca lexical
                rrf_lexical = 1.0 / (k + lexical_rank)
                all_docs[doc_id]["rrf_score"] += rrf_lexical
                all_docs[doc_id]["rank_sources"].append({
                    "source": "lexical",
                    "rank": lexical_rank,
                    "rrf_contribution": rrf_lexical
                })
            
            # Ordenar por RRF score
            fused_results = sorted(all_docs.values(), key=lambda x: x["rrf_score"], reverse=True)
            
            # Adicionar posição final
            for i, result in enumerate(fused_results):
                result["final_rank"] = i + 1
            
            logger.info(f"RRF fusion combinou {len(fused_results)} documentos únicos")
            return fused_results
    
    async def process_external_docs(
        self, 
        external_docs: List[Dict[str, Any]], 
        query: str,
        query_vector: Optional[np.ndarray] = None
    ) -> List[Dict[str, Any]]:
        """
        Processa documentos externos para incluir na busca
        
        Args:
            external_docs: Lista de documentos externos
            query: Query original para calcular relevância
            query_vector: Vetor da query (opcional, para cálculo de similaridade)
        
        Returns:
            Lista de documentos processados com scores
        """
        try:
            if not external_docs:
                return []
            
            ephemeral_hits = []
            
            for i, doc in enumerate(external_docs):
                # Extrair informações do documento
                src_id = doc.get("src_id", f"external_doc_{i}")
                text = doc.get("text", "")
                meta = doc.get("meta", {})
                priority = doc.get("priority", 0.9)
                
                # Calcular score baseado na prioridade e posição
                # Documentos externos têm score alto para aparecer no topo
                base_score = priority
                position_penalty = i * 0.01  # Pequena penalidade por posição
                final_score = max(0.1, base_score - position_penalty)
                
                # Se temos o vetor da query, podemos calcular similaridade semântica
                if query_vector is not None and text:
                    try:
                        # Gerar embedding do documento (simplificado)
                        doc_embedding = await self.get_query_embedding(text[:1000])  # Limite para performance
                        
                        # Calcular similaridade
                        similarity = np.dot(query_vector, doc_embedding)
                        
                        # Combinar prioridade com similaridade
                        final_score = (final_score * 0.7) + (similarity * 0.3)
                        
                    except Exception as e:
                        logger.warning(f"Erro ao calcular similaridade para documento {src_id}: {e}")
                
                # Calcular relevância textual simples
                query_words = set(query.lower().split())
                doc_words = set(text.lower().split())
                text_overlap = len(query_words & doc_words) / len(query_words) if query_words else 0
                
                # Ajustar score com base na sobreposição textual
                final_score = (final_score * 0.8) + (text_overlap * 0.2)
                
                ephemeral_hits.append({
                    "id": src_id,
                    "score": final_score,
                    "external_rank": i + 1,
                    "content": text,
                    "metadata": meta,
                    "source": "external",
                    "priority": priority,
                    "text_overlap": text_overlap,
                    "src_id": src_id
                })
            
            # Ordenar por score decrescente
            ephemeral_hits.sort(key=lambda x: x["score"], reverse=True)
            
            # Adicionar ranking final
            for i, hit in enumerate(ephemeral_hits):
                hit["final_external_rank"] = i + 1
            
            logger.info(f"Processados {len(ephemeral_hits)} documentos externos")
            return ephemeral_hits
            
        except Exception as e:
            logger.error(f"Erro ao processar documentos externos: {e}")
            return []
    
    def fuse_internal_and_external(
        self, 
        internal_results: List[Dict[str, Any]], 
        external_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Combina resultados internos e externos usando estratégia de prioridade
        
        Args:
            internal_results: Resultados da busca interna (já fusionados com RRF)
            external_results: Resultados dos documentos externos
        
        Returns:
            Lista combinada e ordenada
        """
        try:
            # Estratégia: documentos externos têm prioridade alta por padrão
            # mas podem ser intercalados com resultados internos relevantes
            
            combined_results = []
            
            # Adicionar todos os resultados com marcação de origem
            for result in internal_results:
                result["fusion_source"] = "internal"
                combined_results.append(result)
            
            for result in external_results:
                result["fusion_source"] = "external"
                combined_results.append(result)
            
            # Ordenar por score, com boost para documentos externos
            def get_sort_key(result):
                base_score = result.get("score", 0)
                rrf_score = result.get("rrf_score", 0)
                
                # Usar RRF score se disponível, senão usar score normal
                effective_score = rrf_score if rrf_score > 0 else base_score
                
                # Boost para documentos externos
                if result.get("fusion_source") == "external":
                    effective_score *= 1.2  # 20% de boost
                
                return effective_score
            
            combined_results.sort(key=get_sort_key, reverse=True)
            
            # Adicionar ranking final
            for i, result in enumerate(combined_results):
                result["final_rank"] = i + 1
                result["fusion_score"] = get_sort_key(result)
            
            logger.info(f"Fusão interna/externa: {len(internal_results)} internos + {len(external_results)} externos = {len(combined_results)} total")
            
            return combined_results
            
        except Exception as e:
            logger.error(f"Erro na fusão interna/externa: {e}")
            # Fallback: retornar externos primeiro, depois internos
            return external_results + internal_results
    
    async def federated_search(
        self, 
        query: str, 
        tenant_id: str, 
        k_total: int = 20,
        personalization_alpha: Optional[float] = None,
        enable_personalization: bool = True,
        external_docs: Optional[List[Dict[str, Any]]] = None,
        use_internal_rag: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Busca federada com personalização por centroides e suporte a documentos externos
        
        Args:
            query: Texto da consulta
            tenant_id: ID do tenant
            k_total: Número total de resultados desejados
            personalization_alpha: Força da personalização (None = usar padrão)
            enable_personalization: Se deve aplicar personalização
            external_docs: Lista de documentos externos para incluir na busca
            use_internal_rag: Se deve buscar na base de dados interna
        
        Returns:
            Lista de resultados fusionados, incluindo documentos externos
        """
        try:
            start_time = datetime.now()
            
            # Validar parâmetros
            if not use_internal_rag and not external_docs:
                logger.warning("Nem busca interna nem documentos externos fornecidos")
                return []
            
            # Gerar embedding da query apenas se necessário para busca interna
            query_vector = None
            if use_internal_rag:
                query_vector = await self.get_query_embedding(query)
                
                # Aplicar personalização se habilitada
                if enable_personalization:
                    alpha = personalization_alpha or self.personalization_alpha
                    
                    personalized_vector = await personalize_query_vector(
                        query_vector=query_vector,
                        tenant_id=tenant_id,
                        query=query,
                        alpha=alpha
                    )
                    
                    # Calcular similaridade para logging
                    similarity = np.dot(query_vector, personalized_vector)
                    logger.info(f"Personalização aplicada - Similaridade: {similarity:.3f}")
                    
                    query_vector = personalized_vector
            
            # Dicionário para armazenar hits de diferentes fontes
            all_results = {}
            
            # --- 1. Busca nos bancos de dados internos (se habilitado) ---
            if use_internal_rag and query_vector is not None:
                k_search = min(k_total * 2, 50)  # Buscar mais para permitir diversidade
                
                semantic_task = self.semantic_search(query_vector, tenant_id, k_search)
                lexical_task = self.lexical_search(query, tenant_id, k_search)
                
                semantic_results, lexical_results = await asyncio.gather(
                    semantic_task, lexical_task
                )
                
                # Adicionar resultados internos
                all_results["semantic"] = semantic_results
                all_results["lexical"] = lexical_results
                
                logger.info(f"Busca interna: {len(semantic_results)} semânticos, {len(lexical_results)} lexicais")
            
            # --- 2. Processar documentos externos como fonte "efêmera" ---
            if external_docs:
                ephemeral_hits = await self.process_external_docs(external_docs, query, query_vector)
                all_results["ephemeral"] = ephemeral_hits
                logger.info(f"Documentos externos processados: {len(ephemeral_hits)}")
            
            # --- 3. Aplicar RRF fusion se houver resultados ---
            if not all_results:
                logger.warning("Nenhum resultado encontrado em nenhuma fonte")
                return []
            
            # Aplicar RRF fusion
            if len(all_results) == 1:
                # Se só temos uma fonte, usar diretamente
                fused_results = list(all_results.values())[0]
            else:
                # Aplicar RRF entre múltiplas fontes
                semantic_results = all_results.get("semantic", [])
                lexical_results = all_results.get("lexical", [])
                ephemeral_results = all_results.get("ephemeral", [])
                
                # Combinar resultados internos primeiro
                if semantic_results or lexical_results:
                    internal_fused = self.reciprocal_rank_fusion(
                        semantic_results, lexical_results, self.rrf_k
                    )
                else:
                    internal_fused = []
                
                # Se temos documentos externos, combiná-los com os internos
                if ephemeral_results:
                    # Criar estrutura compatível com RRF
                    fused_results = self.fuse_internal_and_external(
                        internal_fused, ephemeral_results
                    )
                else:
                    fused_results = internal_fused
            
            # Limitar ao número desejado
            final_results = fused_results[:k_total]
            
            # Adicionar metadados da busca
            search_metadata = {
                "query": query,
                "tenant_id": tenant_id,
                "personalization_enabled": enable_personalization,
                "personalization_alpha": personalization_alpha or self.personalization_alpha,
                "use_internal_rag": use_internal_rag,
                "external_docs_count": len(external_docs) if external_docs else 0,
                "internal_results_count": len(all_results.get("semantic", [])) + len(all_results.get("lexical", [])),
                "external_results_count": len(all_results.get("ephemeral", [])),
                "final_results_count": len(final_results),
                "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000
            }
            
            # Adicionar metadados a cada resultado
            for result in final_results:
                result["search_metadata"] = search_metadata
            
            logger.info(f"Busca federada concluída: {len(final_results)} resultados em {search_metadata['execution_time_ms']:.2f}ms")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Erro na busca federada: {e}")
            return []
    
    async def get_search_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Retorna estatísticas de busca para um tenant"""
        try:
            # Buscar estatísticas de personalização
            personalization_stats = await self.personalizer.get_personalization_stats(tenant_id)
            
            # Buscar estatísticas de busca (cache Redis)
            search_stats_key = f"search_stats:{tenant_id}"
            cached_stats = self.redis_client.get(search_stats_key)
            
            search_stats = {"cached": False}
            if cached_stats:
                try:
                    search_stats = json.loads(cached_stats)
                    search_stats["cached"] = True
                except:
                    pass
            
            return {
                "tenant_id": tenant_id,
                "personalization": personalization_stats,
                "search_performance": search_stats,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {"error": str(e)}
    
    async def warmup_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Aquece o cache para um tenant específico"""
        try:
            # Buscar centroides para cache
            personalization_stats = await self.personalizer.get_personalization_stats(tenant_id)
            
            # Fazer uma busca de teste
            test_query = "exemplo de consulta para aquecimento"
            test_results = await self.federated_search(
                query=test_query,
                tenant_id=tenant_id,
                k_total=5
            )
            
            return {
                "tenant_id": tenant_id,
                "centroids_loaded": personalization_stats.get("total_centroids", 0),
                "test_results": len(test_results),
                "status": "warmed_up"
            }
            
        except Exception as e:
            logger.error(f"Erro no warmup: {e}")
            return {"error": str(e)}


# Instância global
_rag_bridge_instance = None

def get_rag_bridge() -> RagBridge:
    """Retorna instância singleton do RagBridge"""
    global _rag_bridge_instance
    if _rag_bridge_instance is None:
        _rag_bridge_instance = RagBridge()
    return _rag_bridge_instance


# Função de conveniência para uso direto
async def search_documents(
    query: str,
    tenant_id: str,
    k: int = 20,
    personalization_alpha: Optional[float] = None,
    enable_personalization: bool = True,
    external_docs: Optional[List[Dict[str, Any]]] = None,
    use_internal_rag: bool = True
) -> List[Dict[str, Any]]:
    """
    Função de conveniência para buscar documentos com suporte a contexto externo
    
    Args:
        query: Texto da consulta
        tenant_id: ID do tenant
        k: Número de resultados
        personalization_alpha: Força da personalização
        enable_personalization: Se deve aplicar personalização
        external_docs: Lista de documentos externos
        use_internal_rag: Se deve usar busca interna
    
    Returns:
        Lista de documentos encontrados
    """
    bridge = get_rag_bridge()
    return await bridge.federated_search(
        query=query,
        tenant_id=tenant_id,
        k_total=k,
        personalization_alpha=personalization_alpha,
        enable_personalization=enable_personalization,
        external_docs=external_docs,
        use_internal_rag=use_internal_rag
    )


# Função auxiliar para buscar vetores (usado pelo script de centroides)
async def get_vectors_by_tenant_and_tag(tenant_id: str, tag: str) -> List[np.ndarray]:
    """
    Busca vetores de documentos por tenant e tag
    Usado pelo script de cálculo de centroides
    """
    try:
        # TODO: Implementar busca real no banco de vetores
        # Por enquanto, retorna vetores simulados
        
        vectors = []
        
        # Simular busca no Qdrant
        bridge = get_rag_bridge()
        
        # Buscar todos os documentos do tenant com a tag
        # Em produção, isso seria uma consulta filtered no Qdrant
        # collection_name = "legal_documents"
        # filters = {
        #     "must": [
        #         {"key": "tenant_id", "match": {"value": tenant_id}},
        #         {"key": "tag", "match": {"value": tag}}
        #     ]
        # }
        # results = await bridge.qdrant_client.scroll(
        #     collection_name=collection_name,
        #     filters=filters,
        #     limit=1000
        # )
        
        # Por enquanto, simula vetores
        num_docs = np.random.randint(50, 200)
        for _ in range(num_docs):
            vector = np.random.rand(768)
            vectors.append(vector / np.linalg.norm(vector))
        
        logger.info(f"Encontrados {len(vectors)} vetores para {tenant_id}:{tag}")
        return vectors
        
    except Exception as e:
        logger.error(f"Erro ao buscar vetores: {e}")
        return []


# Função de teste
async def test_federated_search():
    """Testa o sistema completo"""
    bridge = get_rag_bridge()
    
    # Teste com personalização
    results_personalized = await bridge.federated_search(
        query="Contrato de locação comercial com cláusula de reajuste",
        tenant_id="cliente_acme",
        k_total=10,
        enable_personalization=True
    )
    
    # Teste sem personalização
    results_standard = await bridge.federated_search(
        query="Contrato de locação comercial com cláusula de reajuste",
        tenant_id="cliente_acme",
        k_total=10,
        enable_personalization=False
    )
    
    print(f"Resultados com personalização: {len(results_personalized)}")
    print(f"Resultados sem personalização: {len(results_standard)}")
    
    # Comparar primeiros resultados
    if results_personalized and results_standard:
        pers_score = results_personalized[0]["rrf_score"]
        std_score = results_standard[0]["rrf_score"]
        print(f"Score top resultado - Personalizado: {pers_score:.4f}, Padrão: {std_score:.4f}")
    
    return results_personalized, results_standard


if __name__ == "__main__":
    # Executar teste
    asyncio.run(test_federated_search())
