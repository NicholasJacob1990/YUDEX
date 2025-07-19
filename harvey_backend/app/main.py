"""
Harvey Backend - FastAPI Main Application com LangGraph
Sistema RAG jurídico com orquestração dinâmica de agentes
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
import uvicorn
from typing import Dict, Any
import uuid

# Importações locais
from app.orch.state import GraphState
from app.orch.agents import analyzer_node, drafter_node, critic_node, formatter_node, researcher_node
from app.orch.supervisor import supervisor_router, get_execution_summary
from app.security.auth import get_api_identity
from app.api.v1 import feedback as feedback_router
from app.api.centroids import router as centroids_router
from app.core.audit import build_and_save_audit_record

# Variáveis globais
workflow = None
graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle da aplicação"""
    global workflow, graph
    
    # Startup
    print("🚀 Iniciando Harvey Backend com LangGraph...")
    
    # --- Construção do Grafo LangGraph ---
    workflow = StateGraph(GraphState)
    
    # Adicionar os nós (agentes)
    workflow.add_node("analyzer", analyzer_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("drafter", drafter_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("formatter", formatter_node)
    
    # O ponto de entrada usa o supervisor para decidir o primeiro nó
    workflow.add_conditional_edges(
        START,
        supervisor_router,
        {
            "analyzer": "analyzer",
            "researcher": "researcher",
            "drafter": "drafter",
            "critic": "critic",
            "formatter": "formatter",
            "end": END
        }
    )
    
    # Após cada nó, volta ao supervisor para decidir o próximo passo
    workflow.add_conditional_edges(
        "analyzer",
        supervisor_router,
        {
            "analyzer": "analyzer",
            "researcher": "researcher",
            "drafter": "drafter",
            "critic": "critic",
            "formatter": "formatter",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "researcher",
        supervisor_router,
        {
            "analyzer": "analyzer",
            "researcher": "researcher",
            "drafter": "drafter",
            "critic": "critic",
            "formatter": "formatter",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "drafter",
        supervisor_router,
        {
            "analyzer": "analyzer",
            "researcher": "researcher",
            "drafter": "drafter",
            "critic": "critic",
            "formatter": "formatter",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "critic",
        supervisor_router,
        {
            "analyzer": "analyzer",
            "researcher": "researcher",
            "drafter": "drafter",
            "critic": "critic",
            "formatter": "formatter",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "formatter",
        supervisor_router,
        {
            "analyzer": "analyzer",
            "researcher": "researcher",
            "drafter": "drafter",
            "critic": "critic",
            "formatter": "formatter",
            "end": END
        }
    )
    
    # Compilar o grafo com checkpointer de memória
    memory_saver = MemorySaver()
    graph = workflow.compile(checkpointer=memory_saver)
    
    print("✅ Harvey Backend com LangGraph inicializado!")
    
    yield
    
    # Shutdown
    print("🛑 Encerrando Harvey Backend...")

# Cria aplicação FastAPI
app = FastAPI(
    title="Harvey Backend",
    description="Sistema RAG jurídico com orquestração dinâmica usando LangGraph",
    version="1.0.0",
    lifespan=lifespan
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configurar adequadamente em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão dos routers da API
app.include_router(feedback_router.router, prefix="/api/v1")

# Rotas de status
@app.get("/")
async def root():
    """Rota raiz - status da aplicação"""
    return {
        "service": "Harvey Backend",
        "version": "1.0.0",
        "status": "running",
        "description": "Sistema RAG jurídico com orquestração dinâmica (LangGraph)",
        "graph_compiled": graph is not None
    }

@app.get("/health")
async def health_check():
    """Health check da aplicação"""
    return {
        "status": "healthy",
        "graph_ready": graph is not None,
        "workflow_nodes": len(workflow.nodes) if workflow else 0
    }

# Rota principal - execução do grafo dinâmico
@app.post("/v1/generate/dynamic")
async def generate_document_dynamic(
    payload: Dict[str, Any], 
    identity: Dict[str, Any] = Depends(get_api_identity)
):
    """
    Endpoint que executa o pipeline dinâmico usando LangGraph.
    
    Exemplo de payload:
    {
        "query": "Redija um parecer sobre limites de contratos administrativos",
        "task": "draft",
        "doc_type": "parecer",
        "docs": [{"content": "...", "source": "Lei 8.666/93"}],
        "config": {"complexity": "medium"}
    }
    """
    
    if not graph:
        raise HTTPException(status_code=500, detail="Grafo não inicializado")
    
    try:
        # Gerar ID único para a execução
        run_id = payload.get("run_id", str(uuid.uuid4()))
        thread_config = {"configurable": {"thread_id": run_id}}
        
        # Criar estado inicial
        initial_state = GraphState(
            run_id=run_id,
            tenant_id=identity["tenant_id"],
            initial_query=payload.get("query", ""),
            task=payload.get("task", "draft"),
            doc_type=payload.get("doc_type", "documento"),
            rag_docs=payload.get("docs", []),
            config=payload.get("config", {}),
            supervisor_notes=[],
            metrics={}
        )
        
        # Executar o grafo
        final_state = None
        execution_log = []
        
        async for event in graph.astream(initial_state, config=thread_config):
            # Streaming de eventos para monitoramento
            for node_name, output in event.items():
                print(f"--- Nó executado: {node_name} ---")
                print(f"Estado parcial: {list(output.keys())}")
                
                execution_log.append({
                    "node": node_name,
                    "output_keys": list(output.keys()),
                    "supervisor_notes": output.get("supervisor_notes", [])
                })
                
                final_state = output
                
        if not final_state:
            raise HTTPException(status_code=500, detail="Falha ao processar - estado final vazio")
        
        # Gerar resumo de execução
        execution_summary = get_execution_summary(final_state)
        
        return {
            "success": True,
            "run_id": run_id,
            "final_state": final_state,
            "execution_summary": execution_summary,
            "execution_log": execution_log,
            "final_document": final_state.get("final_text", final_state.get("critic_latest_markdown", final_state.get("draft_markdown")))
        }
        
    except Exception as e:
        print(f"Erro na execução do grafo: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na execução: {str(e)}")

# Rota para execução com streaming
@app.post("/v1/generate/stream")
async def generate_document_stream(
    payload: Dict[str, Any],
    identity: Dict[str, Any] = Depends(get_api_identity)
):
    """
    Endpoint para execução com streaming de eventos.
    Retorna os eventos conforme são processados.
    """
    
    if not graph:
        raise HTTPException(status_code=500, detail="Grafo não inicializado")
    
    # TODO: Implementar streaming real com Server-Sent Events
    # Por enquanto, retorna placeholder
    return {
        "message": "Streaming será implementado em versão futura",
        "alternative": "Use /v1/generate/dynamic para execução completa"
    }

# Rotas de debug/desenvolvimento
@app.get("/debug/graph")
async def debug_graph():
    """Informações sobre o grafo"""
    if not graph or not workflow:
        return {"error": "Grafo não inicializado"}
    
    return {
        "nodes": list(workflow.nodes.keys()),
        "edges": len(workflow.edges),
        "compiled": graph is not None,
        "state_schema": "GraphState (LangGraph TypedDict)"
    }

# Incluir routers
app.include_router(feedback_router.router)
app.include_router(centroids_router)

@app.get("/debug/supervisor")
async def debug_supervisor():
    """Testa o supervisor com estado mockado"""
    
    # Estado de teste
    test_state = GraphState(
        run_id="test_run",
        tenant_id="test_tenant",
        initial_query="Teste do supervisor",
        task="draft",
        doc_type="parecer",
        rag_docs=[],
        config={},
        supervisor_notes=[],
        metrics={}
    )
    
    # Testa roteamento
    next_node = supervisor_router(test_state)
    
    return {
        "test_state": dict(test_state),
        "supervisor_decision": next_node,
        "execution_summary": get_execution_summary(test_state)
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
