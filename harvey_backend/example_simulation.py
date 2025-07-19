"""
Exemplo de uso do sistema Harvey - Versão Funcional
Demonstra como usar o sistema com LangGraph
"""

from typing import Any, Dict, List, Optional, TypedDict
# Importação simplificada para evitar problemas
from app.orch.supervisor import supervisor_router

# Importação direta das funções de agente
from app.orch.agents import analyzer_node, drafter_node, critic_node, formatter_node

# Estado simplificado para LangGraph
class LangGraphState(TypedDict, total=False):
    """Estado para LangGraph"""
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
    next_node_to_call: Optional[str]
    supervisor_notes: List[str]
    metrics: Dict[str, Any]

def create_initial_state() -> LangGraphState:
    """Cria estado inicial para teste"""
    return LangGraphState(
        run_id="test_001",
        tenant_id="advocacia_teste",
        initial_query="Redija um parecer sobre limite de 25% em contratos administrativos",
        task="document_draft",
        doc_type="parecer",
        config={
            "model": "gpt-4",
            "format": "abnt",
            "urgency": "normal"
        },
        rag_docs=[
            {
                "source": "Lei 8.666/93",
                "content": "Art. 65. Os contratos regidos por esta Lei poderão ser alterados...",
                "relevance": 0.9
            },
            {
                "source": "Jurisprudência TCU",
                "content": "O limite de 25% constitui regra geral...",
                "relevance": 0.8
            }
        ],
        analysis=None,
        draft_markdown=None,
        critic_reports=[],
        critic_latest_markdown=None,
        final_text=None,
        next_node_to_call=None,
        supervisor_notes=[],
        metrics={}
    )

async def simulate_execution():
    """Simula execução do grafo"""
    
    print("🚀 Simulando execução do Harvey Backend...")
    print("=" * 50)
    
    # Estado inicial
    state = create_initial_state()
    
    print(f"📊 Estado inicial:")
    print(f"  - Run ID: {state['run_id']}")
    print(f"  - Query: {state['initial_query']}")
    print(f"  - Documentos RAG: {len(state.get('rag_docs', []))}")
    print(f"  - Task: {state['task']}")
    
    # Simula execução sequencial
    max_iterations = 5
    current_iteration = 0
    
    while current_iteration < max_iterations:
        print(f"\n🔄 Iteração {current_iteration + 1}/{max_iterations}")
        print("-" * 30)
        
        # Supervisor decide próximo passo
        next_node = supervisor_router(state)
        
        if next_node == "end":
            print("✅ Execução finalizada pelo supervisor")
            break
            
        # Executa o nó apropriado
        if next_node == "analyzer":
            print("🔍 Executando Analyzer...")
            result = await analyzer_node(state)
            state.update(result)
            
        elif next_node == "drafter":
            print("✍️ Executando Drafter...")
            result = await drafter_node(state)
            state.update(result)
            
        elif next_node == "critic":
            print("🔍 Executando Critic...")
            result = await critic_node(state)
            state.update(result)
            
        elif next_node == "formatter":
            print("🎨 Executando Formatter...")
            result = await formatter_node(state)
            state.update(result)
            
        # Mostra resultado da iteração
        print(f"📝 Notas do supervisor: {state.get('supervisor_notes', [])[-1] if state.get('supervisor_notes') else 'Nenhuma'}")
        
        current_iteration += 1
        
        # Verifica se tem resultado final
        if state.get('final_text'):
            print("✅ Documento final gerado!")
            break
    
    print(f"\n{'=' * 50}")
    print("📋 RESULTADO FINAL")
    print("=" * 50)
    
    # Mostra resultado final
    if state.get('final_text'):
        print("📄 Documento gerado:")
        print(state['final_text'])
    else:
        print("❌ Nenhum documento final gerado")
    
    # Mostra análise
    if state.get('analysis'):
        print(f"\n🔍 Análise:")
        for key, value in state['analysis'].items():
            print(f"  - {key}: {value}")
    
    # Mostra críticas
    if state.get('critic_reports'):
        print(f"\n📝 Relatórios de crítica:")
        for i, report in enumerate(state['critic_reports'], 1):
            print(f"  {i}. {report}")
    
    # Mostra notas do supervisor
    if state.get('supervisor_notes'):
        print(f"\n📋 Notas do supervisor:")
        for i, note in enumerate(state['supervisor_notes'], 1):
            print(f"  {i}. {note}")
    
    print(f"\n✅ Simulação concluída após {current_iteration} iterações")
    return state

def simulate_api_request():
    """Simula uma requisição de API"""
    
    print("📡 Simulando requisição API:")
    print("=" * 30)
    
    api_request = {
        "method": "POST",
        "endpoint": "/v1/generate/dynamic",
        "payload": {
            "run_id": "session_123",
            "query": "Redija um parecer sobre limite de 25% em contratos administrativos",
            "task": "document_draft",
            "doc_type": "parecer",
            "config": {
                "model": "gpt-4",
                "format": "abnt"
            },
            "docs": [
                {
                    "source": "Lei 8.666/93",
                    "content": "Art. 65. Os contratos regidos por esta Lei poderão ser alterados...",
                    "relevance": 0.9
                }
            ]
        }
    }
    
    print(f"🔗 {api_request['method']} {api_request['endpoint']}")
    print(f"📦 Payload: {api_request['payload']['query']}")
    print(f"📚 Documentos: {len(api_request['payload']['docs'])}")
    
    return api_request

if __name__ == "__main__":
    import asyncio
    
    print("🎯 HARVEY BACKEND - EXEMPLO DE USO")
    print("=" * 50)
    
    # Simula requisição API
    api_request = simulate_api_request()
    
    print("\n" + "=" * 50)
    print("🚀 EXECUÇÃO DO GRAFO")
    print("=" * 50)
    
    # Executa simulação
    asyncio.run(simulate_execution())
