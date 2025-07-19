
"""
Exemplo Completo com LangGraph
Sistema Harvey usando LangGraph para orquestração real
"""

import asyncio
from typing import TypedDict, Dict, Any, List, Optional
from langgraph.graph import StateGraph, END

from app.orch.agents import analyzer_node, drafter_node, critic_node, formatter_node
from app.orch.supervisor import supervisor_router

# Estado TypedDict para LangGraph
class HarveyState(TypedDict):
    """Estado do sistema Harvey para LangGraph"""
    run_id: str
    tenant_id: str
    initial_query: str
    task: str
    doc_type: str
    config: Dict[str, Any]
    rag_docs: List[Dict[str, Any]]
    analysis: Optional[Dict[str, Any]]
    draft_markdown: Optional[str]
    critic_reports: List[Dict[str, Any]]
    critic_latest_markdown: Optional[str]
    final_text: Optional[str]
    supervisor_notes: List[str]
    metrics: Dict[str, Any]

# Adaptadores para converter entre GraphState e HarveyState
def convert_to_graph_state(state: HarveyState) -> Dict[str, Any]:
    """Converte HarveyState para formato GraphState"""
    return {
        "run_id": state.get("run_id", ""),
        "tenant_id": state.get("tenant_id", ""),
        "initial_query": state.get("initial_query", ""),
        "task": state.get("task", ""),
        "doc_type": state.get("doc_type", ""),
        "config": state.get("config", {}),
        "rag_docs": state.get("rag_docs", []),
        "analysis": state.get("analysis"),
        "draft_markdown": state.get("draft_markdown"),
        "critic_reports": state.get("critic_reports", []),
        "critic_latest_markdown": state.get("critic_latest_markdown"),
        "final_text": state.get("final_text"),
        "supervisor_notes": state.get("supervisor_notes", []),
        "metrics": state.get("metrics", {})
    }

def update_state_from_result(state: HarveyState, result: Dict[str, Any]) -> HarveyState:
    """Atualiza HarveyState com resultado do nó"""
    for key, value in result.items():
        if key in state:
            state[key] = value
    return state

# Nós adaptados para LangGraph
async def analyzer_node_wrapper(state: HarveyState) -> HarveyState:
    """Wrapper para analyzer_node"""
    graph_state = convert_to_graph_state(state)
    result = await analyzer_node(graph_state)
    return update_state_from_result(state, result)

async def drafter_node_wrapper(state: HarveyState) -> HarveyState:
    """Wrapper para drafter_node"""
    graph_state = convert_to_graph_state(state)
    result = await drafter_node(graph_state)
    return update_state_from_result(state, result)

async def critic_node_wrapper(state: HarveyState) -> HarveyState:
    """Wrapper para critic_node"""
    graph_state = convert_to_graph_state(state)
    result = await critic_node(graph_state)
    return update_state_from_result(state, result)

async def formatter_node_wrapper(state: HarveyState) -> HarveyState:
    """Wrapper para formatter_node"""
    graph_state = convert_to_graph_state(state)
    result = await formatter_node(graph_state)
    return update_state_from_result(state, result)

# Função de roteamento para LangGraph
def routing_function(state: HarveyState) -> str:
    """Determina o próximo nó baseado no estado"""
    graph_state = convert_to_graph_state(state)
    next_node = supervisor_router(graph_state)
    
    print(f"🎯 Supervisor decidiu: {next_node}")
    
    # Mapeia para nós LangGraph
    if next_node == "analyzer":
        return "analyzer_node"
    elif next_node == "drafter":
        return "drafter_node"
    elif next_node == "critic":
        return "critic_node"
    elif next_node == "formatter":
        return "formatter_node"
    else:
        return END

def create_harvey_graph():
    """Cria o grafo LangGraph do sistema Harvey"""
    
    # Cria o grafo
    graph = StateGraph(HarveyState)
    
    # Adiciona os nós
    graph.add_node("analyzer_node", analyzer_node_wrapper)
    graph.add_node("drafter_node", drafter_node_wrapper)
    graph.add_node("critic_node", critic_node_wrapper)
    graph.add_node("formatter_node", formatter_node_wrapper)
    
    # Define o ponto de entrada
    graph.set_entry_point("analyzer_node")
    
    # Adiciona arestas condicionais
    graph.add_conditional_edges(
        "analyzer_node",
        routing_function,
        {
            "drafter_node": "drafter_node",
            "critic_node": "critic_node",
            "formatter_node": "formatter_node",
            END: END
        }
    )
    
    graph.add_conditional_edges(
        "drafter_node",
        routing_function,
        {
            "analyzer_node": "analyzer_node",
            "critic_node": "critic_node",
            "formatter_node": "formatter_node",
            END: END
        }
    )
    
    graph.add_conditional_edges(
        "critic_node",
        routing_function,
        {
            "analyzer_node": "analyzer_node",
            "drafter_node": "drafter_node",
            "formatter_node": "formatter_node",
            END: END
        }
    )
    
    graph.add_conditional_edges(
        "formatter_node",
        routing_function,
        {
            "analyzer_node": "analyzer_node",
            "drafter_node": "drafter_node",
            "critic_node": "critic_node",
            END: END
        }
    )
    
    return graph

async def run_harvey_langgraph():
    """Executa o sistema Harvey com LangGraph"""
    print("🚀 Iniciando Harvey com LangGraph...")
    
    # Estado inicial
    initial_state: HarveyState = {
        "run_id": "lg-001",
        "tenant_id": "test-tenant",
        "initial_query": "Preciso de um parecer sobre limites de contratos administrativos",
        "task": "DOCUMENT_GENERATION",
        "doc_type": "LEGAL_OPINION",
        "config": {
            "debug": True,
            "max_iterations": 5,
            "model_provider": "openai"
        },
        "rag_docs": [
            {
                "id": "doc-001",
                "title": "Lei 8.666/93 - Contratos Administrativos",
                "content": "Art. 65 - Limite de 25% para aditivos contratuais",
                "similarity": 0.9
            },
            {
                "id": "doc-002", 
                "title": "Jurisprudência TCU",
                "content": "Precedentes sobre flexibilização de limites",
                "similarity": 0.8
            }
        ],
        "analysis": None,
        "draft_markdown": None,
        "critic_reports": [],
        "critic_latest_markdown": None,
        "final_text": None,
        "supervisor_notes": [],
        "metrics": {}
    }
    
    # Cria e compila o grafo
    graph = create_harvey_graph()
    app = graph.compile()
    
    print("📊 Estado inicial:")
    print(f"  - Run ID: {initial_state['run_id']}")
    print(f"  - Query: {initial_state['initial_query']}")
    print(f"  - Documentos RAG: {len(initial_state['rag_docs'])}")
    
    # Executa o grafo
    print("\n🔄 Executando grafo LangGraph...")
    final_state = None
    step_count = 0
    
    try:
        async for step in app.astream(initial_state):
            step_count += 1
            print(f"\n--- Passo {step_count} ---")
            
            for node_name, node_output in step.items():
                print(f"✅ Nó executado: {node_name}")
                if node_output.get("supervisor_notes"):
                    print(f"   📝 Notas: {node_output['supervisor_notes'][-1]}")
                
                final_state = node_output
                
                # Limita número de passos para evitar loop infinito
                if step_count >= 10:
                    print("⚠️  Limite de passos atingido")
                    break
                    
        print(f"\n{'='*50}")
        print("✅ EXECUÇÃO LANGGRAPH CONCLUÍDA!")
        print(f"{'='*50}")
        
        if final_state:
            print(f"\n📊 Métricas finais:")
            print(f"  - Passos executados: {step_count}")
            print(f"  - Notas do supervisor: {len(final_state.get('supervisor_notes', []))}")
            print(f"  - Relatórios de crítica: {len(final_state.get('critic_reports', []))}")
            
            if final_state.get('analysis'):
                print(f"\n🔍 Análise final:")
                for key, value in final_state['analysis'].items():
                    print(f"  - {key}: {value}")
            
            if final_state.get('final_text'):
                print(f"\n📄 Documento final:")
                print("-" * 30)
                final_text = final_state['final_text']
                print(final_text[:500] + "..." if len(final_text) > 500 else final_text)
            
            if final_state.get('supervisor_notes'):
                print(f"\n📝 Histórico completo:")
                for i, note in enumerate(final_state['supervisor_notes'], 1):
                    print(f"  {i}. {note}")
        
    except Exception as e:
        print(f"❌ Erro durante execução: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_harvey_langgraph())

import asyncio
from typing import TypedDict, Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langgraph.types import Send

from app.orch.agents import analyzer_node, drafter_node, critic_node, formatter_node
from app.orch.supervisor import supervisor_router

# Estado TypedDict para LangGraph
class HarveyState(TypedDict):
    """Estado do sistema Harvey para LangGraph"""
    run_id: str
    tenant_id: str
    initial_query: str
    task: str
    doc_type: str
    config: Dict[str, Any]
    rag_docs: List[Dict[str, Any]]
    analysis: Optional[Dict[str, Any]]
    draft_markdown: Optional[str]
    critic_reports: List[Dict[str, Any]]
    critic_latest_markdown: Optional[str]
    final_text: Optional[str]
    supervisor_notes: List[str]
    metrics: Dict[str, Any]

import asyncio
from typing import Dict, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# Importação dos agentes
from app.orch.agents import analyzer_node, drafter_node, critic_node, formatter_node

# Estado para LangGraph
class WorkflowState(TypedDict):
    run_id: str
    tenant_id: str
    initial_query: str
    task: str
    doc_type: str
    config: Dict[str, Any]
    rag_docs: list
    analysis: Dict[str, Any]
    draft_markdown: str
    critic_reports: list
    critic_latest_markdown: str
    final_text: str
    supervisor_notes: Annotated[list, add_messages]
    iteration_count: int

# Wrapper functions para compatibilidade com LangGraph
async def analyzer_wrapper(state: WorkflowState) -> Dict[str, Any]:
    """Wrapper do analyzer para LangGraph"""
    print(f"🔍 Executando Analyzer (Iteração {state.get('iteration_count', 0) + 1})")
    
    # Simula o GraphState
    mock_state = {
        "run_id": state.get("run_id", ""),
        "initial_query": state.get("initial_query", ""),
        "rag_docs": state.get("rag_docs", []),
        "supervisor_notes": state.get("supervisor_notes", [])
    }
    
    class MockGraphState:
        def get(self, key, default=None):
            return mock_state.get(key, default)
    
    result = await analyzer_node(MockGraphState())
    
    return {
        "analysis": result.get("analysis", {}),
        "supervisor_notes": result.get("supervisor_notes", []),
        "iteration_count": state.get("iteration_count", 0) + 1
    }

async def drafter_wrapper(state: WorkflowState) -> Dict[str, Any]:
    """Wrapper do drafter para LangGraph"""
    print(f"📝 Executando Drafter (Iteração {state.get('iteration_count', 0)})")
    
    mock_state = {
        "analysis": state.get("analysis", {}),
        "config": state.get("config", {}),
        "supervisor_notes": state.get("supervisor_notes", [])
    }
    
    class MockGraphState:
        def get(self, key, default=None):
            return mock_state.get(key, default)
    
    result = await drafter_node(MockGraphState())
    
    return {
        "draft_markdown": result.get("draft_markdown", ""),
        "supervisor_notes": result.get("supervisor_notes", []),
        "iteration_count": state.get("iteration_count", 0) + 1
    }

async def critic_wrapper(state: WorkflowState) -> Dict[str, Any]:
    """Wrapper do critic para LangGraph"""
    print(f"🔍 Executando Critic (Iteração {state.get('iteration_count', 0)})")
    
    mock_state = {
        "draft_markdown": state.get("draft_markdown", ""),
        "analysis": state.get("analysis", {}),
        "critic_reports": state.get("critic_reports", []),
        "supervisor_notes": state.get("supervisor_notes", [])
    }
    
    class MockGraphState:
        def get(self, key, default=None):
            return mock_state.get(key, default)
    
    result = await critic_node(MockGraphState())
    
    return {
        "critic_latest_markdown": result.get("critic_latest_markdown", ""),
        "critic_reports": result.get("critic_reports", []),
        "supervisor_notes": result.get("supervisor_notes", []),
        "iteration_count": state.get("iteration_count", 0) + 1
    }

async def formatter_wrapper(state: WorkflowState) -> Dict[str, Any]:
    """Wrapper do formatter para LangGraph"""
    print(f"📄 Executando Formatter (Iteração {state.get('iteration_count', 0)})")
    
    mock_state = {
        "critic_latest_markdown": state.get("critic_latest_markdown", ""),
        "draft_markdown": state.get("draft_markdown", ""),
        "supervisor_notes": state.get("supervisor_notes", [])
    }
    
    class MockGraphState:
        def get(self, key, default=None):
            return mock_state.get(key, default)
    
    result = await formatter_node(MockGraphState())
    
    return {
        "final_text": result.get("final_text", ""),
        "supervisor_notes": result.get("supervisor_notes", []),
        "iteration_count": state.get("iteration_count", 0) + 1
    }

def should_continue(state: WorkflowState) -> str:
    """Decide se deve continuar o workflow"""
    # Lógica simples: se temos texto final, termina
    if state.get("final_text"):
        return END
    
    # Se não temos análise, vai para analyzer
    if not state.get("analysis"):
        return "analyzer"
    
    # Se não temos draft, vai para drafter
    if not state.get("draft_markdown"):
        return "drafter"
    
    # Se não temos crítica, vai para critic
    if not state.get("critic_latest_markdown"):
        return "critic"
    
    # Senão, vai para formatter
    return "formatter"

def create_workflow() -> StateGraph:
    """Cria o workflow LangGraph"""
    workflow = StateGraph(WorkflowState)
    
    # Adiciona os nós
    workflow.add_node("analyzer", analyzer_wrapper)
    workflow.add_node("drafter", drafter_wrapper)
    workflow.add_node("critic", critic_wrapper)
    workflow.add_node("formatter", formatter_wrapper)
    
    # Define o ponto de entrada
    workflow.set_entry_point("analyzer")
    
    # Define as transições condicionais
    workflow.add_conditional_edges(
        "analyzer",
        should_continue,
        {
            "drafter": "drafter",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "drafter", 
        should_continue,
        {
            "critic": "critic",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "critic",
        should_continue,
        {
            "formatter": "formatter",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "formatter",
        should_continue,
        {
            END: END
        }
    )
    
    return workflow.compile()

async def run_langgraph_example():
    """Executa exemplo com LangGraph"""
    print("🚀 Executando exemplo completo com LangGraph...")
    
    # Cria o workflow
    app = create_workflow()
    
    # Estado inicial
    initial_state = WorkflowState(
        run_id="langgraph-demo-001",
        tenant_id="demo-tenant",
        initial_query="Preciso de uma petição inicial para ação de indenização por danos morais",
        task="DOCUMENT_GENERATION",
        doc_type="PETITION",
        config={
            "debug": True,
            "max_iterations": 10,
            "model_provider": "openai"
        },
        rag_docs=[
            {
                "id": "doc-001",
                "title": "Jurisprudência sobre danos morais",
                "content": "Caso similar: Indenização por danos morais...",
                "similarity": 0.85
            }
        ],
        analysis={},
        draft_markdown="",
        critic_reports=[],
        critic_latest_markdown="",
        final_text="",
        supervisor_notes=[],
        iteration_count=0
    )
    
    print(f"📋 Estado inicial:")
    print(f"  - Run ID: {initial_state['run_id']}")
    print(f"  - Query: {initial_state['initial_query']}")
    print(f"  - Task: {initial_state['task']}")
    
    # Executa o workflow
    print(f"\n🔄 Executando workflow...")
    
    try:
        result = await app.ainvoke(initial_state)
        
        print(f"\n" + "="*50)
        print(f"✅ WORKFLOW LANGGRAPH CONCLUÍDO!")
        print(f"="*50)
        
        print(f"\n📊 Métricas:")
        print(f"  - Iterações: {result.get('iteration_count', 0)}")
        print(f"  - Notas do supervisor: {len(result.get('supervisor_notes', []))}")
        print(f"  - Relatórios de crítica: {len(result.get('critic_reports', []))}")
        
        if result.get('analysis'):
            print(f"\n🔍 Análise:")
            for key, value in result['analysis'].items():
                print(f"  - {key}: {value}")
        
        if result.get('final_text'):
            print(f"\n📄 Documento Final (primeiros 400 caracteres):")
            print("-" * 40)
            final_text = result['final_text']
            print(final_text[:400] + "..." if len(final_text) > 400 else final_text)
        
        print(f"\n📝 Histórico do Supervisor:")
        for i, note in enumerate(result.get('supervisor_notes', []), 1):
            print(f"  {i}. {note}")
            
    except Exception as e:
        print(f"❌ Erro na execução do workflow: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_langgraph_example())
