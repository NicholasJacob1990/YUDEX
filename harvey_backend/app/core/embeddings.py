"""
Embeddings jurídicos
Sistema de embeddings especializado para documentos jurídicos brasileiros
"""

import asyncio
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Union
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F
from dataclasses import dataclass
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Resultado do processamento de embedding"""
    embeddings: np.ndarray
    token_count: int
    processing_time: float
    model_used: str
    dimension: int


class LegalEmbeddingProcessor:
    """
    Processador de embeddings especializado para textos jurídicos
    Otimizado para terminologia legal brasileira
    """
    
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.default_embedding_model
        self.model = None
        self.tokenizer = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._initialize_model()
        
        # Cache para embeddings frequentes
        self._embedding_cache: Dict[str, np.ndarray] = {}
        
        # Termos jurídicos para pré-processamento
        self.legal_terms_mapping = {
            "art.": "artigo",
            "inc.": "inciso", 
            "par.": "parágrafo",
            "cf": "conforme",
            "stf": "supremo tribunal federal",
            "stj": "superior tribunal justiça",
            "tcu": "tribunal contas união",
            "tst": "tribunal superior trabalho",
            "cpc": "código processo civil",
            "cc": "código civil",
            "cf/88": "constituição federal 1988"
        }
    
    def _initialize_model(self):
        """Inicializa o modelo de embedding"""
        try:
            if "sentence-transformers" in self.model_name:
                self.model = SentenceTransformer(self.model_name, device=self.device)
                logger.info(f"Modelo SentenceTransformer carregado: {self.model_name}")
            else:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModel.from_pretrained(self.model_name).to(self.device)
                logger.info(f"Modelo HuggingFace carregado: {self.model_name}")
                
        except Exception as e:
            logger.error(f"Erro ao carregar modelo {self.model_name}: {e}")
            # Fallback para modelo básico
            self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.warning(f"Usando modelo fallback: {self.model_name}")
    
    def _preprocess_legal_text(self, text: str) -> str:
        """
        Pré-processa texto jurídico para melhorar embeddings
        """
        if not text:
            return ""
            
        # Converte para minúsculas
        text = text.lower()
        
        # Substitui abreviações jurídicas
        for abbrev, full_term in self.legal_terms_mapping.items():
            text = text.replace(abbrev, full_term)
        
        # Remove caracteres especiais excessivos
        import re
        text = re.sub(r'[^\w\s\-\.]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    async def encode_single(self, text: str, normalize: bool = True) -> EmbeddingResult:
        """
        Gera embedding para um único texto
        """
        import time
        start_time = time.time()
        
        # Verifica cache
        cache_key = f"{self.model_name}:{hash(text)}"
        if cache_key in self._embedding_cache:
            cached_embedding = self._embedding_cache[cache_key]
            return EmbeddingResult(
                embeddings=cached_embedding,
                token_count=len(text.split()),
                processing_time=time.time() - start_time,
                model_used=self.model_name,
                dimension=cached_embedding.shape[0]
            )
        
        # Pré-processa texto
        processed_text = self._preprocess_legal_text(text)
        
        try:
            if isinstance(self.model, SentenceTransformer):
                # SentenceTransformer
                embedding = self.model.encode(
                    processed_text, 
                    normalize_embeddings=normalize,
                    convert_to_numpy=True
                )
            else:
                # HuggingFace modelo customizado
                embedding = await self._encode_with_huggingface(processed_text, normalize)
            
            # Cache resultado
            self._embedding_cache[cache_key] = embedding
            
            # Limita tamanho do cache
            if len(self._embedding_cache) > 1000:
                # Remove 20% dos itens mais antigos
                items_to_remove = list(self._embedding_cache.keys())[:200]
                for key in items_to_remove:
                    del self._embedding_cache[key]
            
            return EmbeddingResult(
                embeddings=embedding,
                token_count=len(processed_text.split()),
                processing_time=time.time() - start_time,
                model_used=self.model_name,
                dimension=embedding.shape[0]
            )
            
        except Exception as e:
            logger.error(f"Erro ao gerar embedding: {e}")
            # Retorna embedding zero como fallback
            dim = 384  # Dimensão padrão
            return EmbeddingResult(
                embeddings=np.zeros(dim),
                token_count=0,
                processing_time=time.time() - start_time,
                model_used=self.model_name,
                dimension=dim
            )
    
    async def _encode_with_huggingface(self, text: str, normalize: bool) -> np.ndarray:
        """Encoding usando modelos HuggingFace personalizados"""
        
        # Tokeniza
        inputs = self.tokenizer(
            text, 
            return_tensors="pt", 
            max_length=512, 
            truncation=True, 
            padding=True
        ).to(self.device)
        
        # Gera embedding
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Mean pooling
            embeddings = outputs.last_hidden_state.mean(dim=1)
            
            if normalize:
                embeddings = F.normalize(embeddings, p=2, dim=1)
        
        return embeddings.cpu().numpy().squeeze()
    
    async def encode_batch(
        self, 
        texts: List[str], 
        batch_size: int = 32,
        normalize: bool = True
    ) -> List[EmbeddingResult]:
        """
        Gera embeddings para múltiplos textos em lotes
        """
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_tasks = [
                self.encode_single(text, normalize) 
                for text in batch
            ]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)
        
        return results
    
    def calculate_similarity(
        self, 
        embedding1: np.ndarray, 
        embedding2: np.ndarray,
        metric: str = "cosine"
    ) -> float:
        """
        Calcula similaridade entre dois embeddings
        """
        if metric == "cosine":
            # Normaliza se necessário
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return np.dot(embedding1, embedding2) / (norm1 * norm2)
            
        elif metric == "euclidean":
            return 1.0 / (1.0 + np.linalg.norm(embedding1 - embedding2))
            
        elif metric == "manhattan":
            return 1.0 / (1.0 + np.sum(np.abs(embedding1 - embedding2)))
            
        else:
            raise ValueError(f"Métrica não suportada: {metric}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Retorna informações sobre o modelo atual"""
        try:
            if isinstance(self.model, SentenceTransformer):
                dimension = self.model.get_sentence_embedding_dimension()
            else:
                # Estima dimensão com texto de teste
                test_embedding = asyncio.run(self.encode_single("teste"))
                dimension = test_embedding.dimension
                
            return {
                "model_name": self.model_name,
                "dimension": dimension,
                "device": str(self.device),
                "model_type": "SentenceTransformer" if isinstance(self.model, SentenceTransformer) else "HuggingFace",
                "cache_size": len(self._embedding_cache)
            }
        except Exception as e:
            logger.error(f"Erro ao obter informações do modelo: {e}")
            return {
                "model_name": self.model_name,
                "error": str(e)
            }


# Instância global do processador
_global_processor: Optional[LegalEmbeddingProcessor] = None


def get_embedding_processor() -> LegalEmbeddingProcessor:
    """Retorna instância global do processador de embeddings"""
    global _global_processor
    if _global_processor is None:
        _global_processor = LegalEmbeddingProcessor()
    return _global_processor


async def embed_text(text: str, normalize: bool = True) -> EmbeddingResult:
    """Função conveniente para gerar embedding de um texto"""
    processor = get_embedding_processor()
    return await processor.encode_single(text, normalize)


async def embed_texts(texts: List[str], normalize: bool = True) -> List[EmbeddingResult]:
    """Função conveniente para gerar embeddings de múltiplos textos"""
    processor = get_embedding_processor()
    return await processor.encode_batch(texts, normalize=normalize)


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calcula similaridade entre dois textos"""
    processor = get_embedding_processor()
    
    # Gera embeddings
    result1 = asyncio.run(processor.encode_single(text1))
    result2 = asyncio.run(processor.encode_single(text2))
    
    # Calcula similaridade
    return processor.calculate_similarity(
        result1.embeddings, 
        result2.embeddings
    )
