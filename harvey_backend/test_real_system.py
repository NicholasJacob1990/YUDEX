"""
Teste Real do Sistema Harvey com GraphState
Usa as classes reais do sistema de orquestração
"""

import asyncio
from typing import Dict, Any
from app.orch.state import GraphState, TaskType, ExecutionStatus
from app.orch.agents import analyzer_node, drafter_node, critic_node, formatter_node
from app.orch.supervisor import supervisor_router

async def test_real_system():
    """Testa o sistema real usando GraphState"""
    print("🚀 Testando sistema Harvey com GraphState real...")
    
    # Cria estado inicial usando GraphState real
    state = GraphState()
    state.run_id = "test-001"
    state.tenant_id = "test-tenant"
    state.initial_query = "Preciso de uma petição inicial para ação de indenização por danos morais"
    state.task = TaskType.DOCUMENT_GENERATION
    state.doc_type = "PETITION"
    state.config = {
        "debug": True,
        "max_iterations": 10,
        "model_provider": "openai"
    }
    state.rag_docs = [
        {
            "id": "doc-001",
            "title": "Jurisprudência sobre danos morais",
            "content": "Caso similar: Indenização por danos morais...",
            "similarity": 0.85
        }
    ]
    state.execution_status = ExecutionStatus.RUNNING
    
    print(f"Estado inicial criado: {state.run_id}")
    print(f"Query: {state.initial_query}")
    print(f"Task: {state.task}")
    
    # Executa análise
    print("\n--- Executando Analyzer ---")
    analyzer_result = await analyzer_node(state)
    state.analysis = analyzer_result.get("analysis")
    state.supervisor_notes = analyzer_result.get("supervisor_notes", [])
    
    print(f"Análise concluída: {state.analysis}")
    
    # Executa redação
    print("\n--- Executando Drafter ---")
    drafter_result = await drafter_node(state)
    state.draft_markdown = drafter_result.get("draft_markdown")
    state.supervisor_notes = drafter_result.get("supervisor_notes", [])
    
    print(f"Rascunho criado: {len(state.draft_markdown)} caracteres")
    
    # Executa crítica
    print("\n--- Executando Critic ---")
    critic_result = await critic_node(state)
    state.critic_latest_markdown = critic_result.get("critic_latest_markdown")
    state.critic_reports = critic_result.get("critic_reports", [])
    state.supervisor_notes = critic_result.get("supervisor_notes", [])
    
    print(f"Crítica concluída: {len(state.critic_reports)} relatórios")
    
    # Executa formatação
    print("\n--- Executando Formatter ---")
    formatter_result = await formatter_node(state)
    state.final_text = formatter_result.get("final_text")
    state.supervisor_notes = formatter_result.get("supervisor_notes", [])
    
    print(f"Formatação concluída: {len(state.final_text)} caracteres")
    
    # Finaliza execução
    state.execution_status = ExecutionStatus.COMPLETED
    
    # Mostra resultados
    print("\n" + "="*50)
    print("✅ TESTE CONCLUÍDO COM SUCESSO!")
    print("="*50)
    
    print(f"\n📊 Métricas:")
    print(f"  - Status: {state.execution_status}")
    print(f"  - Notas do supervisor: {len(state.supervisor_notes)}")
    print(f"  - Relatórios de crítica: {len(state.critic_reports)}")
    
    if state.analysis:
        print(f"\n🔍 Análise:")
        for key, value in state.analysis.items():
            print(f"  - {key}: {value}")
    
    if state.final_text:
        print(f"\n📄 Documento Final:")
        print("-" * 30)
        print(state.final_text[:500] + "..." if len(state.final_text) > 500 else state.final_text)
    
    print(f"\n📝 Histórico do Supervisor:")
    for i, note in enumerate(state.supervisor_notes, 1):
        print(f"  {i}. {note}")
    
    # Teste do supervisor router
    print(f"\n🎯 Testando Supervisor Router:")
    state_dict = state.to_dict()
    next_node = supervisor_router(state_dict)
    print(f"  - Próximo nó sugerido: {next_node}")

if __name__ == "__main__":
    asyncio.run(test_real_system())
