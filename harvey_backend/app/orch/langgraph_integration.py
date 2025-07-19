"""
LangGraph Integration - Adaptador para usar o GraphState com LangGraph
Combina o sistema robusto anterior com a orquestração dinâmica do LangGraph
"""

from typing import Any, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from .state import GraphState, TaskType, AgentRole, ExecutionStatus, AgentAction
from .agents import (
    AnalyzerAgent,
    ResearcherAgent,
    DrafterAgent,
    CriticAgent,
    FormatterAgent
)
from .supervisor import GraphSupervisor

class LangGraphState(TypedDict):
    """
    Estado simplificado para LangGraph TypedDict
    Serve como wrapper para o GraphState mais completo
    """
    # Core data
    session_id: str
    graph_state: Dict[str, Any]  # Serialized GraphState
    
    # Execution control
    next_node: Optional[str]
    iteration: int
    completed: bool
    
    # Results
    final_output: Optional[str]
    error: Optional[str]

class HarveyLangGraphWorkflow:
    """
    Wrapper que integra o sistema Harvey com LangGraph
    """
    
    def __init__(self, llm_router=None):
        self.llm_router = llm_router
        self.supervisor = GraphSupervisor(llm_router) if llm_router else None
        
        # Initialize agents
        self.agents = {
            AgentRole.ANALYZER: AnalyzerAgent(llm_router) if llm_router else None,
            AgentRole.RESEARCHER: ResearcherAgent(llm_router) if llm_router else None,
            AgentRole.DRAFTER: DrafterAgent(llm_router) if llm_router else None,
            AgentRole.CRITIC: CriticAgent(llm_router) if llm_router else None,
            AgentRole.FORMATTER: FormatterAgent(llm_router) if llm_router else None,
        }
        
        # Build LangGraph workflow
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """Constrói o grafo LangGraph"""
        
        workflow = StateGraph(LangGraphState)
        
        # Add nodes
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("analyzer", self._analyzer_node)
        workflow.add_node("researcher", self._researcher_node)
        workflow.add_node("drafter", self._drafter_node)
        workflow.add_node("critic", self._critic_node)
        workflow.add_node("formatter", self._formatter_node)
        
        # Set entry point
        workflow.set_entry_point("supervisor")
        
        # Add conditional edges from supervisor
        workflow.add_conditional_edges(
            "supervisor",
            self._route_next_node,
            {
                "analyzer": "analyzer",
                "researcher": "researcher", 
                "drafter": "drafter",
                "critic": "critic",
                "formatter": "formatter",
                "end": END
            }
        )
        
        # All nodes return to supervisor for next decision
        for node in ["analyzer", "researcher", "drafter", "critic", "formatter"]:
            workflow.add_edge(node, "supervisor")
            
        return workflow.compile(checkpointer=MemorySaver())
        
    def _supervisor_node(self, state: LangGraphState) -> Dict[str, Any]:
        """Nó supervisor que decide próximos passos"""
        
        # Deserialize GraphState
        graph_state = self._deserialize_graph_state(state["graph_state"])
        
        # Use supervisor to decide next agent
        if self.supervisor:
            next_agent = self.supervisor.decide_next_agent(graph_state)
            self.supervisor.update_state_routing_flags(graph_state)
        else:
            # Fallback logic
            next_agent = self._fallback_routing(graph_state)
            
        # Update state
        next_node = next_agent.value if next_agent else "end"
        
        return {
            "next_node": next_node,
            "graph_state": self._serialize_graph_state(graph_state),
            "iteration": state["iteration"] + 1,
            "completed": next_node == "end"
        }
        
    def _analyzer_node(self, state: LangGraphState) -> Dict[str, Any]:
        """Nó analisador"""
        return self._execute_agent_node(state, AgentRole.ANALYZER)
        
    def _researcher_node(self, state: LangGraphState) -> Dict[str, Any]:
        """Nó pesquisador"""
        return self._execute_agent_node(state, AgentRole.RESEARCHER)
        
    def _drafter_node(self, state: LangGraphState) -> Dict[str, Any]:
        """Nó redator"""
        return self._execute_agent_node(state, AgentRole.DRAFTER)
        
    def _critic_node(self, state: LangGraphState) -> Dict[str, Any]:
        """Nó crítico"""
        return self._execute_agent_node(state, AgentRole.CRITIC)
        
    def _formatter_node(self, state: LangGraphState) -> Dict[str, Any]:
        """Nó formatador"""
        return self._execute_agent_node(state, AgentRole.FORMATTER)
        
    async def _execute_agent_node(self, state: LangGraphState, agent_role: AgentRole) -> Dict[str, Any]:
        """Executa um agente específico"""
        
        # Deserialize state
        graph_state = self._deserialize_graph_state(state["graph_state"])
        
        # Get agent
        agent = self.agents.get(agent_role)
        if not agent:
            graph_state.error_messages.append(f"Agente {agent_role.value} não disponível")
            graph_state.status = ExecutionStatus.FAILED
        else:
            # Execute agent
            try:
                graph_state = await agent.execute(graph_state)
            except Exception as e:
                graph_state.error_messages.append(f"Erro no agente {agent_role.value}: {str(e)}")
                graph_state.status = ExecutionStatus.FAILED
        
        return {
            "graph_state": self._serialize_graph_state(graph_state),
            "final_output": graph_state.final_output,
            "error": graph_state.error_messages[-1] if graph_state.error_messages else None
        }
        
    def _route_next_node(self, state: LangGraphState) -> str:
        """Roteamento condicional"""
        return state.get("next_node", "end")
        
    def _fallback_routing(self, graph_state: GraphState) -> Optional[AgentRole]:
        """Roteamento básico quando supervisor não está disponível"""
        
        if not graph_state.agent_actions:
            return AgentRole.ANALYZER
            
        if not graph_state.current_draft:
            return AgentRole.DRAFTER
            
        if graph_state.current_draft and not graph_state.critique_feedback:
            return AgentRole.CRITIC
            
        if graph_state.current_draft and graph_state.critique_feedback:
            return AgentRole.FORMATTER
            
        return None
        
    def _serialize_graph_state(self, graph_state: GraphState) -> Dict[str, Any]:
        """Serializa GraphState para armazenamento"""
        return graph_state.dict()
        
    def _deserialize_graph_state(self, data: Dict[str, Any]) -> GraphState:
        """Deserializa GraphState"""
        return GraphState(**data)
        
    async def execute(self, initial_state: GraphState) -> GraphState:
        """Executa o workflow completo"""
        
        # Convert to LangGraph state
        langgraph_state = LangGraphState(
            session_id=initial_state.session_id,
            graph_state=self._serialize_graph_state(initial_state),
            next_node=None,
            iteration=0,
            completed=False,
            final_output=None,
            error=None
        )
        
        # Execute graph
        config = {"configurable": {"thread_id": initial_state.session_id}}
        
        async for event in self.graph.astream(langgraph_state, config=config):
            for node_name, node_output in event.items():
                print(f"Executando nó: {node_name}")
                if node_output.get("error"):
                    print(f"Erro: {node_output['error']}")
                    
                # Update state
                langgraph_state.update(node_output)
                
                if langgraph_state.get("completed"):
                    break
                    
        # Return final GraphState
        final_graph_state = self._deserialize_graph_state(langgraph_state["graph_state"])
        return final_graph_state

# Factory function
def create_harvey_workflow(llm_router=None) -> HarveyLangGraphWorkflow:
    """Cria uma instância do workflow Harvey"""
    return HarveyLangGraphWorkflow(llm_router)
