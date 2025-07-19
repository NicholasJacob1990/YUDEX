"""
Módulo de Orquestração - Grafo dinâmico de agentes
Transforma pipeline linear em sistema colaborativo inteligente
"""

from .state import (
    GraphState,
    TaskType,
    AgentRole,
    ExecutionStatus,
    DocumentMetadata,
    AgentAction,
    QualityMetrics
)

from .supervisor import GraphSupervisor
from .tools import (
    ToolRegistry,
    BaseTool,
    ToolSchema,
    ToolResult,
    ToolType,
    get_tool_registry
)

from .agents import (
    analyzer_node,
    drafter_node,
    critic_node,
    formatter_node,
    researcher_node
)

# from .registry_init import (
#     initialize_tool_registry,
#     get_available_tools,
#     get_tool_schemas
# )

__all__ = [
    # State
    "GraphState",
    "TaskType", 
    "AgentRole",
    "ExecutionStatus",
    "DocumentMetadata",
    "AgentAction",
    "QualityMetrics",
    
    # Supervisor
    "GraphSupervisor",
    
    # Tools
    "ToolRegistry",
    "BaseTool",
    "ToolSchema", 
    "ToolResult",
    "ToolType",
    "get_tool_registry",
    
    # Agents
    "analyzer_node",
    "drafter_node",
    "critic_node",
    "formatter_node",
    "researcher_node",
    
    # Registry
    # "initialize_tool_registry",
    # "get_available_tools", 
    # "get_tool_schemas"
]
