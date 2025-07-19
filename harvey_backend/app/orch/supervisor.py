"""
Supervisor - Roteador condicional do grafo
Decide qual agente deve executar próximo baseado no estado atual
"""

from typing import Optional, Dict, Any
from .state import GraphState, AgentRole, ExecutionStatus, TaskType

class GraphSupervisor:
    """
    Supervisor que decide o próximo agente baseado no estado atual
    Usa lógica determinística e heurística para decisões
    """
    
    def __init__(self, llm_router=None):
        self.llm_router = llm_router
        
    def decide_next_agent(self, state: GraphState) -> Optional[AgentRole]:
        """
        Decide qual agente deve executar próximo
        Retorna None se o grafo deve finalizar
        """
        
        # Verifica condições de parada
        if self._should_terminate(state):
            return None
            
        # Lógica determinística primeiro (mais rápida)
        next_agent = self._deterministic_routing(state)
        if next_agent:
            return next_agent
            
        # Fallback para lógica heurística
        return self._heuristic_routing(state)
        
    def _should_terminate(self, state: GraphState) -> bool:
        """Verifica se o grafo deve terminar"""
        
        # Limite de iterações atingido
        if state.is_max_iterations_reached():
            state.status = ExecutionStatus.FAILED
            state.error_messages.append("Limite de iterações atingido")
            return True
            
        # Tem saída final e está completa
        if state.final_output and state.status == ExecutionStatus.COMPLETED:
            return True
            
        # Precisa de revisão humana
        if state.status == ExecutionStatus.NEEDS_HUMAN_REVIEW:
            return True
            
        # Falha crítica
        if state.status == ExecutionStatus.FAILED:
            return True
            
        return False
        
    def _deterministic_routing(self, state: GraphState) -> Optional[AgentRole]:
        """Roteamento determinístico baseado em regras simples"""
        
        # Primeiro agente sempre é o Analyzer
        if not state.agent_actions:
            return AgentRole.ANALYZER
            
        # Se precisa de mais contexto, vai para o Researcher
        if state.needs_more_context and not self._has_recent_research(state):
            return AgentRole.RESEARCHER
            
        # Se não tem draft, vai para o Drafter
        if not state.current_draft:
            return AgentRole.DRAFTER
            
        # Se tem draft mas precisa de revisão, vai para o Critic
        if state.current_draft and state.needs_review and not self._has_recent_critique(state):
            return AgentRole.CRITIC
            
        # Se está pronto para formatação, vai para o Formatter
        if state.ready_for_formatting:
            return AgentRole.FORMATTER
            
        return None
        
    def _heuristic_routing(self, state: GraphState) -> Optional[AgentRole]:
        """Roteamento heurístico baseado no contexto"""
        
        # Se não tem draft, vai para drafter
        if not state.current_draft:
            return AgentRole.DRAFTER
            
        # Se tem draft mas não foi revisado, vai para critic
        if state.current_draft and not self._has_recent_critique(state):
            return AgentRole.CRITIC
            
        # Se tem draft revisado, vai para formatter
        if state.current_draft and state.critique_feedback:
            return AgentRole.FORMATTER
            
        return None
        
    def _has_recent_research(self, state: GraphState) -> bool:
        """Verifica se houve pesquisa recente"""
        recent_actions = state.agent_actions[-3:] if state.agent_actions else []
        return any(action.agent_role == AgentRole.RESEARCHER for action in recent_actions)
        
    def _has_recent_critique(self, state: GraphState) -> bool:
        """Verifica se houve crítica recente"""
        recent_actions = state.agent_actions[-3:] if state.agent_actions else []
        return any(action.agent_role == AgentRole.CRITIC for action in recent_actions)
        
    def update_state_routing_flags(self, state: GraphState):
        """Atualiza flags de roteamento baseado no estado atual"""
        
        # Verifica se precisa de mais contexto
        state.needs_more_context = self._needs_more_context(state)
        
        # Verifica se precisa de revisão
        state.needs_review = self._needs_review(state)
        
        # Verifica se está pronto para formatação
        state.ready_for_formatting = self._ready_for_formatting(state)
        
    def _needs_more_context(self, state: GraphState) -> bool:
        """Verifica se precisa buscar mais contexto"""
        
        # Poucos chunks recuperados
        if len(state.retrieved_chunks) < 3:
            return True
            
        # Baixa relevância nos chunks
        if state.retrieved_chunks:
            relevance_scores = [chunk.get('relevance_score', 0) for chunk in state.retrieved_chunks]
            if relevance_scores:
                avg_relevance = sum(relevance_scores) / len(relevance_scores)
                if avg_relevance < 0.7:
                    return True
                
        # Análise indica necessidade de mais informações
        if state.analysis_notes:
            last_analysis = state.analysis_notes[-1].lower()
            if any(keyword in last_analysis for keyword in ["mais informações", "contexto insuficiente", "buscar"]):
                return True
                
        return False
        
    def _needs_review(self, state: GraphState) -> bool:
        """Verifica se o draft precisa de revisão"""
        
        # Sempre revisar na primeira vez
        if state.current_draft and not self._has_recent_critique(state):
            return True
            
        # Revisar se houve mudanças significativas
        if len(state.previous_drafts) > 0:
            return True
            
        return False
        
    def _ready_for_formatting(self, state: GraphState) -> bool:
        """Verifica se está pronto para formatação final"""
        
        # Deve ter draft
        if not state.current_draft:
            return False
            
        # Deve ter passado por revisão
        if not self._has_recent_critique(state):
            return False
            
        # Não deve ter críticas graves pendentes
        if state.critique_feedback:
            last_critique = state.critique_feedback[-1].lower()
            if any(keyword in last_critique for keyword in ["grave", "incorreto", "refazer"]):
                return False
                
        return True

# Função simplificada para uso com LangGraph
def supervisor_router(state: dict) -> str:
    """
    Decide qual o próximo nó a ser executado. Este é o ponto central
    da lógica de orquestração dinâmica para LangGraph.
    """
    print("--- Supervisor decidindo próximo passo... ---")
    
    # 1. Se a análise ainda não foi feita, é o primeiro passo.
    if "analysis" not in state or state["analysis"] is None:
        print("Decisão: Chamar Analyzer.")
        return "analyzer"

    # 2. Se a análise foi feita, mas não há rascunho.
    if "draft_markdown" not in state or state["draft_markdown"] is None:
        print("Decisão: Chamar Drafter.")
        return "drafter"

    # 3. Se o rascunho existe, mas precisa de crítica (ex: menos de 2 ciclos).
    critic_count = len(state.get("critic_reports", []))
    if critic_count < 1:  # Rodar a crítica pelo menos uma vez
        print(f"Decisão: Chamar Critic (ciclo {critic_count + 1}).")
        return "critic"
        
    # 4. Se todos os passos principais foram concluídos.
    print("Decisão: Finalizar o fluxo.")
    return "end"