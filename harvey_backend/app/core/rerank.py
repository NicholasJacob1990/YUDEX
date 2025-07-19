"""
Reranker supervisionado
Sistema de re-ranking especializado para documentos jurídicos
"""

import asyncio
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from sentence_transformers import CrossEncoder
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from ..config import settings
from .vectordb import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class RerankResult:
    """Resultado do re-ranking"""
    original_results: List[SearchResult]
    reranked_results: List[SearchResult]
    rerank_scores: List[float]
    processing_time: float
    model_used: str


class LegalDocumentReranker:
    """
    Re-ranker especializado para documentos jurídicos brasileiros
    Usa modelos cross-encoder para melhorar a relevância dos resultados
    """
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.rerank_model
        self.model = None
        self.tokenizer = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._initialize_model()
        
        # Pesos específicos para diferentes tipos de documento
        self.document_type_weights = {
            'lei': 1.2,
            'decreto': 1.1,
            'jurisprudencia': 1.3,
            'doutrina': 1.0,
            'parecer': 0.9,
            'peticao': 0.8,
            'generic': 1.0
        }
        
        # Pesos para diferentes tribunais
        self.tribunal_weights = {
            'STF': 1.5,
            'STJ': 1.4,
            'TST': 1.2,
            'TCU': 1.3,
            'TRF': 1.1,
            'TJSP': 1.0,
            'TJRJ': 1.0
        }
    
    def _initialize_model(self):
        """Inicializa o modelo de re-ranking"""
        try:
            if "cross-encoder" in self.model_name.lower():
                # Usa SentenceTransformers CrossEncoder
                self.model = CrossEncoder(self.model_name, device=self.device)
                logger.info(f"CrossEncoder carregado: {self.model_name}")
            else:
                # Usa HuggingFace modelo de classificação
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name
                ).to(self.device)
                logger.info(f"Modelo HuggingFace carregado: {self.model_name}")
                
        except Exception as e:
            logger.error(f"Erro ao carregar modelo {self.model_name}: {e}")
            # Fallback para modelo básico
            self.model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            self.model = CrossEncoder(self.model_name, device=self.device)
            logger.warning(f"Usando modelo fallback: {self.model_name}")
    
    async def rerank(
        self,
        query: str,
        search_results: List[SearchResult],
        top_k: int = None,
        use_legal_features: bool = True
    ) -> RerankResult:
        """
        Re-ranking principal dos resultados de busca
        """
        import time
        start_time = time.time()
        
        if not search_results:
            return RerankResult(
                original_results=[],
                reranked_results=[],
                rerank_scores=[],
                processing_time=0.0,
                model_used=self.model_name
            )
        
        top_k = top_k or settings.rerank_top_k
        
        # Prepara pares query-documento
        pairs = [(query, result.content) for result in search_results]
        
        # Calcula scores de re-ranking
        if isinstance(self.model, CrossEncoder):
            rerank_scores = await self._rerank_with_cross_encoder(pairs)
        else:
            rerank_scores = await self._rerank_with_huggingface(pairs)
        
        # Aplica features jurídicas se habilitado
        if use_legal_features:
            rerank_scores = self._apply_legal_features(
                query, search_results, rerank_scores
            )
        
        # Ordena resultados por score
        scored_results = list(zip(search_results, rerank_scores))
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # Pega top-k
        reranked_results = [result for result, _ in scored_results[:top_k]]
        final_scores = [score for _, score in scored_results[:top_k]]
        
        processing_time = time.time() - start_time
        
        logger.info(f"Re-ranking concluído: {len(search_results)} -> {len(reranked_results)} em {processing_time:.2f}s")
        
        return RerankResult(
            original_results=search_results,
            reranked_results=reranked_results,
            rerank_scores=final_scores,
            processing_time=processing_time,
            model_used=self.model_name
        )
    
    async def _rerank_with_cross_encoder(self, pairs: List[Tuple[str, str]]) -> List[float]:
        """Re-ranking usando CrossEncoder"""
        try:
            # CrossEncoder pode processar lotes
            scores = self.model.predict(pairs)
            return scores.tolist() if hasattr(scores, 'tolist') else list(scores)
        except Exception as e:
            logger.error(f"Erro no re-ranking com CrossEncoder: {e}")
            # Retorna scores neutros
            return [0.5] * len(pairs)
    
    async def _rerank_with_huggingface(self, pairs: List[Tuple[str, str]]) -> List[float]:
        """Re-ranking usando modelo HuggingFace"""
        scores = []
        
        try:
            for query, doc in pairs:
                # Tokeniza par query-documento
                inputs = self.tokenizer(
                    query,
                    doc,
                    return_tensors="pt",
                    max_length=512,
                    truncation=True,
                    padding=True
                ).to(self.device)
                
                # Calcula score
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    # Aplica softmax para obter probabilidade
                    logits = outputs.logits
                    score = torch.softmax(logits, dim=-1)[0, 1].item()  # Assume classe 1 = relevante
                    scores.append(score)
            
            return scores
            
        except Exception as e:
            logger.error(f"Erro no re-ranking com HuggingFace: {e}")
            return [0.5] * len(pairs)
    
    def _apply_legal_features(
        self,
        query: str,
        search_results: List[SearchResult],
        base_scores: List[float]
    ) -> List[float]:
        """
        Aplica features específicas do domínio jurídico
        """
        enhanced_scores = []
        query_lower = query.lower()
        
        for i, (result, base_score) in enumerate(zip(search_results, base_scores)):
            enhanced_score = base_score
            
            # 1. Boost por tipo de documento
            doc_type = result.metadata.document_type
            type_weight = self.document_type_weights.get(doc_type, 1.0)
            enhanced_score *= type_weight
            
            # 2. Boost por tribunal (se aplicável)
            tribunal = result.metadata.tribunal
            if tribunal:
                tribunal_weight = self.tribunal_weights.get(tribunal.upper(), 1.0)
                enhanced_score *= tribunal_weight
            
            # 3. Boost por data (documentos mais recentes têm peso maior)
            date_boost = self._calculate_date_boost(result.metadata.date_created)
            enhanced_score *= date_boost
            
            # 4. Boost por correspondência de termos jurídicos
            legal_term_boost = self._calculate_legal_term_boost(query_lower, result.content.lower())
            enhanced_score *= legal_term_boost
            
            # 5. Penalidade por chunks muito pequenos
            length_penalty = self._calculate_length_penalty(result.content)
            enhanced_score *= length_penalty
            
            # 6. Boost por tags relevantes
            tag_boost = self._calculate_tag_boost(query_lower, result.metadata.tags or [])
            enhanced_score *= tag_boost
            
            enhanced_scores.append(enhanced_score)
        
        return enhanced_scores
    
    def _calculate_date_boost(self, date_created) -> float:
        """Calcula boost baseado na data do documento"""
        try:
            from datetime import datetime, timedelta
            
            if not date_created:
                return 1.0
            
            now = datetime.now()
            if hasattr(date_created, 'year'):
                document_date = date_created
            else:
                return 1.0
            
            # Documentos dos últimos 2 anos têm boost
            years_old = (now - document_date).days / 365.25
            
            if years_old <= 1:
                return 1.2  # Muito recente
            elif years_old <= 2:
                return 1.1  # Recente
            elif years_old <= 5:
                return 1.0  # Normal
            else:
                return 0.95  # Mais antigo, leve penalidade
                
        except Exception:
            return 1.0
    
    def _calculate_legal_term_boost(self, query: str, content: str) -> float:
        """Calcula boost baseado em termos jurídicos específicos"""
        
        # Termos jurídicos importantes
        important_legal_terms = [
            'artigo', 'art.', 'parágrafo', 'inciso', 'alínea',
            'lei', 'decreto', 'resolução', 'portaria',
            'constituição', 'código', 'súmula',
            'jurisprudência', 'precedente', 'entendimento',
            'administrativo', 'civil', 'penal', 'tributário',
            'trabalhista', 'constitucional', 'processual'
        ]
        
        # Institutions e tribunais
        legal_institutions = [
            'stf', 'stj', 'tst', 'tcu', 'trf', 'tjsp', 'tjrj',
            'supremo', 'superior', 'tribunal', 'federal', 'justiça'
        ]
        
        boost = 1.0
        
        # Conta matches de termos importantes
        for term in important_legal_terms:
            if term in query and term in content:
                boost += 0.05  # Pequeno boost por termo
        
        # Conta matches de instituições
        for institution in legal_institutions:
            if institution in query and institution in content:
                boost += 0.1  # Boost maior para instituições
        
        # Boost por números de artigos/leis correspondentes
        import re
        
        # Procura por padrões como "art. 123", "lei 8.666"
        art_pattern = r'art\.?\s*(\d+)'
        lei_pattern = r'lei\s*n?[ºª°]?\s*(\d+[\.\d/]*)'
        
        query_arts = set(re.findall(art_pattern, query, re.IGNORECASE))
        content_arts = set(re.findall(art_pattern, content, re.IGNORECASE))
        
        query_leis = set(re.findall(lei_pattern, query, re.IGNORECASE))
        content_leis = set(re.findall(lei_pattern, content, re.IGNORECASE))
        
        # Boost por correspondência exata de artigos/leis
        if query_arts & content_arts:  # Interseção
            boost += 0.2
        
        if query_leis & content_leis:
            boost += 0.3
        
        return min(boost, 2.0)  # Limita boost máximo
    
    def _calculate_length_penalty(self, content: str) -> float:
        """Aplica penalidade para chunks muito pequenos"""
        content_length = len(content.strip())
        
        if content_length < 100:
            return 0.7  # Penalidade severa para chunks muito pequenos
        elif content_length < 200:
            return 0.85  # Penalidade moderada
        elif content_length < 300:
            return 0.95  # Penalidade leve
        else:
            return 1.0  # Sem penalidade
    
    def _calculate_tag_boost(self, query: str, tags: List[str]) -> float:
        """Calcula boost baseado em tags relevantes"""
        if not tags:
            return 1.0
        
        boost = 1.0
        query_words = set(query.split())
        
        for tag in tags:
            tag_words = set(tag.lower().split())
            # Se há interseção entre palavras da query e da tag
            if query_words & tag_words:
                boost += 0.1
        
        return min(boost, 1.5)  # Limita boost máximo
    
    def get_model_info(self) -> Dict[str, Any]:
        """Retorna informações sobre o modelo de re-ranking"""
        return {
            "model_name": self.model_name,
            "model_type": "CrossEncoder" if isinstance(self.model, CrossEncoder) else "HuggingFace",
            "device": str(self.device),
            "document_type_weights": self.document_type_weights,
            "tribunal_weights": self.tribunal_weights
        }


class HybridReranker:
    """
    Re-ranker híbrido que combina múltiplas estratégias
    """
    
    def __init__(self):
        self.semantic_reranker = LegalDocumentReranker()
        
        # Pesos para combinação
        self.combination_weights = {
            'semantic_score': 0.6,
            'original_score': 0.2,
            'legal_features': 0.2
        }
    
    async def rerank(
        self,
        query: str,
        search_results: List[SearchResult],
        top_k: int = None
    ) -> RerankResult:
        """
        Re-ranking híbrido combinando múltiplas estratégias
        """
        import time
        start_time = time.time()
        
        if not search_results:
            return RerankResult(
                original_results=[],
                reranked_results=[],
                rerank_scores=[],
                processing_time=0.0,
                model_used="hybrid"
            )
        
        # 1. Re-ranking semântico
        semantic_result = await self.semantic_reranker.rerank(
            query, search_results, len(search_results), use_legal_features=False
        )
        
        # 2. Scores originais (normalizados)
        original_scores = [result.score for result in search_results]
        max_original = max(original_scores) if original_scores else 1.0
        normalized_original = [score / max_original for score in original_scores]
        
        # 3. Features jurídicas
        legal_scores = self.semantic_reranker._apply_legal_features(
            query, search_results, [1.0] * len(search_results)
        )
        
        # 4. Combina scores
        final_scores = []
        for i in range(len(search_results)):
            semantic_score = semantic_result.rerank_scores[i] if i < len(semantic_result.rerank_scores) else 0.5
            original_score = normalized_original[i]
            legal_score = legal_scores[i]
            
            combined_score = (
                self.combination_weights['semantic_score'] * semantic_score +
                self.combination_weights['original_score'] * original_score +
                self.combination_weights['legal_features'] * (legal_score - 1.0)  # legal_score é multiplicador
            )
            
            final_scores.append(combined_score)
        
        # 5. Ordena e seleciona top-k
        top_k = top_k or settings.rerank_top_k
        scored_results = list(zip(search_results, final_scores))
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        reranked_results = [result for result, _ in scored_results[:top_k]]
        final_scores_top_k = [score for _, score in scored_results[:top_k]]
        
        processing_time = time.time() - start_time
        
        return RerankResult(
            original_results=search_results,
            reranked_results=reranked_results,
            rerank_scores=final_scores_top_k,
            processing_time=processing_time,
            model_used="hybrid"
        )


# Instância global do re-ranker
_global_reranker: Optional[Union[LegalDocumentReranker, HybridReranker]] = None


def get_reranker(reranker_type: str = "legal") -> Union[LegalDocumentReranker, HybridReranker]:
    """Retorna instância global do re-ranker"""
    global _global_reranker
    if _global_reranker is None:
        if reranker_type == "hybrid":
            _global_reranker = HybridReranker()
        else:
            _global_reranker = LegalDocumentReranker()
    return _global_reranker


async def rerank_search_results(
    query: str,
    search_results: List[SearchResult],
    top_k: int = None,
    reranker_type: str = "legal"
) -> RerankResult:
    """Função conveniente para re-ranking"""
    reranker = get_reranker(reranker_type)
    return await reranker.rerank(query, search_results, top_k)
