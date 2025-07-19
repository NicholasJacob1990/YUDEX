"""
Exemplo Simples do Sistema Harvey
Demonstra o funcionamento básico sem LangGraph
"""

import asyncio
from typing import Dict, Any, List

# Simulação de estado sem TypedDict
def create_initial_state() -> Dict[str, Any]:
    """Cria estado inicial para simulação"""
    return {
        'run_id': 'demo-001',
        'tenant_id': 'demo-tenant',
        'initial_query': 'Preciso de uma petição inicial para ação de indenização por danos morais',
        'task': 'DOCUMENT_GENERATION',
        'doc_type': 'PETITION',
        'config': {
            'debug': True,
            'max_iterations': 10,
            'model_provider': 'openai'
        },
        'rag_docs': [
            {
                'id': 'doc-001',
                'title': 'Jurisprudência sobre danos morais',
                'content': 'Caso similar: Indenização por danos morais...',
                'similarity': 0.85
            }
        ],
        'analysis': None,
        'draft_markdown': None,
        'critic_reports': [],
        'critic_latest_markdown': None,
        'final_text': None,
        'next_node_to_call': 'analyzer',
        'supervisor_notes': [],
        'metrics': {}
    }

def print_state_info(state: Dict[str, Any]) -> None:
    """Imprime informações do estado atual"""
    print(f"\n=== Estado Atual ===")
    print(f"  - Run ID: {state['run_id']}")
    print(f"  - Query: {state['initial_query']}")
    print(f"  - Próximo nó: {state['next_node_to_call']}")
    print(f"  - Task: {state['task']}")
    print(f"  - Notas do supervisor: {len(state['supervisor_notes'])}")

async def simulate_analyzer(state: Dict[str, Any]) -> Dict[str, Any]:
    """Simula o agente analyzer"""
    print("\n🔍 Executando Analyzer...")
    await asyncio.sleep(0.5)  # Simula processamento
    
    analysis = {
        'case_type': 'CIVIL_DAMAGES',
        'complexity': 'MEDIUM',
        'required_elements': ['facts', 'legal_basis', 'damages_calculation'],
        'suggested_structure': ['introduction', 'facts', 'legal_arguments', 'conclusion']
    }
    
    return {
        'analysis': analysis,
        'next_node_to_call': 'drafter',
        'supervisor_notes': state['supervisor_notes'] + ['Análise concluída com sucesso']
    }

async def simulate_drafter(state: Dict[str, Any]) -> Dict[str, Any]:
    """Simula o agente drafter"""
    print("\n📝 Executando Drafter...")
    await asyncio.sleep(0.5)  # Simula processamento
    
    draft = """
# PETIÇÃO INICIAL - AÇÃO DE INDENIZAÇÃO POR DANOS MORAIS

## I. QUALIFICAÇÃO DAS PARTES
[Autor e Réu]

## II. DOS FATOS
[Descrição dos fatos que geraram o dano moral]

## III. DO DIREITO
[Fundamentação jurídica baseada no CC/2002 e jurisprudência]

## IV. DO PEDIDO
[Valor da indenização e demais requerimentos]

## V. DO VALOR DA CAUSA
[Valor atribuído à causa]

Termos em que pede deferimento.

[Local], [Data]
[Assinatura do Advogado]
"""
    
    return {
        'draft_markdown': draft,
        'next_node_to_call': 'critic',
        'supervisor_notes': state['supervisor_notes'] + ['Rascunho criado']
    }

async def simulate_critic(state: Dict[str, Any]) -> Dict[str, Any]:
    """Simula o agente critic"""
    print("\n🔍 Executando Critic...")
    await asyncio.sleep(0.5)  # Simula processamento
    
    critic_report = {
        'overall_score': 8.5,
        'strengths': ['Estrutura clara', 'Fundamentação adequada'],
        'weaknesses': ['Falta detalhamento dos danos', 'Valor não especificado'],
        'suggestions': ['Incluir mais detalhes sobre o sofrimento', 'Calcular valor da indenização']
    }
    
    improved_draft = state['draft_markdown'].replace(
        '[Valor da indenização e demais requerimentos]',
        'Requer-se indenização por danos morais no valor de R$ 15.000,00'
    )
    
    return {
        'critic_reports': state['critic_reports'] + [critic_report],
        'critic_latest_markdown': improved_draft,
        'next_node_to_call': 'formatter',
        'supervisor_notes': state['supervisor_notes'] + ['Crítica e melhorias aplicadas']
    }

async def simulate_formatter(state: Dict[str, Any]) -> Dict[str, Any]:
    """Simula o agente formatter"""
    print("\n📄 Executando Formatter...")
    await asyncio.sleep(0.5)  # Simula processamento
    
    # Converte markdown para texto final
    final_text = state['critic_latest_markdown'].replace('# ', '').replace('## ', '')
    
    return {
        'final_text': final_text,
        'next_node_to_call': 'END',
        'supervisor_notes': state['supervisor_notes'] + ['Formatação final concluída']
    }

async def run_simulation():
    """Executa simulação completa"""
    print("🚀 Iniciando simulação do sistema Harvey...")
    
    # Estado inicial
    state = create_initial_state()
    print_state_info(state)
    
    # Simulação do fluxo
    max_iterations = 10
    iteration = 0
    
    while state['next_node_to_call'] != 'END' and iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteração {iteration} ---")
        
        if state['next_node_to_call'] == 'analyzer':
            result = await simulate_analyzer(state)
            state.update(result)
            
        elif state['next_node_to_call'] == 'drafter':
            result = await simulate_drafter(state)
            state.update(result)
            
        elif state['next_node_to_call'] == 'critic':
            result = await simulate_critic(state)
            state.update(result)
            
        elif state['next_node_to_call'] == 'formatter':
            result = await simulate_formatter(state)
            state.update(result)
            
        else:
            print(f"❌ Nó desconhecido: {state['next_node_to_call']}")
            break
    
    # Resultados finais
    print("\n" + "="*50)
    print("✅ SIMULAÇÃO CONCLUÍDA!")
    print("="*50)
    
    print(f"\n📊 Métricas:")
    print(f"  - Iterações: {iteration}")
    print(f"  - Notas do supervisor: {len(state['supervisor_notes'])}")
    print(f"  - Relatórios de crítica: {len(state['critic_reports'])}")
    
    if state.get('analysis'):
        print(f"\n🔍 Análise:")
        for key, value in state['analysis'].items():
            print(f"  - {key}: {value}")
    
    if state.get('final_text'):
        print(f"\n📄 Documento Final:")
        print("-" * 30)
        print(state['final_text'])
    
    if state.get('critic_reports'):
        print(f"\n📋 Relatórios de Crítica:")
        for i, report in enumerate(state['critic_reports'], 1):
            print(f"  Relatório {i}:")
            print(f"    - Score: {report['overall_score']}")
            print(f"    - Pontos fortes: {report['strengths']}")
            print(f"    - Sugestões: {report['suggestions']}")
    
    print(f"\n📝 Histórico do Supervisor:")
    for i, note in enumerate(state['supervisor_notes'], 1):
        print(f"  {i}. {note}")

if __name__ == "__main__":
    asyncio.run(run_simulation())
