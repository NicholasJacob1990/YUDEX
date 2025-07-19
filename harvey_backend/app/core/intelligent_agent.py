"""
Agent Wrapper com Inteligência Ativa
Integra ferramentas, avaliação de qualidade e comportamento inteligente
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import logging
import json

from app.core.llm_router import intelligent_llm_call
from app.core.quality_evaluator import QualityEvaluator, GoldenDataset, EvaluationResult
from app.orch.tools import ToolRegistry
from app.orch.registry_init import build_tool_registry

logger = logging.getLogger(__name__)

@dataclass
class AgentExecution:
    """Resultado da execução de um agente"""
    agent_id: str
    prompt: str
    response: str
    tools_used: List[str]
    execution_time: float
    timestamp: datetime
    evaluation_result: Optional[EvaluationResult] = None
    error: Optional[str] = None

class IntelligentAgent:
    """
    Agente inteligente que:
    1. Usa ferramentas ativamente para buscar informações
    2. Se auto-avalia continuamente
    3. Aprende com feedback e melhora performance
    """
    
    def __init__(
        self,
        agent_id: str,
        tenant_id: str,
        system_message: str,
        model_provider: str = "openai",
        model_name: str = "gpt-4",
        tools_config: Optional[Dict[str, Any]] = None,
        enable_evaluation: bool = True
    ):
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self.system_message = system_message
        self.model_provider = model_provider
        self.model_name = model_name
        self.enable_evaluation = enable_evaluation
        
        # Inicializa registry de ferramentas
        self.tool_registry = build_tool_registry(tenant_id, tools_config or {})
        
        # Sistema de avaliação
        if enable_evaluation:
            self.golden_dataset = GoldenDataset()
            self.evaluator = QualityEvaluator(self.golden_dataset)
        
        # Histórico de execuções
        self.execution_history: List[AgentExecution] = []
        
        # Métricas de performance
        self.performance_metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "avg_execution_time": 0.0,
            "avg_quality_score": 0.0,
            "tools_usage_count": {},
            "error_count": 0
        }
    
    async def execute(self, prompt: str, evaluate_quality: Optional[bool] = None) -> AgentExecution:
        """
        Executa o agente com inteligência ativa
        
        Args:
            prompt: Prompt do usuário
            evaluate_quality: Se deve avaliar qualidade (padrão: usa configuração do agente)
        
        Returns:
            Resultado da execução com métricas
        """
        
        start_time = asyncio.get_event_loop().time()
        evaluate_quality = evaluate_quality if evaluate_quality is not None else self.enable_evaluation
        
        logger.info(f"Iniciando execução do agente {self.agent_id}")
        logger.info(f"Prompt: {prompt[:100]}...")
        
        execution = AgentExecution(
            agent_id=self.agent_id,
            prompt=prompt,
            response="",
            tools_used=[],
            execution_time=0.0,
            timestamp=datetime.now()
        )
        
        try:
            # Executa o LLM com ferramentas
            response = await intelligent_llm_call(
                prompt=prompt,
                system_message=self.system_message,
                tool_registry=self.tool_registry,
                model_provider=self.model_provider,
                model_name=self.model_name
            )
            
            execution.response = response
            execution.execution_time = asyncio.get_event_loop().time() - start_time
            
            # Captura ferramentas utilizadas (simulado - na produção seria capturado do LLM router)
            execution.tools_used = self._extract_tools_used(response)
            
            # Avaliação de qualidade
            if evaluate_quality:
                execution.evaluation_result = await self._evaluate_execution(execution)
            
            # Atualiza métricas
            self._update_metrics(execution)
            
            logger.info(f"Execução concluída com sucesso em {execution.execution_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Erro na execução do agente {self.agent_id}: {e}")
            execution.error = str(e)
            execution.execution_time = asyncio.get_event_loop().time() - start_time
            self.performance_metrics["error_count"] += 1
        
        # Adiciona ao histórico
        self.execution_history.append(execution)
        
        return execution
    
    def _extract_tools_used(self, response: str) -> List[str]:
        """Extrai ferramentas utilizadas da resposta (simulado)"""
        # Na produção, isso seria capturado do LLM router
        tools = []
        
        if "jurisprudência" in response.lower():
            tools.append("buscar_jurisprudencia_recente")
        
        if "documento interno" in response.lower():
            tools.append("buscar_documento_interno")
        
        if "valor" in response.lower() and "causa" in response.lower():
            tools.append("calcular_valor_causa")
        
        if "validar" in response.lower() and "fundamentação" in response.lower():
            tools.append("validar_fundamentacao_legal")
        
        if "legislação" in response.lower() or "lei" in response.lower():
            tools.append("buscar_legislacao_atualizada")
        
        return tools
    
    async def _evaluate_execution(self, execution: AgentExecution) -> Optional[EvaluationResult]:
        """Avalia a qualidade da execução"""
        
        if not self.enable_evaluation:
            return None
        
        try:
            # Busca amostra similar no golden dataset
            similar_sample = self._find_similar_sample(execution.prompt)
            
            if similar_sample:
                # Cria função de agente para avaliação
                async def agent_function(prompt: str) -> str:
                    return execution.response
                
                # Avalia usando o golden dataset
                evaluation_result = await self.evaluator.evaluate_sample(
                    similar_sample, 
                    agent_function, 
                    execution.tools_used
                )
                
                logger.info(f"Avaliação concluída para execução {execution.agent_id}")
                return evaluation_result
            
        except Exception as e:
            logger.error(f"Erro na avaliação: {e}")
        
        return None
    
    def _find_similar_sample(self, prompt: str) -> Optional[Any]:
        """Encontra amostra similar no golden dataset"""
        # Implementação simples baseada em palavras-chave
        prompt_lower = prompt.lower()
        
        for sample in self.golden_dataset.samples:
            sample_words = set(sample.input_prompt.lower().split())
            prompt_words = set(prompt_lower.split())
            
            # Calcula similaridade
            intersection = sample_words.intersection(prompt_words)
            union = sample_words.union(prompt_words)
            
            if union and len(intersection) / len(union) > 0.3:  # 30% similaridade
                return sample
        
        return None
    
    def _update_metrics(self, execution: AgentExecution):
        """Atualiza métricas de performance"""
        
        self.performance_metrics["total_executions"] += 1
        
        if execution.error is None:
            self.performance_metrics["successful_executions"] += 1
        
        # Atualiza tempo médio
        total_time = (self.performance_metrics["avg_execution_time"] * 
                     (self.performance_metrics["total_executions"] - 1) + 
                     execution.execution_time)
        self.performance_metrics["avg_execution_time"] = total_time / self.performance_metrics["total_executions"]
        
        # Atualiza uso de ferramentas
        for tool in execution.tools_used:
            self.performance_metrics["tools_usage_count"][tool] = (
                self.performance_metrics["tools_usage_count"].get(tool, 0) + 1
            )
        
        # Atualiza score de qualidade
        if execution.evaluation_result:
            current_score = self.performance_metrics["avg_quality_score"]
            new_score = sum(execution.evaluation_result.metrics.values()) / len(execution.evaluation_result.metrics)
            
            total_evaluations = len([e for e in self.execution_history if e.evaluation_result])
            
            if total_evaluations > 0:
                self.performance_metrics["avg_quality_score"] = (
                    (current_score * (total_evaluations - 1) + new_score) / total_evaluations
                )
    
    def get_performance_report(self) -> str:
        """Gera relatório de performance do agente"""
        
        metrics = self.performance_metrics
        
        report = f"""
=== RELATÓRIO DE PERFORMANCE - AGENTE {self.agent_id} ===

🤖 INFORMAÇÕES GERAIS:
• Tenant: {self.tenant_id}
• Modelo: {self.model_provider}/{self.model_name}
• Avaliação Habilitada: {'Sim' if self.enable_evaluation else 'Não'}

📊 MÉTRICAS DE EXECUÇÃO:
• Total de Execuções: {metrics['total_executions']}
• Execuções Bem-sucedidas: {metrics['successful_executions']}
• Taxa de Sucesso: {metrics['successful_executions'] / max(metrics['total_executions'], 1):.2%}
• Tempo Médio: {metrics['avg_execution_time']:.2f}s
• Erros: {metrics['error_count']}

📈 QUALIDADE:
• Score Médio de Qualidade: {metrics['avg_quality_score']:.2%}

🔧 USO DE FERRAMENTAS:
"""
        
        for tool, count in metrics['tools_usage_count'].items():
            report += f"• {tool}: {count} usos\n"
        
        if not metrics['tools_usage_count']:
            report += "• Nenhuma ferramenta utilizada\n"
        
        # Últimas execuções
        recent_executions = self.execution_history[-5:]  # Últimas 5
        
        report += f"\n🕐 ÚLTIMAS EXECUÇÕES:\n"
        for exec in recent_executions:
            status = "✅" if exec.error is None else "❌"
            quality = ""
            if exec.evaluation_result:
                avg_score = sum(exec.evaluation_result.metrics.values()) / len(exec.evaluation_result.metrics)
                quality = f" (Q: {avg_score:.1%})"
            
            report += f"• {exec.timestamp.strftime('%H:%M:%S')} {status} {exec.execution_time:.2f}s{quality}\n"
        
        return report
    
    async def auto_evaluate(self, sample_count: int = 3) -> Dict[str, Any]:
        """
        Auto-avaliação usando amostras do golden dataset
        
        Args:
            sample_count: Número de amostras para testar
            
        Returns:
            Resultados da avaliação
        """
        
        if not self.enable_evaluation:
            return {"error": "Avaliação não habilitada para este agente"}
        
        # Seleciona amostras aleatórias
        import random
        samples = random.sample(self.golden_dataset.samples, min(sample_count, len(self.golden_dataset.samples)))
        
        results = []
        
        for sample in samples:
            logger.info(f"Auto-avaliação com amostra {sample.id}")
            
            # Executa o agente
            execution = await self.execute(sample.input_prompt, evaluate_quality=True)
            results.append(execution)
        
        # Calcula métricas agregadas
        evaluation_results = [r.evaluation_result for r in results if r.evaluation_result]
        
        if not evaluation_results:
            return {"error": "Nenhuma avaliação foi possível"}
        
        # Métricas agregadas
        total_score = sum(
            sum(result.metrics.values()) / len(result.metrics) 
            for result in evaluation_results
        )
        
        avg_score = total_score / len(evaluation_results)
        
        return {
            "avg_quality_score": avg_score,
            "samples_tested": len(samples),
            "successful_evaluations": len(evaluation_results),
            "results": results,
            "detailed_metrics": {
                metric.value: sum(result.metrics[metric] for result in evaluation_results) / len(evaluation_results)
                for metric in evaluation_results[0].metrics.keys()
            }
        }

# Sistema de gerenciamento de agentes
class AgentManager:
    """Gerencia múltiplos agentes inteligentes"""
    
    def __init__(self):
        self.agents: Dict[str, IntelligentAgent] = {}
    
    def create_agent(
        self, 
        agent_id: str, 
        tenant_id: str, 
        system_message: str,
        **kwargs
    ) -> IntelligentAgent:
        """Cria um novo agente"""
        
        agent = IntelligentAgent(
            agent_id=agent_id,
            tenant_id=tenant_id,
            system_message=system_message,
            **kwargs
        )
        
        self.agents[agent_id] = agent
        logger.info(f"Agente {agent_id} criado para tenant {tenant_id}")
        
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[IntelligentAgent]:
        """Busca um agente específico"""
        return self.agents.get(agent_id)
    
    async def execute_agent(self, agent_id: str, prompt: str) -> Optional[AgentExecution]:
        """Executa um agente específico"""
        agent = self.get_agent(agent_id)
        
        if not agent:
            logger.error(f"Agente {agent_id} não encontrado")
            return None
        
        return await agent.execute(prompt)
    
    def get_all_agents_report(self) -> str:
        """Gera relatório de todos os agentes"""
        
        if not self.agents:
            return "Nenhum agente registrado."
        
        report = "=== RELATÓRIO GERAL DE AGENTES ===\n\n"
        
        for agent_id, agent in self.agents.items():
            report += f"📋 {agent_id}:\n"
            report += f"• Tenant: {agent.tenant_id}\n"
            report += f"• Execuções: {agent.performance_metrics['total_executions']}\n"
            report += f"• Taxa de Sucesso: {agent.performance_metrics['successful_executions'] / max(agent.performance_metrics['total_executions'], 1):.2%}\n"
            report += f"• Qualidade Média: {agent.performance_metrics['avg_quality_score']:.2%}\n\n"
        
        return report

# Exemplo de uso
async def exemplo_agent_inteligente():
    """Demonstra o uso do agente inteligente"""
    
    # Cria gerenciador
    manager = AgentManager()
    
    # Cria agente jurídico
    agent = manager.create_agent(
        agent_id="juridico_001",
        tenant_id="cliente_abc",
        system_message="Você é um assistente jurídico especializado em direito civil e administrativo. Use as ferramentas disponíveis para buscar informações precisas e atualizadas.",
        model_provider="openai",
        model_name="gpt-4",
        enable_evaluation=True
    )
    
    # Executa algumas tarefas
    prompts = [
        "Preciso de jurisprudência recente do STJ sobre rescisão de contratos administrativos",
        "Qual o valor da causa para uma ação de indenização de R$ 25.000?",
        "Valide esta fundamentação: O contrato deve ser rescindido com base no art. 78 da Lei 8.666/93"
    ]
    
    for prompt in prompts:
        print(f"\n🤖 Executando: {prompt}")
        execution = await agent.execute(prompt)
        print(f"✅ Resposta: {execution.response[:100]}...")
        print(f"⏱️  Tempo: {execution.execution_time:.2f}s")
        print(f"🔧 Ferramentas: {execution.tools_used}")
    
    # Relatório de performance
    print("\n" + agent.get_performance_report())
    
    # Auto-avaliação
    print("\n🔍 Iniciando auto-avaliação...")
    eval_results = await agent.auto_evaluate(sample_count=3)
    print(f"📊 Score de qualidade: {eval_results.get('avg_quality_score', 0):.2%}")

if __name__ == "__main__":
    asyncio.run(exemplo_agent_inteligente())
