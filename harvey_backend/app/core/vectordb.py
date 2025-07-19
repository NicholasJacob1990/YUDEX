"""
Vector database (Qdrant/FAISS)
Gerenciamento de banco de dados vetorial para documentos jurídicos
"""

import asyncio
import logging
import numpy as np
import uuid
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, SearchRequest,
    UpdateStatus, CollectionInfo
)
import faiss
import pickle
import os
from ..config import settings
from .embeddings import get_embedding_processor, EmbeddingResult

logger = logging.getLogger(__name__)


@dataclass
class DocumentMetadata:
    """Metadados de um documento jurídico"""
    doc_id: str
    title: str
    content: str
    document_type: str  # parecer, lei, jurisprudencia, doutrina
    source: str
    date_created: datetime
    date_indexed: datetime
    author: Optional[str] = None
    tags: List[str] = None
    tribunal: Optional[str] = None
    area_juridica: Optional[str] = None
    chunk_id: Optional[str] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None


@dataclass
class SearchResult:
    """Resultado de busca vetorial"""
    doc_id: str
    score: float
    content: str
    metadata: DocumentMetadata
    embedding: Optional[np.ndarray] = None


class QdrantVectorStore:
    """
    Cliente Qdrant especializado para documentos jurídicos
    """
    
    def __init__(
        self, 
        host: str = None, 
        port: int = None, 
        collection_name: str = None,
        api_key: str = None
    ):
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self.collection_name = collection_name or settings.qdrant_collection
        self.api_key = api_key or settings.qdrant_api_key
        
        self.client = None
        self.embedding_processor = get_embedding_processor()
        self._connect()
    
    def _connect(self):
        """Conecta ao Qdrant"""
        try:
            if self.api_key:
                self.client = QdrantClient(
                    host=self.host,
                    port=self.port,
                    api_key=self.api_key
                )
            else:
                self.client = QdrantClient(
                    host=self.host,
                    port=self.port
                )
            
            logger.info(f"Conectado ao Qdrant em {self.host}:{self.port}")
            
            # Verifica se a coleção existe
            self._ensure_collection_exists()
            
        except Exception as e:
            logger.error(f"Erro ao conectar ao Qdrant: {e}")
            raise
    
    def _ensure_collection_exists(self):
        """Garante que a coleção existe"""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Cria a coleção
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # Dimensão padrão, será ajustada dinamicamente
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Coleção '{self.collection_name}' criada")
            else:
                logger.info(f"Coleção '{self.collection_name}' já existe")
                
        except Exception as e:
            logger.error(f"Erro ao verificar/criar coleção: {e}")
            raise
    
    async def add_document(
        self, 
        document: DocumentMetadata, 
        embedding: Optional[np.ndarray] = None
    ) -> str:
        """
        Adiciona um documento ao banco vetorial
        """
        try:
            # Gera embedding se não fornecido
            if embedding is None:
                embedding_result = await self.embedding_processor.encode_single(document.content)
                embedding = embedding_result.embeddings
            
            # Cria ponto para inserção
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding.tolist(),
                payload={
                    "doc_id": document.doc_id,
                    "title": document.title,
                    "content": document.content,
                    "document_type": document.document_type,
                    "source": document.source,
                    "date_created": document.date_created.isoformat(),
                    "date_indexed": document.date_indexed.isoformat(),
                    "author": document.author,
                    "tags": document.tags or [],
                    "tribunal": document.tribunal,
                    "area_juridica": document.area_juridica,
                    "chunk_id": document.chunk_id,
                    "chunk_index": document.chunk_index,
                    "total_chunks": document.total_chunks
                }
            )
            
            # Insere no Qdrant
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            if operation_info.status == UpdateStatus.COMPLETED:
                logger.info(f"Documento {document.doc_id} adicionado com sucesso")
                return point.id
            else:
                logger.error(f"Falha ao adicionar documento {document.doc_id}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao adicionar documento: {e}")
            raise
    
    async def add_documents_batch(
        self, 
        documents: List[DocumentMetadata],
        embeddings: Optional[List[np.ndarray]] = None
    ) -> List[str]:
        """
        Adiciona múltiplos documentos em lote
        """
        if embeddings is None:
            # Gera embeddings para todos os documentos
            texts = [doc.content for doc in documents]
            embedding_results = await self.embedding_processor.encode_batch(texts)
            embeddings = [result.embeddings for result in embedding_results]
        
        points = []
        point_ids = []
        
        for i, (document, embedding) in enumerate(zip(documents, embeddings)):
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)
            
            point = PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload={
                    "doc_id": document.doc_id,
                    "title": document.title,
                    "content": document.content,
                    "document_type": document.document_type,
                    "source": document.source,
                    "date_created": document.date_created.isoformat(),
                    "date_indexed": document.date_indexed.isoformat(),
                    "author": document.author,
                    "tags": document.tags or [],
                    "tribunal": document.tribunal,
                    "area_juridica": document.area_juridica,
                    "chunk_id": document.chunk_id,
                    "chunk_index": document.chunk_index,
                    "total_chunks": document.total_chunks
                }
            )
            points.append(point)
        
        try:
            # Insere lote
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            if operation_info.status == UpdateStatus.COMPLETED:
                logger.info(f"Lote de {len(documents)} documentos adicionado com sucesso")
                return point_ids
            else:
                logger.error(f"Falha ao adicionar lote de documentos")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao adicionar lote de documentos: {e}")
            raise
    
    async def search(
        self,
        query_text: str = None,
        query_embedding: np.ndarray = None,
        limit: int = 10,
        filters: Dict[str, Any] = None,
        score_threshold: float = None
    ) -> List[SearchResult]:
        """
        Busca documentos similares
        """
        try:
            # Gera embedding da query se não fornecido
            if query_embedding is None and query_text:
                embedding_result = await self.embedding_processor.encode_single(query_text)
                query_embedding = embedding_result.embeddings
            
            if query_embedding is None:
                raise ValueError("query_text ou query_embedding deve ser fornecido")
            
            # Constrói filtros Qdrant
            qdrant_filter = None
            if filters:
                conditions = []
                for field, value in filters.items():
                    if isinstance(value, list):
                        # Filtro OR para listas
                        for v in value:
                            conditions.append(
                                FieldCondition(key=field, match={"value": v})
                            )
                    else:
                        conditions.append(
                            FieldCondition(key=field, match={"value": value})
                        )
                
                if conditions:
                    qdrant_filter = Filter(should=conditions)
            
            # Executa busca
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                limit=limit,
                query_filter=qdrant_filter,
                score_threshold=score_threshold
            )
            
            # Converte resultados
            results = []
            for result in search_results:
                payload = result.payload
                
                metadata = DocumentMetadata(
                    doc_id=payload["doc_id"],
                    title=payload["title"],
                    content=payload["content"],
                    document_type=payload["document_type"],
                    source=payload["source"],
                    date_created=datetime.fromisoformat(payload["date_created"]),
                    date_indexed=datetime.fromisoformat(payload["date_indexed"]),
                    author=payload.get("author"),
                    tags=payload.get("tags", []),
                    tribunal=payload.get("tribunal"),
                    area_juridica=payload.get("area_juridica"),
                    chunk_id=payload.get("chunk_id"),
                    chunk_index=payload.get("chunk_index"),
                    total_chunks=payload.get("total_chunks")
                )
                
                search_result = SearchResult(
                    doc_id=payload["doc_id"],
                    score=result.score,
                    content=payload["content"],
                    metadata=metadata
                )
                
                results.append(search_result)
            
            logger.info(f"Busca retornou {len(results)} resultados")
            return results
            
        except Exception as e:
            logger.error(f"Erro na busca: {e}")
            raise
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Retorna informações sobre a coleção"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": info.config.params.vectors.size,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Erro ao obter informações da coleção: {e}")
            return {}
    
    async def delete_document(self, doc_id: str) -> bool:
        """Remove um documento"""
        try:
            # Busca pontos com o doc_id
            search_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="doc_id", match={"value": doc_id})]
                ),
                limit=1000  # Assumindo que um doc_id não tem mais que 1000 chunks
            )
            
            point_ids = [point.id for point in search_result[0]]
            
            if point_ids:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids
                )
                logger.info(f"Documento {doc_id} removido ({len(point_ids)} pontos)")
                return True
            else:
                logger.warning(f"Documento {doc_id} não encontrado para remoção")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao remover documento {doc_id}: {e}")
            return False


class FAISSVectorStore:
    """
    Cliente FAISS para busca vetorial local (fallback)
    """
    
    def __init__(self, index_file: str = "legal_docs.faiss"):
        self.index_file = index_file
        self.index = None
        self.metadata_store = {}
        self.id_mapping = {}
        self.next_id = 0
        
        self.embedding_processor = get_embedding_processor()
        self._load_index()
    
    def _load_index(self):
        """Carrega ou cria índice FAISS"""
        if os.path.exists(self.index_file):
            try:
                self.index = faiss.read_index(self.index_file)
                
                # Carrega metadados
                metadata_file = self.index_file.replace(".faiss", "_metadata.pkl")
                if os.path.exists(metadata_file):
                    with open(metadata_file, "rb") as f:
                        data = pickle.load(f)
                        self.metadata_store = data.get("metadata_store", {})
                        self.id_mapping = data.get("id_mapping", {})
                        self.next_id = data.get("next_id", 0)
                
                logger.info(f"Índice FAISS carregado: {self.index.ntotal} vetores")
            except Exception as e:
                logger.error(f"Erro ao carregar índice FAISS: {e}")
                self._create_new_index()
        else:
            self._create_new_index()
    
    def _create_new_index(self):
        """Cria novo índice FAISS"""
        # Dimensão padrão - será ajustada dinamicamente
        dimension = 384
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product para similaridade coseno
        logger.info(f"Novo índice FAISS criado com dimensão {dimension}")
    
    def _save_index(self):
        """Salva índice e metadados"""
        try:
            faiss.write_index(self.index, self.index_file)
            
            # Salva metadados
            metadata_file = self.index_file.replace(".faiss", "_metadata.pkl")
            with open(metadata_file, "wb") as f:
                pickle.dump({
                    "metadata_store": self.metadata_store,
                    "id_mapping": self.id_mapping,
                    "next_id": self.next_id
                }, f)
            
            logger.info("Índice FAISS salvo")
        except Exception as e:
            logger.error(f"Erro ao salvar índice FAISS: {e}")
    
    async def add_document(
        self, 
        document: DocumentMetadata, 
        embedding: Optional[np.ndarray] = None
    ) -> str:
        """Adiciona documento ao índice FAISS"""
        try:
            if embedding is None:
                embedding_result = await self.embedding_processor.encode_single(document.content)
                embedding = embedding_result.embeddings
            
            # Normaliza embedding para similaridade coseno
            embedding = embedding / np.linalg.norm(embedding)
            
            # Adiciona ao índice
            self.index.add(embedding.reshape(1, -1))
            
            # Armazena metadados
            doc_internal_id = self.next_id
            self.id_mapping[document.doc_id] = doc_internal_id
            self.metadata_store[doc_internal_id] = asdict(document)
            self.next_id += 1
            
            # Salva periodicamente
            if self.next_id % 100 == 0:
                self._save_index()
            
            logger.info(f"Documento {document.doc_id} adicionado ao FAISS")
            return document.doc_id
            
        except Exception as e:
            logger.error(f"Erro ao adicionar documento ao FAISS: {e}")
            raise
    
    async def search(
        self,
        query_text: str = None,
        query_embedding: np.ndarray = None,
        limit: int = 10,
        filters: Dict[str, Any] = None,
        score_threshold: float = None
    ) -> List[SearchResult]:
        """Busca no índice FAISS"""
        try:
            if query_embedding is None and query_text:
                embedding_result = await self.embedding_processor.encode_single(query_text)
                query_embedding = embedding_result.embeddings
            
            if query_embedding is None:
                raise ValueError("query_text ou query_embedding deve ser fornecido")
            
            # Normaliza query
            query_embedding = query_embedding / np.linalg.norm(query_embedding)
            
            # Busca
            scores, indices = self.index.search(query_embedding.reshape(1, -1), limit)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # FAISS retorna -1 para índices inválidos
                    continue
                
                if score_threshold and score < score_threshold:
                    continue
                
                metadata_dict = self.metadata_store.get(idx, {})
                if not metadata_dict:
                    continue
                
                # Aplica filtros se especificados
                if filters:
                    skip = False
                    for field, value in filters.items():
                        if field in metadata_dict:
                            if isinstance(value, list):
                                if metadata_dict[field] not in value:
                                    skip = True
                                    break
                            else:
                                if metadata_dict[field] != value:
                                    skip = True
                                    break
                    if skip:
                        continue
                
                # Reconstrói metadados
                metadata = DocumentMetadata(
                    doc_id=metadata_dict["doc_id"],
                    title=metadata_dict["title"],
                    content=metadata_dict["content"],
                    document_type=metadata_dict["document_type"],
                    source=metadata_dict["source"],
                    date_created=datetime.fromisoformat(metadata_dict["date_created"]),
                    date_indexed=datetime.fromisoformat(metadata_dict["date_indexed"]),
                    author=metadata_dict.get("author"),
                    tags=metadata_dict.get("tags", []),
                    tribunal=metadata_dict.get("tribunal"),
                    area_juridica=metadata_dict.get("area_juridica"),
                    chunk_id=metadata_dict.get("chunk_id"),
                    chunk_index=metadata_dict.get("chunk_index"),
                    total_chunks=metadata_dict.get("total_chunks")
                )
                
                result = SearchResult(
                    doc_id=metadata_dict["doc_id"],
                    score=float(score),
                    content=metadata_dict["content"],
                    metadata=metadata
                )
                
                results.append(result)
            
            logger.info(f"Busca FAISS retornou {len(results)} resultados")
            return results
            
        except Exception as e:
            logger.error(f"Erro na busca FAISS: {e}")
            raise


# Factory para criar instância do vector store
def create_vector_store(store_type: str = "qdrant") -> Union[QdrantVectorStore, FAISSVectorStore]:
    """Cria instância do vector store"""
    if store_type.lower() == "qdrant":
        return QdrantVectorStore()
    elif store_type.lower() == "faiss":
        return FAISSVectorStore()
    else:
        raise ValueError(f"Tipo de vector store não suportado: {store_type}")


# Instância global
_global_vector_store = None


def get_vector_store() -> Union[QdrantVectorStore, FAISSVectorStore]:
    """Retorna instância global do vector store"""
    global _global_vector_store
    if _global_vector_store is None:
        try:
            _global_vector_store = create_vector_store("qdrant")
        except Exception as e:
            logger.warning(f"Falha ao conectar Qdrant, usando FAISS: {e}")
            _global_vector_store = create_vector_store("faiss")
    return _global_vector_store
