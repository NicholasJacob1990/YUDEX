"""
Pipeline RAG
Sistema completo de Retrieval-Augmented Generation para documentos jurídicos
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
from ..config import settings
from .vectordb import get_vector_store, SearchResult, DocumentMetadata
from .embeddings import get_embedding_processor
from .rerank import get_reranker, RerankResult
from .chunker import chunk_legal_document, DocumentChunk

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    """Resultado completo do pipeline RAG"""
    query: str
    retrieved_docs: List[SearchResult]
    reranked_docs: List[SearchResult]
    context_text: str
    metadata: Dict[str, Any]
    processing_time: float
    retrieval_stats: Dict[str, Any]


class LegalRAGPipeline:
    """
    Pipeline RAG completo para documentos jurídicos
    Integra retrieval, re-ranking e geração de contexto
    """
    
    def __init__(
        self,
        vector_store=None,
        embedding_processor=None,
        reranker=None
    ):
        self.vector_store = vector_store or get_vector_store()
        self.embedding_processor = embedding_processor or get_embedding_processor()
        self.reranker = reranker or get_reranker("hybrid")
        
        # Configurações do pipeline
        self.max_docs_retrieval = settings.max_docs_retrieval
        self.similarity_threshold = settings.similarity_threshold
        self.rerank_top_k = settings.rerank_top_k
        
        # Cache para queries frequentes
        self._query_cache: Dict[str, RAGResult] = {}
        self._cache_ttl = 3600  # 1 hora
    
    async def search_and_rank(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        top_k: int = None,
        use_cache: bool = True,
        include_metadata: bool = True
    ) -> RAGResult:
        """
        Pipeline completo: busca, re-ranking e preparação de contexto
        """
        import time
        start_time = time.time()
        
        # Verifica cache
        cache_key = f"{query}:{str(filters)}:{top_k}"
        if use_cache and cache_key in self._query_cache:
            cached_result = self._query_cache[cache_key]
            # Verifica TTL do cache
            if (time.time() - cached_result.metadata.get('cached_at', 0)) < self._cache_ttl:
                logger.info(f"Resultado encontrado no cache para: {query[:50]}")
                return cached_result
        
        top_k = top_k or self.rerank_top_k
        
        try:
            # 1. Retrieval inicial
            logger.info(f"Iniciando busca RAG para: {query[:50]}...")
            
            initial_results = await self.vector_store.search(
                query_text=query,
                limit=self.max_docs_retrieval,
                filters=filters,
                score_threshold=self.similarity_threshold
            )
            
            logger.info(f"Retrieval inicial: {len(initial_results)} documentos")
            
            # 2. Re-ranking
            if initial_results and len(initial_results) > 1:
                rerank_result = await self.reranker.rerank(
                    query=query,
                    search_results=initial_results,
                    top_k=top_k
                )
                final_results = rerank_result.reranked_results
                rerank_scores = rerank_result.rerank_scores
            else:
                final_results = initial_results[:top_k]
                rerank_scores = [result.score for result in final_results]
            
            logger.info(f"Re-ranking: {len(final_results)} documentos finais")
            
            # 3. Prepara contexto
            context_text = self._prepare_context_text(final_results)
            
            # 4. Calcula estatísticas
            retrieval_stats = {
                'initial_results_count': len(initial_results),
                'final_results_count': len(final_results),
                'average_initial_score': sum(r.score for r in initial_results) / len(initial_results) if initial_results else 0,
                'average_final_score': sum(rerank_scores) / len(rerank_scores) if rerank_scores else 0,
                'score_improvement': 0.0
            }
            
            if initial_results and final_results:
                retrieval_stats['score_improvement'] = (
                    retrieval_stats['average_final_score'] - retrieval_stats['average_initial_score']
                )
            
            # 5. Monta resultado
            processing_time = time.time() - start_time
            
            result = RAGResult(
                query=query,
                retrieved_docs=initial_results,
                reranked_docs=final_results,
                context_text=context_text,
                metadata={
                    'filters_applied': filters,
                    'processing_time': processing_time,
                    'cached_at': time.time(),
                    'vector_store_type': type(self.vector_store).__name__,
                    'reranker_type': type(self.reranker).__name__,
                    'include_metadata': include_metadata
                },
                processing_time=processing_time,
                retrieval_stats=retrieval_stats
            )
            
            # Adiciona ao cache
            if use_cache:
                self._query_cache[cache_key] = result
                # Limita tamanho do cache
                if len(self._query_cache) > 100:
                    # Remove 20% dos itens mais antigos
                    sorted_items = sorted(
                        self._query_cache.items(),
                        key=lambda x: x[1].metadata.get('cached_at', 0)
                    )
                    for key, _ in sorted_items[:20]:
                        del self._query_cache[key]
            
            logger.info(f"RAG pipeline concluído em {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Erro no pipeline RAG: {e}")
            # Retorna resultado vazio em caso de erro
            return RAGResult(
                query=query,
                retrieved_docs=[],
                reranked_docs=[],
                context_text="",
                metadata={'error': str(e), 'processing_time': time.time() - start_time},
                processing_time=time.time() - start_time,
                retrieval_stats={'error': True}
            )
    
    def _prepare_context_text(
        self,
        search_results: List[SearchResult],
        max_context_length: int = 4000
    ) -> str:
        """
        Prepara texto de contexto a partir dos resultados
        """
        if not search_results:
            return ""
        
        context_parts = []
        current_length = 0
        
        for i, result in enumerate(search_results):
            # Cabeçalho do documento
            header = f"\n--- Documento {i+1} ---"
            if result.metadata.title:
                header += f"\nTítulo: {result.metadata.title}"
            if result.metadata.source:
                header += f"\nFonte: {result.metadata.source}"
            if result.metadata.document_type:
                header += f"\nTipo: {result.metadata.document_type}"
            
            header += f"\nRelevância: {result.score:.3f}\n"
            
            # Conteúdo
            content = result.content.strip()
            
            # Estima tamanho total
            section_length = len(header) + len(content) + 2  # +2 para quebras de linha
            
            # Verifica se cabe no limite
            if current_length + section_length > max_context_length:
                # Se é o primeiro documento, trunca o conteúdo
                if i == 0:
                    available_space = max_context_length - len(header) - 50  # Reserva espaço
                    if available_space > 100:
                        content = content[:available_space] + "..."
                        context_parts.append(header + content)
                break
            
            context_parts.append(header + content)
            current_length += section_length
        
        context_text = "\n".join(context_parts)
        
        # Adiciona estatísticas no final
        stats_footer = f"\n\n--- Informações da Busca ---\nDocumentos encontrados: {len(search_results)}"
        if len(context_text) + len(stats_footer) <= max_context_length:
            context_text += stats_footer
        
        return context_text
    
    async def add_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        chunk_document: bool = True
    ) -> List[str]:
        """
        Adiciona documento ao índice vetorial
        """
        try:
            if chunk_document:
                # Faz chunking do documento
                chunks = chunk_legal_document(
                    text=content,
                    document_type=metadata.get('document_type', 'generic'),
                    metadata=metadata
                )
                
                # Converte chunks para DocumentMetadata
                documents = []
                for chunk in chunks:
                    doc_metadata = DocumentMetadata(
                        doc_id=f"{metadata.get('doc_id', 'unknown')}_{chunk.chunk_id}",
                        title=metadata.get('title', ''),
                        content=chunk.content,
                        document_type=metadata.get('document_type', 'generic'),
                        source=metadata.get('source', ''),
                        date_created=metadata.get('date_created', datetime.now()),
                        date_indexed=datetime.now(),
                        author=metadata.get('author'),
                        tags=metadata.get('tags', []),
                        tribunal=metadata.get('tribunal'),
                        area_juridica=metadata.get('area_juridica'),
                        chunk_id=chunk.chunk_id,
                        chunk_index=chunk.chunk_index,
                        total_chunks=len(chunks)
                    )
                    documents.append(doc_metadata)
                
                # Adiciona lote ao vector store
                point_ids = await self.vector_store.add_documents_batch(documents)
                
                logger.info(f"Documento adicionado com {len(chunks)} chunks")
                return point_ids
                
            else:
                # Adiciona documento inteiro
                doc_metadata = DocumentMetadata(
                    doc_id=metadata.get('doc_id', f"doc_{int(datetime.now().timestamp())}"),
                    title=metadata.get('title', ''),
                    content=content,
                    document_type=metadata.get('document_type', 'generic'),
                    source=metadata.get('source', ''),
                    date_created=metadata.get('date_created', datetime.now()),
                    date_indexed=datetime.now(),
                    author=metadata.get('author'),
                    tags=metadata.get('tags', []),
                    tribunal=metadata.get('tribunal'),
                    area_juridica=metadata.get('area_juridica')
                )
                
                point_id = await self.vector_store.add_document(doc_metadata)
                logger.info(f"Documento {doc_metadata.doc_id} adicionado")
                return [point_id] if point_id else []
                
        except Exception as e:
            logger.error(f"Erro ao adicionar documento: {e}")
            return []
    
    async def delete_document(self, doc_id: str) -> bool:
        """Remove documento do índice"""
        try:
            success = await self.vector_store.delete_document(doc_id)
            if success:
                logger.info(f"Documento {doc_id} removido")
                # Limpa cache relacionado
                self._clear_cache()
            return success
        except Exception as e:
            logger.error(f"Erro ao remover documento {doc_id}: {e}")
            return False
    
    def _clear_cache(self):
        """Limpa cache de queries"""
        self._query_cache.clear()
        logger.info("Cache de queries limpo")
    
    async def get_similar_documents(
        self,
        doc_id: str,
        limit: int = 5
    ) -> List[SearchResult]:
        """
        Encontra documentos similares a um documento específico
        """
        try:
            # Busca o documento original
            original_results = await self.vector_store.search(
                query_text="",  # Será substituído pelo embedding
                limit=1,
                filters={"doc_id": doc_id}
            )
            
            if not original_results:
                logger.warning(f"Documento {doc_id} não encontrado")
                return []
            
            original_doc = original_results[0]
            
            # Busca documentos similares
            similar_results = await self.vector_store.search(
                query_text=original_doc.content,
                limit=limit + 1,  # +1 porque o próprio documento será retornado
                filters={"doc_id": {"$ne": doc_id}}  # Exclui o documento original
            )
            
            # Remove o documento original se aparecer
            similar_results = [
                result for result in similar_results 
                if result.doc_id != doc_id
            ][:limit]
            
            logger.info(f"Encontrados {len(similar_results)} documentos similares a {doc_id}")
            return similar_results
            
        except Exception as e:
            logger.error(f"Erro ao buscar documentos similares: {e}")
            return []
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do pipeline"""
        try:
            vector_store_info = {}
            if hasattr(self.vector_store, 'get_collection_info'):
                vector_store_info = self.vector_store.get_collection_info()
            
            embedding_info = self.embedding_processor.get_model_info()
            reranker_info = self.reranker.get_model_info()
            
            return {
                'vector_store': {
                    'type': type(self.vector_store).__name__,
                    'info': vector_store_info
                },
                'embedding_processor': embedding_info,
                'reranker': reranker_info,
                'cache': {
                    'size': len(self._query_cache),
                    'ttl_seconds': self._cache_ttl
                },
                'config': {
                    'max_docs_retrieval': self.max_docs_retrieval,
                    'similarity_threshold': self.similarity_threshold,
                    'rerank_top_k': self.rerank_top_k
                }
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {'error': str(e)}


class HybridRAGPipeline(LegalRAGPipeline):
    """
    Pipeline RAG híbrido que combina busca vetorial com busca lexical
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurações para busca híbrida
        self.vector_weight = 0.7
        self.lexical_weight = 0.3
    
    async def search_and_rank(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        top_k: int = None,
        use_cache: bool = True,
        include_metadata: bool = True
    ) -> RAGResult:
        """
        Busca híbrida combinando vetorial e lexical
        """
        # Por enquanto, usa apenas busca vetorial
        # TODO: Implementar busca lexical (BM25, Elasticsearch, etc.)
        return await super().search_and_rank(
            query, filters, top_k, use_cache, include_metadata
        )


# Instância global do pipeline RAG
_global_rag_pipeline: Optional[LegalRAGPipeline] = None


def get_rag_pipeline(pipeline_type: str = "standard") -> LegalRAGPipeline:
    """Retorna instância global do pipeline RAG"""
    global _global_rag_pipeline
    if _global_rag_pipeline is None:
        if pipeline_type == "hybrid":
            _global_rag_pipeline = HybridRAGPipeline()
        else:
            _global_rag_pipeline = LegalRAGPipeline()
    return _global_rag_pipeline


async def search_legal_documents(
    query: str,
    filters: Dict[str, Any] = None,
    top_k: int = None,
    pipeline_type: str = "standard"
) -> RAGResult:
    """Função conveniente para busca de documentos jurídicos"""
    pipeline = get_rag_pipeline(pipeline_type)
    return await pipeline.search_and_rank(query, filters, top_k)


async def add_legal_document(
    content: str,
    metadata: Dict[str, Any],
    chunk_document: bool = True,
    pipeline_type: str = "standard"
) -> List[str]:
    """Função conveniente para adicionar documento jurídico"""
    pipeline = get_rag_pipeline(pipeline_type)
    return await pipeline.add_document(content, metadata, chunk_document)
