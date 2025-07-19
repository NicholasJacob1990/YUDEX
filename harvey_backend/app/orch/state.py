"""
GraphState - Scratchpad compartilhado entre todos os agentes
Estado global que mantém contexto, documentos, drafts e decisões
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class TaskType(str, Enum):
    """Tipos de tarefas que o sistema pode executar"""
    LEGAL_ANALYSIS = "legal_analysis"
    DOCUMENT_DRAFT = "document_draft"
    JURISPRUDENCE_SEARCH = "jurisprudence_search"
    ABNT_FORMAT = "abnt_format"
    REVIEW_CRITIQUE = "review_critique"

class AgentRole(str, Enum):
    """Papéis dos agentes no grafo"""
    ANALYZER = "analyzer"       # Analisa requisitos e contexto
    RESEARCHER = "researcher"   # Busca informações adicionais
    DRAFTER = "drafter"        # Redige documentos
    CRITIC = "critic"          # Revisa e sugere melhorias
    FORMATTER = "formatter"    # Aplica formatação ABNT
    SUPERVISOR = "supervisor"  # Decide próximos passos

class ExecutionStatus(str, Enum):
    """Status de execução do grafo"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_HUMAN_REVIEW = "needs_human_review"

class DocumentMetadata(BaseModel):
    """Metadados dos documentos processados"""
    doc_id: str
    filename: str
    doc_type: str
    area_direito: str
    cliente_tenant: str
    nivel_sigilo: str
    chunks_used: List[str] = Field(default_factory=list)
    relevance_score: Optional[float] = None

class AgentAction(BaseModel):
    """Registro de ação executada por um agente"""
    agent_role: AgentRole
    action_type: str
    timestamp: datetime = Field(default_factory=datetime.now)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    tools_used: List[str] = Field(default_factory=list)
    confidence_score: Optional[float] = None
    reasoning: Optional[str] = None

class QualityMetrics(BaseModel):
    """Métricas de qualidade da resposta"""
    context_recall: Optional[float] = None
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    abnt_compliance: Optional[float] = None
    citation_accuracy: Optional[float] = None
    
class GraphState(BaseModel):
    """
    Estado compartilhado entre todos os agentes no grafo
    Funciona como um "scratchpad" global
    """
    
    class Config:
        """Configuração do Pydantic"""
        arbitrary_types_allowed = True
    
    # === Identificação e Metadados ===
    session_id: str
    task_type: TaskType
    tenant_id: str
    user_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    # === Input Original ===
    user_query: str
    user_requirements: Dict[str, Any] = Field(default_factory=dict)
    uploaded_docs: List[DocumentMetadata] = Field(default_factory=list)
    
    # === Contexto RAG ===
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    reranked_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    jurisprudence_context: List[Dict[str, Any]] = Field(default_factory=list)
    
    # === Trabalho em Progresso ===
    current_draft: Optional[str] = None
    previous_drafts: List[str] = Field(default_factory=list)
    analysis_notes: List[str] = Field(default_factory=list)
    critique_feedback: List[str] = Field(default_factory=list)
    
    # === Decisões e Roteamento ===
    next_agent: Optional[AgentRole] = None
    needs_more_context: bool = False
    needs_review: bool = False
    ready_for_formatting: bool = False
    
    # === Histórico de Execução ===
    agent_actions: List[AgentAction] = Field(default_factory=list)
    execution_path: List[str] = Field(default_factory=list)
    
    # === Qualidade e Auditoria ===
    quality_metrics: QualityMetrics = Field(default_factory=QualityMetrics)
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)
    
    # === Status Final ===
    status: ExecutionStatus = ExecutionStatus.PENDING
    final_output: Optional[str] = None
    error_messages: List[str] = Field(default_factory=list)
    
    # === Configurações ===
    model_config_dict: Dict[str, Any] = Field(default_factory=dict)
    max_iterations: int = 10
    current_iteration: int = 0
    
    def add_agent_action(self, action: AgentAction):
        """Adiciona uma ação ao histórico"""
        self.agent_actions.append(action)
        self.execution_path.append(f"{action.agent_role.value}:{action.action_type}")
        
    def add_analysis_note(self, note: str, agent_role: AgentRole):
        """Adiciona nota de análise"""
        timestamped_note = f"[{datetime.now().isoformat()}] {agent_role.value}: {note}"
        self.analysis_notes.append(timestamped_note)
        
    def add_critique(self, critique: str, agent_role: AgentRole = AgentRole.CRITIC):
        """Adiciona feedback de crítica"""
        timestamped_critique = f"[{datetime.now().isoformat()}] {agent_role.value}: {critique}"
        self.critique_feedback.append(timestamped_critique)
        
    def increment_iteration(self):
        """Incrementa contador de iterações"""
        self.current_iteration += 1
        
    def is_max_iterations_reached(self) -> bool:
        """Verifica se atingiu limite de iterações"""
        return self.current_iteration >= self.max_iterations
        
    def get_context_summary(self) -> str:
        """Resumo do contexto para prompts"""
        summary = f"Tarefa: {self.task_type.value}\n"
        summary += f"Query: {self.user_query}\n"
        summary += f"Documentos: {len(self.uploaded_docs)} docs\n"
        summary += f"Chunks RAG: {len(self.retrieved_chunks)} chunks\n"
        summary += f"Iteração: {self.current_iteration}/{self.max_iterations}\n"
        
        if self.analysis_notes:
            summary += f"Análises: {len(self.analysis_notes)} notas\n"
            
        if self.critique_feedback:
            summary += f"Críticas: {len(self.critique_feedback)} feedbacks\n"
            
        return summary
        
    def get_audit_summary(self) -> Dict[str, Any]:
        """Resumo para auditoria"""
        return {
            "session_id": self.session_id,
            "task_type": self.task_type.value,
            "tenant_id": self.tenant_id,
            "execution_path": self.execution_path,
            "iterations": self.current_iteration,
            "status": self.status.value,
            "docs_processed": len(self.uploaded_docs),
            "chunks_used": len(self.retrieved_chunks),
            "quality_metrics": self.quality_metrics.dict(),
            "created_at": self.created_at.isoformat(),
            "agents_involved": list(set([action.agent_role.value for action in self.agent_actions]))
        }