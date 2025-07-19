"""
Exemplo LangGraph Simples - Sistema Harvey
Versão simplificada que funciona sem problemas de tipos
"""

import asyncio
from typing import TypedDict, Dict, Any, List, Optional
from langgraph.graph import StateGraph, END

# Estado para LangGraph
class HarveyState(TypedDict):
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

# Nós simplificados
async def analyzer_node(state: HarveyState) -> HarveyState:
    """Nó de análise"""
    print("🔍 Executando Analyzer...")
    
    state["analysis"] = {
        "tese_principal": "O limite de 25% é a regra geral, mas exceções são possíveis.",
        "lacunas": ["jurisprudência TCU 2024"],
        "abordagem_recomendada": "Análise constitucional e administrativa",
        "complexidade": "média"
    }
    
    notes = state.get("supervisor_notes", [])
    notes.append("Análise macro concluída. Complexidade: média")
    state["supervisor_notes"] = notes
    
    return state

async def drafter_node(state: HarveyState) -> HarveyState:
    """Nó de redação"""
    print("📝 Executando Drafter...")
    
    state["draft_markdown"] = """## Parecer Jurídico

### I. Dos Fatos
Trata-se de consulta acerca da aplicação do limite de 25% em contratos administrativos.

### II. Análise Jurídica
Conforme a análise realizada, o limite de 25% constitui regra geral estabelecida no art. 65 da Lei 8.666/93.

### III. Fundamentação
Conforme entendimento do TCU (Acórdão 1234/2024), o limite pode ser flexibilizado em casos excepcionais.

### IV. Conclusão
O limite é aplicável, ressalvadas as exceções legais."""
    
    notes = state.get("supervisor_notes", [])
    notes.append("Rascunho inicial gerado")
    state["supervisor_notes"] = notes
    
    return state

async def critic_node(state: HarveyState) -> HarveyState:
    """Nó de crítica"""
    print("🔍 Executando Critic...")
    
    critic_report = {
        "report": "O rascunho está bem estruturado e fundamentado.",
        "quality_score": 0.85,
        "suggestions": ["Adicionar mais fundamentação doutrinária"]
    }
    
    reports = state.get("critic_reports", [])
    reports.append(critic_report)
    state["critic_reports"] = reports
    
    state["critic_latest_markdown"] = state.get("draft_markdown", "")
    
    notes = state.get("supervisor_notes", [])
    notes.append("Ciclo de crítica concluído. Score: 0.85")
    state["supervisor_notes"] = notes
    
    return state

async def formatter_node(state: HarveyState) -> HarveyState:
    """Nó de formatação"""
    print("📄 Executando Formatter...")
    
    text_to_format = state.get("critic_latest_markdown") or state.get("draft_markdown", "")
    
    formatted_text = f"""# PARECER JURÍDICO

{text_to_format}

---
*Documento elaborado conforme normas ABNT*
*Data: 17/07/2025*
"""
    
    state["final_text"] = formatted_text
    
    notes = state.get("supervisor_notes", [])
    notes.append("Formatação ABNT aplicada")
    state["supervisor_notes"] = notes
    
    return state

# Função de roteamento
def routing_function(state: HarveyState) -> str:
    """Determina o próximo nó"""
    print(f"🎯 Roteando baseado no estado atual...")
    
    if not state.get("analysis"):
        print("   → Direcionando para analyzer_node")
        return "analyzer_node"
    elif not state.get("draft_markdown"):
        print("   → Direcionando para drafter_node")
        return "drafter_node"
    elif not state.get("critic_reports"):
        print("   → Direcionando para critic_node")
        return "critic_node"
    elif not state.get("final_text"):
        print("   → Direcionando para formatter_node")
        return "formatter_node"
    else:
        print("   → Finalizando execução")
        return END

def create_harvey_workflow():
    """Cria o workflow do sistema Harvey"""
    workflow = StateGraph(HarveyState)
    
    # Adiciona nós
    workflow.add_node("analyzer_node", analyzer_node)
    workflow.add_node("drafter_node", drafter_node)
    workflow.add_node("critic_node", critic_node)
    workflow.add_node("formatter_node", formatter_node)
    
    # Ponto de entrada
    workflow.set_entry_point("analyzer_node")
    
    # Arestas condicionais
    workflow.add_conditional_edges(
        "analyzer_node",
        routing_function,
        {
            "analyzer_node": "analyzer_node",
            "drafter_node": "drafter_node",
            "critic_node": "critic_node",
            "formatter_node": "formatter_node",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "drafter_node",
        routing_function,
        {
            "analyzer_node": "analyzer_node",
            "drafter_node": "drafter_node",
            "critic_node": "critic_node",
            "formatter_node": "formatter_node",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "critic_node",
        routing_function,
        {
            "analyzer_node": "analyzer_node",
            "drafter_node": "drafter_node",
            "critic_node": "critic_node",
            "formatter_node": "formatter_node",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "formatter_node",
        routing_function,
        {
            "analyzer_node": "analyzer_node",
            "drafter_node": "drafter_node",
            "critic_node": "critic_node",
            "formatter_node": "formatter_node",
            END: END
        }
    )
    
    return workflow.compile()

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
    
    # Cria o workflow
    app = create_harvey_workflow()
    
    print("📊 Estado inicial:")
    print(f"  - Run ID: {initial_state['run_id']}")
    print(f"  - Query: {initial_state['initial_query']}")
    print(f"  - Documentos RAG: {len(initial_state['rag_docs'])}")
    
    # Executa o workflow
    print("\n🔄 Executando workflow LangGraph...")
    
    try:
        result = await app.ainvoke(initial_state)
        
        print(f"\n{'='*50}")
        print("✅ EXECUÇÃO LANGGRAPH CONCLUÍDA!")
        print(f"{'='*50}")
        
        print(f"\n📊 Métricas finais:")
        print(f"  - Notas do supervisor: {len(result.get('supervisor_notes', []))}")
        print(f"  - Relatórios de crítica: {len(result.get('critic_reports', []))}")
        
        if result.get('analysis'):
            print(f"\n🔍 Análise final:")
            for key, value in result['analysis'].items():
                print(f"  - {key}: {value}")
        
        if result.get('final_text'):
            print(f"\n📄 Documento final:")
            print("-" * 30)
            final_text = result['final_text']
            print(final_text)
        
        if result.get('supervisor_notes'):
            print(f"\n📝 Histórico completo:")
            for i, note in enumerate(result['supervisor_notes'], 1):
                print(f"  {i}. {note}")
        
    except Exception as e:
        print(f"❌ Erro durante execução: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_harvey_langgraph())
