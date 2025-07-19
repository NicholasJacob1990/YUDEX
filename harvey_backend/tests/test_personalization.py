"""
Testes para o sistema de personalização por centroides
"""

import pytest
import numpy as np
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.core.personalization import CentroidPersonalizer, get_personalizer, personalize_query_vector
from app.core.rag_bridge import RagBridge, get_rag_bridge, search_documents
from scripts.calculate_centroids import CentroidCalculator

class TestCentroidPersonalizer:
    """Testes para a classe CentroidPersonalizer"""
    
    @pytest.fixture
    def personalizer(self):
        """Fixture para criar um personalizador"""
        return CentroidPersonalizer()
    
    @pytest.fixture
    def mock_redis(self):
        """Mock do Redis"""
        mock = Mock()
        mock.get.return_value = None
        mock.ping.return_value = True
        return mock
    
    @pytest.fixture
    def sample_centroid(self):
        """Centroide de exemplo"""
        centroid = np.random.rand(768)
        return centroid / np.linalg.norm(centroid)
    
    @pytest.fixture
    def sample_query_vector(self):
        """Vetor de query de exemplo"""
        vector = np.random.rand(768)
        return vector / np.linalg.norm(vector)
    
    @pytest.mark.asyncio
    async def test_get_centroid_not_found(self, personalizer, mock_redis):
        """Testa busca de centroide não encontrado"""
        with patch.object(personalizer, 'redis_client', mock_redis):
            mock_redis.get.return_value = None
            
            result = await personalizer.get_centroid("tenant1", "tag1")
            
            assert result is None
            mock_redis.get.assert_called_once_with("centroid:tenant1:tag1")
    
    @pytest.mark.asyncio
    async def test_get_centroid_found(self, personalizer, mock_redis, sample_centroid):
        """Testa busca de centroide encontrado"""
        with patch.object(personalizer, 'redis_client', mock_redis):
            mock_redis.get.return_value = sample_centroid.astype(np.float32).tobytes()
            
            result = await personalizer.get_centroid("tenant1", "tag1")
            
            assert result is not None
            assert len(result) == 768
            assert np.allclose(result, sample_centroid, atol=1e-6)
    
    @pytest.mark.asyncio
    async def test_infer_query_tag(self, personalizer):
        """Testa inferência de tags"""
        # Teste com palavras-chave de imóveis
        tag = await personalizer.infer_query_tag("Contrato de aluguel de casa")
        assert tag == "contratos_imobiliarios"
        
        # Teste com palavras-chave tributárias
        tag = await personalizer.infer_query_tag("Imposto de renda pessoa física")
        assert tag == "litigios_tributarios"
        
        # Teste com query genérica
        tag = await personalizer.infer_query_tag("Consulta genérica")
        assert tag == "direito_civil"  # Fallback
    
    @pytest.mark.asyncio
    async def test_apply_personalization_no_centroid(self, personalizer, sample_query_vector):
        """Testa personalização sem centroide disponível"""
        with patch.object(personalizer, 'get_centroid', return_value=None):
            result = await personalizer.apply_personalization(
                query_vector=sample_query_vector,
                tenant_id="tenant1",
                query="test query"
            )
            
            # Deve retornar o vetor original
            assert np.allclose(result, sample_query_vector)
    
    @pytest.mark.asyncio
    async def test_apply_personalization_with_centroid(self, personalizer, sample_query_vector, sample_centroid):
        """Testa personalização com centroide"""
        with patch.object(personalizer, 'get_centroid', return_value=sample_centroid):
            result = await personalizer.apply_personalization(
                query_vector=sample_query_vector,
                tenant_id="tenant1",
                query="test query",
                alpha=0.5
            )
            
            # Deve retornar vetor modificado
            assert not np.allclose(result, sample_query_vector)
            assert np.allclose(np.linalg.norm(result), 1.0)  # Deve estar normalizado
    
    @pytest.mark.asyncio
    async def test_get_personalization_stats(self, personalizer, mock_redis):
        """Testa obtenção de estatísticas"""
        with patch.object(personalizer, 'redis_client', mock_redis):
            mock_redis.keys.return_value = [
                b"centroid:tenant1:tag1",
                b"centroid:tenant1:tag2"
            ]
            mock_redis.get.return_value = b'{"updated_at": "2023-01-01T00:00:00"}'
            
            stats = await personalizer.get_personalization_stats("tenant1")
            
            assert stats["tenant_id"] == "tenant1"
            assert stats["total_centroids"] == 2
            assert len(stats["tags"]) == 2
    
    def test_clear_cache(self, personalizer):
        """Testa limpeza do cache"""
        personalizer._centroid_cache = {"test": "data"}
        personalizer.clear_cache()
        assert len(personalizer._centroid_cache) == 0


class TestCentroidCalculator:
    """Testes para a classe CentroidCalculator"""
    
    @pytest.fixture
    def calculator(self):
        """Fixture para criar um calculador"""
        return CentroidCalculator()
    
    @pytest.fixture
    def mock_redis(self):
        """Mock do Redis"""
        mock = Mock()
        mock.setex.return_value = True
        return mock
    
    @pytest.fixture
    def sample_vectors(self):
        """Vetores de exemplo"""
        vectors = []
        for _ in range(10):
            vector = np.random.rand(768)
            vectors.append(vector / np.linalg.norm(vector))
        return vectors
    
    @pytest.mark.asyncio
    async def test_get_tenant_tags(self, calculator):
        """Testa obtenção de tags do tenant"""
        tags = await calculator.get_tenant_tags("tenant1")
        
        assert isinstance(tags, list)
        assert len(tags) > 0
        assert "contratos_imobiliarios" in tags
        assert "litigios_tributarios" in tags
    
    @pytest.mark.asyncio
    async def test_get_vectors_for_tag(self, calculator):
        """Testa busca de vetores por tag"""
        vectors = await calculator.get_vectors_for_tag("tenant1", "tag1")
        
        assert isinstance(vectors, list)
        if vectors:  # Pode estar vazio em alguns casos
            assert all(isinstance(v, np.ndarray) for v in vectors)
            assert all(len(v) == 768 for v in vectors)
    
    def test_calculate_centroid_empty(self, calculator):
        """Testa cálculo de centroide com lista vazia"""
        result = calculator.calculate_centroid([])
        assert result is None
    
    def test_calculate_centroid_valid(self, calculator, sample_vectors):
        """Testa cálculo de centroide válido"""
        result = calculator.calculate_centroid(sample_vectors)
        
        assert result is not None
        assert len(result) == 768
        assert np.allclose(np.linalg.norm(result), 1.0)  # Deve estar normalizado
    
    def test_store_centroid(self, calculator, mock_redis, sample_vectors):
        """Testa armazenamento de centroide"""
        with patch.object(calculator, 'redis_client', mock_redis):
            centroid = calculator.calculate_centroid(sample_vectors)
            success = calculator.store_centroid("tenant1", "tag1", centroid)
            
            assert success is True
            assert mock_redis.setex.call_count == 2  # Centroide + metadados
    
    @pytest.mark.asyncio
    async def test_calculate_and_store_centroids(self, calculator, mock_redis):
        """Testa cálculo e armazenamento completo"""
        with patch.object(calculator, 'redis_client', mock_redis):
            with patch.object(calculator, 'get_vectors_for_tag', return_value=[np.random.rand(768)]):
                results = await calculator.calculate_and_store_centroids("tenant1")
                
                assert isinstance(results, dict)
                assert len(results) > 0
                # Pelo menos algumas tags devem ter sido processadas
                assert any(results.values())


class TestRagBridge:
    """Testes para a classe RagBridge"""
    
    @pytest.fixture
    def rag_bridge(self):
        """Fixture para criar um RagBridge"""
        return RagBridge()
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock do serviço de embeddings"""
        mock = AsyncMock()
        mock.embed_query.return_value = np.random.rand(768).tolist()
        return mock
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock do cliente Qdrant"""
        mock = AsyncMock()
        mock.search.return_value = []
        return mock
    
    @pytest.mark.asyncio
    async def test_get_query_embedding(self, rag_bridge, mock_embedding_service):
        """Testa geração de embedding"""
        with patch.object(rag_bridge, 'embedding_service', mock_embedding_service):
            result = await rag_bridge.get_query_embedding("test query")
            
            assert isinstance(result, np.ndarray)
            assert len(result) == 768
            assert np.allclose(np.linalg.norm(result), 1.0)
    
    @pytest.mark.asyncio
    async def test_semantic_search(self, rag_bridge, mock_qdrant_client):
        """Testa busca semântica"""
        with patch.object(rag_bridge, 'qdrant_client', mock_qdrant_client):
            mock_qdrant_client.search.return_value = []
            
            query_vector = np.random.rand(768)
            results = await rag_bridge.semantic_search(query_vector, "tenant1")
            
            assert isinstance(results, list)
            mock_qdrant_client.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_lexical_search(self, rag_bridge):
        """Testa busca lexical"""
        results = await rag_bridge.lexical_search("test query", "tenant1")
        
        assert isinstance(results, list)
        for result in results:
            assert "id" in result
            assert "score" in result
            assert "lexical_rank" in result
    
    def test_reciprocal_rank_fusion(self, rag_bridge):
        """Testa fusão RRF"""
        semantic_results = [
            {"id": "doc1", "score": 0.9, "semantic_rank": 1},
            {"id": "doc2", "score": 0.8, "semantic_rank": 2}
        ]
        
        lexical_results = [
            {"id": "doc2", "score": 0.95, "lexical_rank": 1},
            {"id": "doc3", "score": 0.7, "lexical_rank": 2}
        ]
        
        results = rag_bridge.reciprocal_rank_fusion(semantic_results, lexical_results)
        
        assert isinstance(results, list)
        assert len(results) == 3  # doc1, doc2, doc3
        
        # Verificar se doc2 tem pontuação RRF maior (aparece em ambas as listas)
        doc2_result = next(r for r in results if r["id"] == "doc2")
        assert "rrf_score" in doc2_result
        assert len(doc2_result["rank_sources"]) == 2
    
    @pytest.mark.asyncio
    async def test_federated_search(self, rag_bridge):
        """Testa busca federada completa"""
        with patch.object(rag_bridge, 'get_query_embedding', return_value=np.random.rand(768)):
            with patch.object(rag_bridge, 'semantic_search', return_value=[]):
                with patch.object(rag_bridge, 'lexical_search', return_value=[]):
                    results = await rag_bridge.federated_search("test query", "tenant1")
                    
                    assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_federated_search_with_personalization(self, rag_bridge):
        """Testa busca federada com personalização"""
        with patch.object(rag_bridge, 'get_query_embedding', return_value=np.random.rand(768)):
            with patch.object(rag_bridge, 'semantic_search', return_value=[]):
                with patch.object(rag_bridge, 'lexical_search', return_value=[]):
                    with patch('app.core.rag_bridge.personalize_query_vector', return_value=np.random.rand(768)):
                        results = await rag_bridge.federated_search(
                            "test query", 
                            "tenant1",
                            enable_personalization=True
                        )
                        
                        assert isinstance(results, list)


class TestIntegration:
    """Testes de integração"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_personalization(self):
        """Teste end-to-end do sistema de personalização"""
        # Criar instâncias
        calculator = CentroidCalculator()
        personalizer = CentroidPersonalizer()
        
        # Mock Redis
        mock_redis = Mock()
        centroid_data = np.random.rand(768).astype(np.float32).tobytes()
        mock_redis.get.return_value = centroid_data
        
        with patch.object(personalizer, 'redis_client', mock_redis):
            # Testar personalização
            query_vector = np.random.rand(768)
            query_vector = query_vector / np.linalg.norm(query_vector)
            
            result = await personalizer.apply_personalization(
                query_vector=query_vector,
                tenant_id="tenant1",
                query="test query",
                alpha=0.3
            )
            
            # Verificar resultado
            assert result is not None
            assert len(result) == 768
            assert np.allclose(np.linalg.norm(result), 1.0)
            
            # Verificar que houve modificação
            similarity = np.dot(query_vector, result)
            assert similarity < 1.0  # Deve ter sido modificado
    
    @pytest.mark.asyncio
    async def test_convenience_function(self):
        """Testa função de conveniência"""
        with patch('app.core.personalization.get_personalizer') as mock_get:
            mock_personalizer = Mock()
            mock_personalizer.apply_personalization = AsyncMock(return_value=np.random.rand(768))
            mock_get.return_value = mock_personalizer
            
            result = await personalize_query_vector(
                query_vector=np.random.rand(768),
                tenant_id="tenant1",
                query="test"
            )
            
            assert result is not None
            assert len(result) == 768


# Fixtures globais para pytest
@pytest.fixture(scope="session")
def event_loop():
    """Cria um loop de eventos para testes assíncronos"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def setup_logging():
    """Configura logging para testes"""
    import logging
    logging.basicConfig(level=logging.INFO)


# Configuração de teste
pytest_plugins = ["pytest_asyncio"]

# Marcadores personalizados
pytestmark = pytest.mark.asyncio
