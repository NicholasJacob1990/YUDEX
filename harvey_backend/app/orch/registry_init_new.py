"""
Inicializador do Registry de Ferramentas
Monta a "caixa de ferramentas" para uma execução específica
"""

from .tools import ToolRegistry
from .tools_builtin import BUILTIN_TOOL_SPECS

def build_tool_registry(tenant_id: str, config: dict) -> ToolRegistry:
    """Cria e popula o registro de ferramentas para uma execução."""
    registry = ToolRegistry()
    
    # Registra as ferramentas padrão
    for tool_spec in BUILTIN_TOOL_SPECS:
        registry.register_spec(tool_spec)
    
    # TODO: Adicionar lógica para registrar ferramentas específicas por tenant ou tarefa
    # if config.get("enable_financial_tools"):
    #     registry.register_spec(calcular_juros_spec)
    
    # if config.get("enable_external_apis"):
    #     registry.register_spec(consultar_api_externa_spec)
    
    print(f"Registry criado para tenant {tenant_id} com {len(registry.get_available_tools())} ferramentas")
    return registry

def get_available_tools(tenant_id: str = None) -> list:
    """Lista todas as ferramentas disponíveis para um tenant"""
    registry = build_tool_registry(tenant_id or "default", {})
    return registry.get_available_tools()

def get_tool_schemas(tenant_id: str = None) -> dict:
    """Retorna os schemas de todas as ferramentas disponíveis"""
    registry = build_tool_registry(tenant_id or "default", {})
    return registry.get_tool_schemas()

def initialize_tool_registry(tenant_id: str, config: dict) -> ToolRegistry:
    """Inicializa o registry de ferramentas (alias para build_tool_registry)"""
    return build_tool_registry(tenant_id, config)
