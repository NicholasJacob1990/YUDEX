"""
Nó RAG dedicado para processamento de contexto externo
Integra com o sistema de orquestração LangGraph
"""

import asyncio
from typing import Dict, Any, List, Optional
import logging

from app.orch.state import GraphState
from app.core.rag_bridge import get_rag_bridge
from app.models.schema_api import ExternalDocProcessor

logger = logging.getLogger(__name__)

async def rag_node(state: GraphState) -> Dict[str, Any]:
    """
    Nó dedicado para a execução do RAG Bridge com suporte a contexto externo.
    Este nó substitui a lógica de busca que estava antes no analyzer.
    """
    logger.info("-> Entrando no nó: RAG Bridge")
    
    try:
        # Extrair informações do estado
        query = state.get("initial_query", "")
        tenant_id = state.get("tenant_id", "")
        config = state.get("config", {})
        
        if not query or not tenant_id:
            error_msg = "Query ou tenant_id não fornecidos"
            logger.error(error_msg)
            return {
                "error_messages": [error_msg],
                "supervisor_notes": [f"Erro no RAG: {error_msg}"]
            }
        
        # Extrair parâmetros de contexto externo
        external_docs = config.get("context_docs_external")
        use_internal_rag = config.get("use_internal_rag", True)
        rag_config = config.get("rag_config", {})
        
        # Parâmetros de busca
        k_total = rag_config.get("k_total", 20)
        enable_personalization = rag_config.get("enable_personalization", True)
        personalization_alpha = rag_config.get("personalization_alpha")
        
        # Processar documentos externos se fornecidos
        processed_external_docs = None
        if external_docs:
            try:
                # Converter para formato interno
                processed_external_docs = ExternalDocProcessor.prepare_for_rag(external_docs)
                logger.info(f"Processados {len(processed_external_docs)} documentos externos")
            except Exception as e:
                logger.error(f"Erro ao processar documentos externos: {e}")
                return {
                    "error_messages": [f"Erro ao processar documentos externos: {str(e)}"],
                    "supervisor_notes": [f"Erro no processamento de documentos externos: {str(e)}"]
                }
        
        # Executar busca federada
        rag_bridge = get_rag_bridge()
        
        start_time = asyncio.get_event_loop().time()
        
        rag_docs = await rag_bridge.federated_search(
            query=query,
            tenant_id=tenant_id,
            k_total=k_total,
            personalization_alpha=personalization_alpha,
            enable_personalization=enable_personalization,
            external_docs=processed_external_docs,
            use_internal_rag=use_internal_rag
        )
        
        end_time = asyncio.get_event_loop().time()
        execution_time = end_time - start_time
        
        # Preparar notas do supervisor
        notes = state.get("supervisor_notes", [])
        
        # Estatísticas da busca
        total_docs = len(rag_docs)
        internal_docs = len([d for d in rag_docs if d.get("source") != "external"])
        external_docs_found = len([d for d in rag_docs if d.get("source") == "external"])
        
        notes.append(f"RAG Bridge executado em {execution_time:.2f}s")
        notes.append(f"Total: {total_docs} documentos ({internal_docs} internos + {external_docs_found} externos)")
        
        if processed_external_docs:
            notes.append(f"Contexto externo: {len(processed_external_docs)} documentos fornecidos")
        
        if enable_personalization:
            notes.append(f"Personalização aplicada (α={personalization_alpha or 0.25})")
        
        # Adicionar metadados de contexto
        context_metadata = {
            "total_documents": total_docs,
            "internal_documents": internal_docs,
            "external_documents": external_docs_found,
            "use_internal_rag": use_internal_rag,
            "personalization_enabled": enable_personalization,
            "execution_time": execution_time
        }
        
        # Preparar lista de documentos externos usados para resposta
        external_docs_used = []
        if processed_external_docs:
            for doc in rag_docs:
                if doc.get("source") == "external":
                    external_docs_used.append({
                        "src_id": doc.get("src_id"),
                        "score": doc.get("score", 0),
                        "rank": doc.get("final_rank", 0),
                        "text_overlap": doc.get("text_overlap", 0)
                    })
        
        logger.info(f"RAG Bridge concluído: {total_docs} documentos recuperados")
        
        return {
            "rag_docs": rag_docs,
            "supervisor_notes": notes,
            "context_metadata": context_metadata,
            "external_docs_used": external_docs_used
        }
        
    except Exception as e:
        error_msg = f"Erro no RAG Bridge: {str(e)}"
        logger.error(error_msg)
        
        notes = state.get("supervisor_notes", [])
        notes.append(error_msg)
        
        return {
            "error_messages": [error_msg],
            "supervisor_notes": notes,
            "rag_docs": []
        }

async def context_validator_node(state: GraphState) -> Dict[str, Any]:
    """
    Nó opcional para validar contexto externo antes do processamento
    """
    logger.info("-> Entrando no nó: Context Validator")
    
    try:
        config = state.get("config", {})
        external_docs = config.get("context_docs_external")
        
        if not external_docs:
            # Sem documentos externos, prosseguir normalmente
            return {
                "supervisor_notes": ["Nenhum documento externo para validar"]
            }
        
        # Validar documentos externos
        validation_result = ExternalDocProcessor.validate_docs(external_docs)
        
        notes = state.get("supervisor_notes", [])
        
        if validation_result.valid:
            notes.append(f"Documentos externos validados: {validation_result.total_docs} docs, {validation_result.total_characters} chars")
            notes.append(f"Tokens estimados: {validation_result.estimated_tokens}")
            
            return {
                "supervisor_notes": notes,
                "validation_result": validation_result.dict()
            }
        else:
            # Documentos inválidos
            error_msg = f"Documentos externos inválidos: {validation_result.validation_errors}"
            logger.error(error_msg)
            
            notes.append(error_msg)
            
            return {
                "error_messages": [error_msg],
                "supervisor_notes": notes,
                "validation_result": validation_result.dict()
            }
            
    except Exception as e:
        error_msg = f"Erro na validação de contexto: {str(e)}"
        logger.error(error_msg)
        
        notes = state.get("supervisor_notes", [])
        notes.append(error_msg)
        
        return {
            "error_messages": [error_msg],
            "supervisor_notes": notes
        }

def should_validate_context(state: GraphState) -> str:
    """
    Função de roteamento para decidir se deve validar contexto externo
    """
    config = state.get("config", {})
    external_docs = config.get("context_docs_external")
    
    if external_docs and len(external_docs) > 0:
        return "context_validator"
    else:
        return "rag_bridge"

def get_context_summary(state: GraphState) -> Dict[str, Any]:
    """
    Gera resumo do contexto utilizado para incluir na resposta
    """
    try:
        context_metadata = state.get("context_metadata", {})
        external_docs_used = state.get("external_docs_used", [])
        config = state.get("config", {})
        
        summary = {
            "context_type": "hybrid" if context_metadata.get("use_internal_rag") and external_docs_used else 
                           "external_only" if external_docs_used else "internal_only",
            "total_documents": context_metadata.get("total_documents", 0),
            "internal_documents": context_metadata.get("internal_documents", 0),
            "external_documents": context_metadata.get("external_documents", 0),
            "personalization_enabled": context_metadata.get("personalization_enabled", False),
            "execution_time": context_metadata.get("execution_time", 0)
        }
        
        if external_docs_used:
            summary["external_docs_used"] = external_docs_used
            summary["external_docs_count"] = len(external_docs_used)
        
        return summary
        
    except Exception as e:
        logger.error(f"Erro ao gerar resumo de contexto: {e}")
        return {"error": str(e)}

# Exemplo de integração no grafo principal
def integrate_rag_nodes(workflow):
    """
    Integra os nós RAG no workflow principal
    
    Args:
        workflow: Instância do StateGraph
    """
    
    # Adicionar nós
    workflow.add_node("context_validator", context_validator_node)
    workflow.add_node("rag_bridge", rag_node)
    
    # Roteamento condicional do START
    workflow.add_conditional_edges(
        "START",
        should_validate_context,
        {
            "context_validator": "context_validator",
            "rag_bridge": "rag_bridge"
        }
    )
    
    # Se validação passou, ir para RAG
    workflow.add_edge("context_validator", "rag_bridge")
    
    # Após RAG, ir para analyzer
    workflow.add_edge("rag_bridge", "analyzer")

# Função auxiliar para testing
async def test_rag_with_external_context():
    """
    Testa o nó RAG com contexto externo
    """
    from app.models.schema_api import ExternalDoc
    
    # Criar estado de teste
    test_state = GraphState(
        run_id="test_external_context",
        tenant_id="cliente_teste",
        initial_query="Responsabilidade por vazamento de dados",
        task="draft",
        doc_type="parecer",
        config={
            "context_docs_external": [
                ExternalDoc(
                    src_id="incident_report",
                    text="Relatório de incidente: vazamento de 10.000 registros de usuários devido a falha de segurança no servidor.",
                    meta={"tipo": "incidente", "gravidade": "alta"}
                ),
                ExternalDoc(
                    src_id="policy_excerpt",
                    text="Política de privacidade: A empresa não se responsabiliza por ataques externos.",
                    meta={"tipo": "politica", "versao": "1.2"}
                )
            ],
            "use_internal_rag": True,
            "rag_config": {
                "k_total": 15,
                "enable_personalization": True
            }
        }
    )
    
    # Executar nó RAG
    result = await rag_node(test_state)
    
    print("Resultado do teste:")
    print(f"- Documentos recuperados: {len(result.get('rag_docs', []))}")
    print(f"- Contexto externo usado: {len(result.get('external_docs_used', []))}")
    print(f"- Notas do supervisor: {result.get('supervisor_notes', [])}")
    
    return result

if __name__ == "__main__":
    # Executar teste
    asyncio.run(test_rag_with_external_context())
