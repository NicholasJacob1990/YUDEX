"""
Exemplo de uso do sistema Harvey com LangGraph
Demonstra como executar o pipeline dinâmico
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from app.orch.state import GraphState, TaskType, ExecutionStatus
from app.orch.langgraph_integration import create_harvey_workflow

async def example_execution():
    """Exemplo de execução do pipeline Harvey"""
    
    print("🚀 Iniciando exemplo de execução Harvey...")
    
    # Criar estado inicial
    initial_state = GraphState(
        session_id="exemplo_001",
        task_type=TaskType.DOCUMENT_DRAFT,
        tenant_id="advocacia_exemplo",
        user_id="usuario_teste",
        user_query="Redija uma petição inicial para ação de cobrança de honorários advocatícios",
        user_requirements={
            "document_type": "petição",
            "area_direito": "civil",
            "urgency": "normal"
        }
    )
    
    # Simular documentos RAG
    initial_state.retrieved_chunks = [
        {
            "text": "Os honorários advocatícios são devidos conforme o Código de Ética da OAB...",
            "source": "Código de Ética OAB",
            "relevance_score": 0.8
        },
        {
            "text": "A ação de cobrança deve fundamentar-se no contrato de honorários...",
            "source": "Jurisprudência STJ",
            "relevance_score": 0.7
        }
    ]
    
    # Criar workflow
    workflow = create_harvey_workflow()
    
    print("📊 Estado inicial:")
    print(f"  - Session ID: {initial_state.session_id}")
    print(f"  - Task: {initial_state.task_type.value}")
    print(f"  - Query: {initial_state.user_query}")
    print(f"  - Chunks RAG: {len(initial_state.retrieved_chunks)}")
    
    # Executar workflow
    try:
        print("\n🔄 Executando workflow...")
        final_state = await workflow.execute(initial_state)
        
        print("\n✅ Execução concluída!")
        print(f"  - Status: {final_state.status.value}")
        print(f"  - Iterações: {final_state.current_iteration}")
        print(f"  - Caminho: {' → '.join(final_state.execution_path)}")
        
        if final_state.final_output:
            print(f"\n📄 Resultado:")
            print(final_state.final_output[:200] + "..." if len(final_state.final_output) > 200 else final_state.final_output)
            
        if final_state.error_messages:
            print(f"\n⚠️  Erros:")
            for error in final_state.error_messages:
                print(f"  - {error}")
                
        # Mostrar resumo de auditoria
        print(f"\n📋 Resumo de auditoria:")
        audit = final_state.get_audit_summary()
        for key, value in audit.items():
            print(f"  - {key}: {value}")
            
    except Exception as e:
        print(f"\n❌ Erro na execução: {str(e)}")
        
def simulate_api_call():
    """Simula uma chamada de API"""
    
    payload = {
        "query": "Redija uma petição inicial para ação de cobrança",
        "task_type": "document_draft",
        "tenant_id": "advocacia_silva",
        "user_id": "usuario_123",
        "requirements": {
            "document_type": "petição",
            "area_direito": "civil"
        },
        "docs": [
            {
                "text": "Contexto jurídico relevante...",
                "source": "Código Civil",
                "relevance_score": 0.9
            }
        ]
    }
    
    print("📡 Simulando chamada de API:")
    print(f"POST /v1/execute")
    print(f"Payload: {payload}")
    
    # Em um cenário real, isso seria processado pelo endpoint FastAPI
    return payload

if __name__ == "__main__":
    print("=" * 50)
    print("EXEMPLO DE USO - HARVEY BACKEND")
    print("=" * 50)
    
    # Simular chamada de API
    api_payload = simulate_api_call()
    
    print("\n" + "=" * 50)
    print("EXECUÇÃO DO WORKFLOW")
    print("=" * 50)
    
    # Executar exemplo
    asyncio.run(example_execution())
