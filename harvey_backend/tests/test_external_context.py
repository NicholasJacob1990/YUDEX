"""
Testes para o sistema de contexto externo
Valida processamento de documentos externos, integração com RAG e API
"""

import pytest
import asyncio
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from app.models.schema_api import (
    ExternalDoc, 
    ExternalDocProcessor, 
    ExternalDocValidationResult,
    GenerationRequest,
    GenerationResponse
)
from app.core.rag_bridge import RagBridge
from app.orch.rag_node import rag_node, context_validator_node
from app.orch.harvey_workflow import HarveyToolsWorkflow


class TestExternalDocProcessor:
    """Testes para o processador de documentos externos"""
    
    def test_validate_docs_success(self):
        """Testa validação bem-sucedida de documentos externos"""
        docs = [
            ExternalDoc(
                src_id="doc1",
                text="Texto do documento 1 com conteúdo relevante para análise jurídica.",
                meta={"tipo": "contrato", "data": "2024-01-15"}
            ),
            ExternalDoc(
                src_id="doc2",
                text="Documento 2 com informações adicionais sobre o caso em questão.",
                meta={"tipo": "parecer", "autor": "Advogado X"}
            )
        ]
        
        result = ExternalDocProcessor.validate_docs(docs)
        
        assert result.valid is True
        assert result.total_docs == 2
        assert result.total_characters > 0
        assert result.estimated_tokens > 0
        assert result.max_doc_length > 0
        assert len(result.validation_errors) == 0
    
    def test_validate_docs_empty(self):
        """Testa validação com lista vazia"""
        docs = []
        
        result = ExternalDocProcessor.validate_docs(docs)
        
        assert result.valid is False
        assert "Nenhum documento fornecido" in result.validation_errors
    
    def test_validate_docs_too_large(self):
        """Testa validação com documentos muito grandes"""
        large_text = "x" * 1000000  # 1MB de texto
        docs = [
            ExternalDoc(
                src_id="large_doc",
                text=large_text,
                meta={"tipo": "contrato"}
            )
        ]
        
        result = ExternalDocProcessor.validate_docs(docs)
        
        assert result.valid is False
        assert any("muito grande" in error for error in result.validation_errors)
    
    def test_validate_docs_duplicate_ids(self):
        """Testa validação com IDs duplicados"""
        docs = [
            ExternalDoc(
                src_id="doc1",
                text="Primeiro documento",
                meta={"tipo": "contrato"}
            ),
            ExternalDoc(
                src_id="doc1",  # ID duplicado
                text="Segundo documento",
                meta={"tipo": "parecer"}
            )
        ]
        
        result = ExternalDocProcessor.validate_docs(docs)
        
        assert result.valid is False
        assert any("duplicado" in error for error in result.validation_errors)
    
    def test_prepare_for_rag(self):
        """Testa preparação de documentos para RAG"""
        docs = [
            ExternalDoc(
                src_id="doc1",
                text="Este é um documento longo que precisa ser dividido em chunks menores para processamento eficiente no sistema RAG. " * 10,
                meta={"tipo": "contrato", "data": "2024-01-15"}
            )
        ]
        
        processed = ExternalDocProcessor.prepare_for_rag(docs)
        
        assert len(processed) == 1
        assert processed[0]["src_id"] == "doc1"
        assert processed[0]["source"] == "external"
        assert "chunks" in processed[0]
        assert "metadata" in processed[0]
        assert "estimated_tokens" in processed[0]
        assert len(processed[0]["chunks"]) > 0
    
    def test_chunk_text(self):
        """Testa divisão de texto em chunks"""
        text = "Parágrafo 1 com informações importantes.\n\nParágrafo 2 com mais detalhes.\n\nParágrafo 3 com conclusões."
        
        chunks = ExternalDocProcessor._chunk_text(text)
        
        assert len(chunks) > 0
        assert all(len(chunk) <= 1000 for chunk in chunks)
        assert all(len(chunk.strip()) > 0 for chunk in chunks)


class TestRagBridge:
    """Testes para o RAG Bridge com contexto externo"""
    
    @pytest.fixture
    def mock_rag_bridge(self):
        """Fixture para mock do RAG Bridge"""
        bridge = Mock(spec=RagBridge)
        bridge.federated_search = AsyncMock()
        return bridge
    
    @pytest.mark.asyncio
    async def test_federated_search_with_external_docs(self, mock_rag_bridge):
        """Testa busca federada com documentos externos"""
        external_docs = [
            {
                "src_id": "external_1",
                "source": "external",
                "chunks": [
                    {"text": "Conteúdo relevante para busca", "start": 0, "end": 100}
                ],
                "metadata": {"tipo": "contrato"},
                "estimated_tokens": 25
            }
        ]
        
        # Mock do resultado da busca
        mock_result = [
            {
                "src_id": "internal_1",
                "source": "internal",
                "score": 0.9,
                "text": "Documento interno relevante",
                "final_rank": 1
            },
            {
                "src_id": "external_1",
                "source": "external",
                "score": 0.8,
                "text": "Conteúdo relevante para busca",
                "final_rank": 2
            }
        ]
        
        mock_rag_bridge.federated_search.return_value = mock_result
        
        # Executar busca
        result = await mock_rag_bridge.federated_search(
            query="busca teste",
            tenant_id="test_tenant",
            k_total=10,
            external_docs=external_docs,
            use_internal_rag=True
        )
        
        # Verificar resultado
        assert len(result) == 2
        assert result[0]["source"] == "internal"
        assert result[1]["source"] == "external"
        
        # Verificar chamada do mock
        mock_rag_bridge.federated_search.assert_called_once_with(
            query="busca teste",
            tenant_id="test_tenant",
            k_total=10,
            external_docs=external_docs,
            use_internal_rag=True
        )


class TestRagNode:
    """Testes para o nó RAG com contexto externo"""
    
    @pytest.mark.asyncio
    async def test_rag_node_with_external_context(self):
        """Testa nó RAG com contexto externo"""
        external_docs = [
            ExternalDoc(
                src_id="test_doc",
                text="Documento de teste para validação",
                meta={"tipo": "teste"}
            )
        ]
        
        state = {
            "initial_query": "teste de busca",
            "tenant_id": "test_tenant",
            "config": {
                "context_docs_external": external_docs,
                "use_internal_rag": True,
                "rag_config": {
                    "k_total": 10,
                    "enable_personalization": True
                }
            }
        }
        
        # Mock do RAG Bridge
        with patch('app.orch.rag_node.get_rag_bridge') as mock_get_bridge:
            mock_bridge = Mock()
            mock_bridge.federated_search = AsyncMock(return_value=[
                {
                    "src_id": "test_doc",
                    "source": "external",
                    "score": 0.8,
                    "text": "Documento de teste",
                    "final_rank": 1
                }
            ])
            mock_get_bridge.return_value = mock_bridge
            
            # Executar nó
            result = await rag_node(state)
            
            # Verificar resultado
            assert "rag_docs" in result
            assert len(result["rag_docs"]) == 1
            assert result["rag_docs"][0]["source"] == "external"
            assert "context_metadata" in result
            assert "external_docs_used" in result
            assert len(result["external_docs_used"]) == 1
    
    @pytest.mark.asyncio
    async def test_context_validator_node(self):
        """Testa nó validador de contexto"""
        external_docs = [
            ExternalDoc(
                src_id="valid_doc",
                text="Documento válido para teste",
                meta={"tipo": "teste"}
            )
        ]
        
        state = {
            "config": {
                "context_docs_external": external_docs
            }
        }
        
        # Mock do processador
        with patch('app.orch.rag_node.ExternalDocProcessor') as mock_processor:
            mock_validation = ExternalDocValidationResult(
                valid=True,
                total_docs=1,
                total_characters=100,
                estimated_tokens=25,
                max_doc_length=100,
                validation_errors=[]
            )
            mock_processor.validate_docs.return_value = mock_validation
            
            # Executar nó
            result = await context_validator_node(state)
            
            # Verificar resultado
            assert "validation_result" in result
            assert result["validation_result"]["valid"] is True
            assert "supervisor_notes" in result
            assert len(result["supervisor_notes"]) > 0


class TestHarveyWorkflow:
    """Testes para o workflow com contexto externo"""
    
    @pytest.fixture
    def workflow(self):
        """Fixture para o workflow"""
        return HarveyToolsWorkflow()
    
    @pytest.mark.asyncio
    async def test_workflow_with_external_context(self, workflow):
        """Testa workflow completo com contexto externo"""
        external_docs = [
            ExternalDoc(
                src_id="contract_001",
                text="Contrato de prestação de serviços com cláusulas específicas sobre responsabilidade.",
                meta={"tipo": "contrato", "data": "2024-01-15"}
            )
        ]
        
        # Mock dos componentes necessários
        with patch('app.orch.harvey_workflow.context_validator_node') as mock_validator, \
             patch('app.orch.harvey_workflow.rag_node') as mock_rag, \
             patch.object(workflow.registry, 'execute_tool') as mock_execute:
            
            # Mock do validador
            mock_validator.return_value = {
                "validation_result": {
                    "valid": True,
                    "total_docs": 1,
                    "validation_errors": []
                }
            }
            
            # Mock do RAG
            mock_rag.return_value = {
                "rag_docs": [
                    {
                        "src_id": "contract_001",
                        "source": "external",
                        "score": 0.85,
                        "text": "Contrato de prestação de serviços",
                        "final_rank": 1
                    }
                ],
                "context_metadata": {
                    "total_documents": 1,
                    "external_documents": 1,
                    "internal_documents": 0
                },
                "external_docs_used": [
                    {
                        "src_id": "contract_001",
                        "score": 0.85,
                        "rank": 1
                    }
                ],
                "supervisor_notes": ["Contexto externo processado com sucesso"]
            }
            
            # Mock das ferramentas
            mock_execute.return_value = Mock(success=True, data=[])
            
            # Executar workflow
            result = await workflow.process_request(
                "Analisar responsabilidade contratual",
                external_docs=external_docs
            )
            
            # Verificar resultado
            assert "content" in result
            assert "external_context_summary" in result
            assert "external_docs_used" in result
            assert "context_metadata" in result
            assert result["metadata"]["external_docs_provided"] == 1


class TestGenerationRequestResponse:
    """Testes para os schemas de requisição e resposta"""
    
    def test_generation_request_with_external_docs(self):
        """Testa criação de requisição com documentos externos"""
        external_docs = [
            ExternalDoc(
                src_id="doc1",
                text="Texto do documento",
                meta={"tipo": "contrato"}
            )
        ]
        
        request = GenerationRequest(
            query="Analisar contrato",
            context_docs_external=external_docs,
            use_internal_rag=True,
            k_total=15,
            enable_personalization=True,
            doc_type="parecer"
        )
        
        assert request.query == "Analisar contrato"
        assert len(request.context_docs_external) == 1
        assert request.context_docs_external[0].src_id == "doc1"
        assert request.use_internal_rag is True
        assert request.k_total == 15
    
    def test_generation_response_with_external_context(self):
        """Testa criação de resposta com contexto externo"""
        external_docs_used = [
            {
                "src_id": "doc1",
                "score": 0.85,
                "rank": 1,
                "text_overlap": 0.3
            }
        ]
        
        context_summary = {
            "context_type": "hybrid",
            "total_documents": 10,
            "external_documents": 1,
            "internal_documents": 9
        }
        
        response = GenerationResponse(
            run_id="test_run",
            query="Analisar contrato",
            doc_type="parecer",
            generated_text="Texto gerado",
            context_summary=context_summary,
            external_docs_used=external_docs_used,
            execution_time=2.5
        )
        
        assert response.run_id == "test_run"
        assert response.context_summary["context_type"] == "hybrid"
        assert len(response.external_docs_used) == 1
        assert response.external_docs_used[0]["src_id"] == "doc1"
        assert response.execution_time == 2.5


# Função para executar testes específicos
async def run_integration_tests():
    """Executa testes de integração do sistema completo"""
    print("🧪 Executando testes de integração...")
    
    # Teste 1: Validação de documentos
    print("\n1. Testando validação de documentos...")
    docs = [
        ExternalDoc(
            src_id="integration_test_1",
            text="Documento de teste para integração do sistema de contexto externo.",
            meta={"tipo": "teste", "origem": "integração"}
        )
    ]
    
    validation = ExternalDocProcessor.validate_docs(docs)
    print(f"   Validação: {'✅' if validation.valid else '❌'}")
    print(f"   Total docs: {validation.total_docs}")
    print(f"   Total chars: {validation.total_characters}")
    
    # Teste 2: Preparação para RAG
    print("\n2. Testando preparação para RAG...")
    processed = ExternalDocProcessor.prepare_for_rag(docs)
    print(f"   Documentos processados: {len(processed)}")
    print(f"   Chunks gerados: {len(processed[0]['chunks'])}")
    
    # Teste 3: Workflow completo (simulado)
    print("\n3. Testando workflow completo...")
    workflow = HarveyToolsWorkflow()
    
    # Mock simples para teste
    with patch('app.orch.harvey_workflow.context_validator_node') as mock_validator, \
         patch('app.orch.harvey_workflow.rag_node') as mock_rag:
        
        mock_validator.return_value = {"validation_result": {"valid": True}}
        mock_rag.return_value = {
            "rag_docs": [],
            "context_metadata": {},
            "external_docs_used": [],
            "supervisor_notes": []
        }
        
        try:
            result = await workflow.process_request(
                "Teste de integração",
                external_docs=docs
            )
            print(f"   Resultado: {'✅' if result else '❌'}")
            print(f"   Metadados: {result.get('metadata', {})}")
        except Exception as e:
            print(f"   Erro: {e}")
    
    print("\n🎯 Testes de integração concluídos!")


if __name__ == "__main__":
    # Executar testes básicos
    print("🧪 Executando testes básicos...")
    
    processor_tests = TestExternalDocProcessor()
    processor_tests.test_validate_docs_success()
    processor_tests.test_prepare_for_rag()
    print("✅ Testes do processador concluídos")
    
    # Executar testes de integração
    asyncio.run(run_integration_tests())
