"""
Exemplo de uso do Harvey Backend com LangGraph
Teste básico da orquestração dinâmica
"""

import asyncio
import json
from app.orch.state import GraphState
from app.orch.agents import analyzer_node, drafter_node, critic_node, formatter_node
from app.orch.supervisor import supervisor_router, get_execution_summary

async def test_graph_execution():
    """
    Testa a execução do grafo sem LangGraph (simulação)
    """
    print("🧪 Testando execução do grafo Harvey Backend...")
    
    # Estado inicial
    state = GraphState(
        run_id="test_run_001",
        tenant_id="test_tenant",
        initial_query="Redija um parecer sobre limites de contratos administrativos",
        task="draft",
        doc_type="parecer",
        rag_docs=[
            {
                "content": "Lei 8.666/93 estabelece normas para licitações",
                "source": "Lei 8.666/93"
            },
            {
                "content": "Jurisprudência do TCU sobre limites contratuais",
                "source": "TCU Acórdão 1234/2024"
            }
        ],
        config={"complexity": "medium"},
        supervisor_notes=[],
        metrics={}
    )
    
    print(f"📋 Estado inicial: {state['initial_query']}")
    print(f"📚 Documentos RAG: {len(state['rag_docs'])} documentos")
    
    # Simula execução do grafo
    max_iterations = 10
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteração {iteration} ---")
        
        # Supervisor decide próximo nó
        next_node = supervisor_router(state)
        print(f"🎯 Supervisor decidiu: {next_node}")
        
        if next_node == "end":
            print("✅ Execução finalizada!")
            break
            
        # Executa o nó correspondente
        if next_node == "analyzer":
            result = await analyzer_node(state)
        elif next_node == "drafter":
            result = await drafter_node(state)
        elif next_node == "critic":
            result = await critic_node(state)
        elif next_node == "formatter":
            result = await formatter_node(state)
        else:
            print(f"❌ Nó desconhecido: {next_node}")
            break
            
        # Atualiza estado
        state.update(result)
        
        # Mostra progresso
        summary = get_execution_summary(state)
        print(f"📊 Progresso: {summary}")
        
        # Mostra notas do supervisor
        if state.get("supervisor_notes"):
            print(f"📝 Última nota: {state['supervisor_notes'][-1]}")
    
    print(f"\n🎉 Execução completa!")
    print(f"📄 Documento final disponível: {'final_text' in state}")
    
    if "final_text" in state:
        print(f"📝 Tamanho do documento: {len(state['final_text'])} caracteres")
        print(f"🔍 Primeiros 200 caracteres:")
        print(state["final_text"][:200] + "...")
    
    # Resumo final
    final_summary = get_execution_summary(state)
    print(f"\n📊 Resumo final:")
    print(json.dumps(final_summary, indent=2, ensure_ascii=False))
    
    return state

async def test_individual_nodes():
    """
    Testa cada nó individualmente
    """
    print("\n🔧 Testando nós individuais...")
    
    # Estado de teste
    test_state = GraphState(
        run_id="test_individual",
        tenant_id="test",
        initial_query="Teste de nó individual",
        task="draft",
        doc_type="parecer",
        rag_docs=[{"content": "Documento teste", "source": "Teste"}],
        config={},
        supervisor_notes=[],
        metrics={}
    )
    
    # Teste Analyzer
    print("\n🔍 Testando Analyzer Node...")
    analyzer_result = await analyzer_node(test_state)
    print(f"✅ Analyzer: {analyzer_result.get('analysis', {}).get('tese_principal', 'N/A')}")
    
    # Atualiza estado
    test_state.update(analyzer_result)
    
    # Teste Drafter
    print("\n✍️ Testando Drafter Node...")
    drafter_result = await drafter_node(test_state)
    print(f"✅ Drafter: {len(drafter_result.get('draft_markdown', ''))} caracteres")
    
    # Atualiza estado
    test_state.update(drafter_result)
    
    # Teste Critic
    print("\n🔎 Testando Critic Node...")
    critic_result = await critic_node(test_state)
    print(f"✅ Critic: {len(critic_result.get('critic_latest_markdown', ''))} caracteres")
    
    # Atualiza estado
    test_state.update(critic_result)
    
    # Teste Formatter
    print("\n🎨 Testando Formatter Node...")
    formatter_result = await formatter_node(test_state)
    print(f"✅ Formatter: {len(formatter_result.get('final_text', ''))} caracteres")
    
    print("\n✅ Todos os nós testados com sucesso!")

if __name__ == "__main__":
    print("🚀 Iniciando testes do Harvey Backend...")
    
    # Executa testes
    asyncio.run(test_individual_nodes())
    asyncio.run(test_graph_execution())
    
    print("\n🎯 Testes concluídos!")
