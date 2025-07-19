"""
Teste Básico do Sistema Harvey - Apenas Agentes
Testa apenas os nós dos agentes sem dependências externas
"""

import asyncio
from typing import Dict, Any

# Importação direta dos agentes
from app.orch.agents import analyzer_node, drafter_node, critic_node, formatter_node

# Estado simulado simples
def create_test_state() -> Dict[str, Any]:
    """Cria um estado de teste simples"""
    return {
        "run_id": "test-001",
        "tenant_id": "test-tenant", 
        "initial_query": "Preciso de uma petição inicial para ação de indenização por danos morais",
        "task": "DOCUMENT_GENERATION",
        "doc_type": "PETITION",
        "config": {
            "debug": True,
            "max_iterations": 10,
            "model_provider": "openai"
        },
        "rag_docs": [
            {
                "id": "doc-001",
                "title": "Jurisprudência sobre danos morais",
                "content": "Caso similar: Indenização por danos morais...",
                "similarity": 0.85
            }
        ],
        "analysis": None,
        "draft_markdown": None,
        "critic_reports": [],
        "critic_latest_markdown": None,
        "final_text": None,
        "supervisor_notes": []
    }

# Classe mock para simular GraphState
class MockGraphState:
    def __init__(self, data: Dict[str, Any]):
        self._data = data
    
    def get(self, key: str, default=None):
        return self._data.get(key, default)
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __setitem__(self, key, value):
        self._data[key] = value
    
    def to_dict(self):
        return self._data.copy()

async def test_agents_only():
    """Testa apenas os agentes individuais"""
    print("🚀 Testando agentes individuais do sistema Harvey...")
    
    # Cria estado inicial
    state_data = create_test_state()
    state = MockGraphState(state_data)
    
    print(f"Estado inicial criado: {state.get('run_id')}")
    print(f"Query: {state.get('initial_query')}")
    
    # Testa Analyzer
    print("\n--- Testando Analyzer ---")
    try:
        analyzer_result = await analyzer_node(state)
        print(f"✅ Analyzer executado com sucesso")
        print(f"   - Resultado: {analyzer_result}")
        state._data.update(analyzer_result)
    except Exception as e:
        print(f"❌ Erro no Analyzer: {e}")
        return
    
    # Testa Drafter
    print("\n--- Testando Drafter ---")
    try:
        drafter_result = await drafter_node(state)
        print(f"✅ Drafter executado com sucesso")
        print(f"   - Tamanho do draft: {len(drafter_result.get('draft_markdown', ''))}")
        state._data.update(drafter_result)
    except Exception as e:
        print(f"❌ Erro no Drafter: {e}")
        return
    
    # Testa Critic
    print("\n--- Testando Critic ---")
    try:
        critic_result = await critic_node(state)
        print(f"✅ Critic executado com sucesso")
        print(f"   - Relatórios: {len(critic_result.get('critic_reports', []))}")
        state._data.update(critic_result)
    except Exception as e:
        print(f"❌ Erro no Critic: {e}")
        return
    
    # Testa Formatter
    print("\n--- Testando Formatter ---")
    try:
        formatter_result = await formatter_node(state)
        print(f"✅ Formatter executado com sucesso")
        print(f"   - Texto final: {len(formatter_result.get('final_text', ''))}")
        state._data.update(formatter_result)
    except Exception as e:
        print(f"❌ Erro no Formatter: {e}")
        return
    
    # Mostra resultados
    print("\n" + "="*50)
    print("✅ TESTE DOS AGENTES CONCLUÍDO COM SUCESSO!")
    print("="*50)
    
    print(f"\n📊 Resultados:")
    print(f"  - Notas do supervisor: {len(state.get('supervisor_notes', []))}")
    print(f"  - Relatórios de crítica: {len(state.get('critic_reports', []))}")
    print(f"  - Análise gerada: {'✅' if state.get('analysis') else '❌'}")
    print(f"  - Draft criado: {'✅' if state.get('draft_markdown') else '❌'}")
    print(f"  - Texto final: {'✅' if state.get('final_text') else '❌'}")
    
    if state.get('analysis'):
        print(f"\n🔍 Análise:")
        for key, value in state.get('analysis', {}).items():
            print(f"  - {key}: {value}")
    
    if state.get('final_text'):
        print(f"\n📄 Documento Final (primeiros 300 caracteres):")
        print("-" * 30)
        final_text = state.get('final_text', '')
        print(final_text[:300] + "..." if len(final_text) > 300 else final_text)
    
    print(f"\n📝 Histórico do Supervisor:")
    for i, note in enumerate(state.get('supervisor_notes', []), 1):
        print(f"  {i}. {note}")

if __name__ == "__main__":
    asyncio.run(test_agents_only())
