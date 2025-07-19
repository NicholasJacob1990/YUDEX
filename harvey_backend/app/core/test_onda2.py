"""
Teste e demonstração da Onda 2: Inteligência Ativa e Qualidade Mensurável
"""

import asyncio
import logging
from app.core.intelligent_agent import AgentManager, IntelligentAgent
from app.core.quality_evaluator import GoldenDataset, QualityEvaluator
from app.orch.registry_init import build_tool_registry

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demonstracao_onda2():
    """Demonstração completa da Onda 2"""
    
    print("=" * 60)
    print("🌊 ONDA 2: INTELIGÊNCIA ATIVA E QUALIDADE MENSURÁVEL")
    print("=" * 60)
    
    # 1. Criação do sistema de agentes inteligentes
    print("\n📋 1. CRIANDO SISTEMA DE AGENTES INTELIGENTES")
    print("-" * 40)
    
    manager = AgentManager()
    
    # Agente especializado em direito civil
    agente_civil = manager.create_agent(
        agent_id="civil_specialist",
        tenant_id="escritorio_abc",
        system_message="""Você é um especialista em direito civil brasileiro. 
        Use as ferramentas disponíveis para buscar jurisprudência, legislação e 
        documentos internos. Sempre fundamente suas respostas em fontes confiáveis.""",
        model_provider="openai",
        model_name="gpt-4",
        enable_evaluation=True
    )
    
    # Agente especializado em direito administrativo
    agente_admin = manager.create_agent(
        agent_id="admin_specialist",
        tenant_id="escritorio_abc",
        system_message="""Você é um especialista em direito administrativo brasileiro.
        Foque em licitações, contratos administrativos e procedimentos da administração pública.
        Use as ferramentas para buscar informações atualizadas.""",
        model_provider="anthropic",
        model_name="claude-3-sonnet",
        enable_evaluation=True
    )
    
    print(f"✅ Agente Civil criado: {agente_civil.agent_id}")
    print(f"✅ Agente Administrativo criado: {agente_admin.agent_id}")
    
    # 2. Demonstração de execução com ferramentas
    print("\n🔧 2. DEMONSTRANDO USO ATIVO DE FERRAMENTAS")
    print("-" * 40)
    
    casos_teste = [
        {
            "agente": agente_civil,
            "prompt": "Preciso de jurisprudência recente sobre responsabilidade civil por danos morais em contratos de prestação de serviços",
            "descricao": "Busca de jurisprudência civil"
        },
        {
            "agente": agente_admin,
            "prompt": "Qual o valor da causa para uma ação questionando licitação no valor de R$ 500.000? Consulte também a legislação aplicável",
            "descricao": "Cálculo de valor + consulta legislação"
        },
        {
            "agente": agente_civil,
            "prompt": "Valide a fundamentação legal: 'O contrato deve ser rescindido com base no art. 475 do Código Civil por onerosidade excessiva'",
            "descricao": "Validação de fundamentação legal"
        }
    ]
    
    execucoes = []
    
    for caso in casos_teste:
        print(f"\n🤖 Executando: {caso['descricao']}")
        print(f"📝 Prompt: {caso['prompt']}")
        
        execution = await caso['agente'].execute(caso['prompt'])
        execucoes.append(execution)
        
        print(f"✅ Agente: {execution.agent_id}")
        print(f"⏱️  Tempo: {execution.execution_time:.2f}s")
        print(f"🔧 Ferramentas utilizadas: {', '.join(execution.tools_used) if execution.tools_used else 'Nenhuma'}")
        print(f"📄 Resposta: {execution.response[:150]}...")
        
        if execution.evaluation_result:
            avg_score = sum(execution.evaluation_result.metrics.values()) / len(execution.evaluation_result.metrics)
            print(f"📊 Score de qualidade: {avg_score:.2%}")
    
    # 3. Demonstração do sistema de avaliação
    print("\n📊 3. SISTEMA DE AVALIAÇÃO DE QUALIDADE")
    print("-" * 40)
    
    # Cria dataset de golden samples
    golden_dataset = GoldenDataset()
    print(f"📚 Dataset criado com {len(golden_dataset.samples)} amostras de referência")
    
    # Lista categorias disponíveis
    categorias = set(sample.category for sample in golden_dataset.samples)
    print(f"📂 Categorias disponíveis: {', '.join(categorias)}")
    
    # Demonstra avaliação automática
    print("\n🔍 Executando avaliação automática...")
    
    evaluator = QualityEvaluator(golden_dataset)
    
    # Função de agente simulada para avaliação
    async def agente_para_avaliacao(prompt: str) -> str:
        # Simula execução do agente civil
        execution = await agente_civil.execute(prompt, evaluate_quality=False)
        return execution.response
    
    # Avalia em algumas amostras
    sample_ids = ["juris_001", "calc_001", "valid_001"]
    results = await evaluator.evaluate_agent(agente_para_avaliacao, sample_ids)
    
    # Gera relatório
    report = evaluator.generate_report(results)
    print(report)
    
    # 4. Auto-avaliação dos agentes
    print("\n🔄 4. AUTO-AVALIAÇÃO DOS AGENTES")
    print("-" * 40)
    
    for agente in [agente_civil, agente_admin]:
        print(f"\n🤖 Auto-avaliando agente: {agente.agent_id}")
        
        eval_results = await agente.auto_evaluate(sample_count=2)
        
        if "error" not in eval_results:
            print(f"📊 Score médio: {eval_results['avg_quality_score']:.2%}")
            print(f"🧪 Amostras testadas: {eval_results['samples_tested']}")
            print(f"✅ Avaliações bem-sucedidas: {eval_results['successful_evaluations']}")
            
            # Métricas detalhadas
            print("📈 Métricas detalhadas:")
            for metric, value in eval_results['detailed_metrics'].items():
                print(f"  • {metric.replace('_', ' ').title()}: {value:.2%}")
        else:
            print(f"❌ {eval_results['error']}")
    
    # 5. Relatório de performance
    print("\n📈 5. RELATÓRIO DE PERFORMANCE")
    print("-" * 40)
    
    for agente in [agente_civil, agente_admin]:
        report = agente.get_performance_report()
        print(report)
    
    # 6. Relatório geral do sistema
    print("\n📋 6. RELATÓRIO GERAL DO SISTEMA")
    print("-" * 40)
    
    general_report = manager.get_all_agents_report()
    print(general_report)
    
    # 7. Demonstração de melhoria contínua
    print("\n🔄 7. DEMONSTRAÇÃO DE MELHORIA CONTÍNUA")
    print("-" * 40)
    
    print("🎯 Executando mais casos para demonstrar aprendizado...")
    
    # Executa mais casos no agente civil
    casos_adicionais = [
        "Busque jurisprudência sobre contratos de compra e venda com vício do produto",
        "Calcule o valor da causa para ação de cobrança de R$ 15.000",
        "Valide: 'A garantia deve ser executada conforme art. 441 do CC'"
    ]
    
    for prompt in casos_adicionais:
        await agente_civil.execute(prompt)
    
    # Mostra evolução das métricas
    print(f"\n📊 Métricas após execuções adicionais:")
    print(f"• Total de execuções: {agente_civil.performance_metrics['total_executions']}")
    print(f"• Taxa de sucesso: {agente_civil.performance_metrics['successful_executions'] / agente_civil.performance_metrics['total_executions']:.2%}")
    print(f"• Tempo médio: {agente_civil.performance_metrics['avg_execution_time']:.2f}s")
    
    # 8. Conclusão
    print("\n🎉 8. CONCLUSÃO - ONDA 2 IMPLEMENTADA")
    print("-" * 40)
    
    print("✅ Funcionalidades implementadas:")
    print("  • Agentes com uso ativo de ferramentas")
    print("  • Sistema de avaliação de qualidade automatizada")
    print("  • Golden dataset para benchmarking")
    print("  • Métricas de performance em tempo real")
    print("  • Auto-avaliação e melhoria contínua")
    print("  • Relatórios detalhados de qualidade")
    print("  • Suporte a múltiplos LLMs (OpenAI, Anthropic)")
    print("  • Ferramentas especializadas para domínio jurídico")
    
    print("\n🚀 O sistema Harvey agora possui inteligência ativa e qualidade mensurável!")
    print("=" * 60)

async def teste_rapido():
    """Teste rápido das funcionalidades principais"""
    
    print("🧪 TESTE RÁPIDO - ONDA 2")
    print("-" * 30)
    
    # Cria agente simples
    manager = AgentManager()
    agente = manager.create_agent(
        agent_id="teste_001",
        tenant_id="teste",
        system_message="Você é um assistente jurídico de teste.",
        enable_evaluation=True
    )
    
    # Executa caso simples
    execution = await agente.execute("Preciso de jurisprudência sobre contratos administrativos")
    
    print(f"✅ Execução concluída:")
    print(f"  • Tempo: {execution.execution_time:.2f}s")
    print(f"  • Ferramentas: {execution.tools_used}")
    print(f"  • Resposta: {execution.response[:100]}...")
    
    # Mostra métricas
    metrics = agente.performance_metrics
    print(f"📊 Métricas: {metrics['total_executions']} execuções, {metrics['successful_executions']} sucessos")

if __name__ == "__main__":
    # Executa demonstração completa
    asyncio.run(demonstracao_onda2())
    
    # Ou executa teste rápido
    # asyncio.run(teste_rapido())
