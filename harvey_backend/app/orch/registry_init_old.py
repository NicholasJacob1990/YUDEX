"""
Registry Init - Inicialização do registry de ferramentas
Registra todas as ferramentas disponíveis no sistema
"""

from app.orch.tools import get_tool_registry
from app.orch.tools_builtin import (
    RAGSearchTool,
    JurisprudenceSearchTool,
    DocumentAnalyzerTool,
    ABNTFormatterTool,
    CitationGeneratorTool
)

# Importações dos serviços core (serão implementados posteriormente)
# from app.core.rag import RAGPipeline
# from app.core.vectordb import VectorDB
# from app.core.abnt import ABNTFormatter
# from app.core.embeddings import EmbeddingService

def initialize_tool_registry():
    """
    Inicializa o registry global de ferramentas
    Registra todas as ferramentas disponíveis
    """
    
    registry = get_tool_registry()
    
    # TODO: Inicializar serviços core quando estiverem implementados
    # Por enquanto, usamos None como placeholder
    
    # rag_pipeline = RAGPipeline()
    # vector_db = VectorDB()
    # abnt_formatter = ABNTFormatter()
    # embedding_service = EmbeddingService()
    
    # Registra ferramentas built-in
    tools = [
        # RAGSearchTool(rag_pipeline),
        # JurisprudenceSearchTool(vector_db),
        # DocumentAnalyzerTool(embedding_service),
        # ABNTFormatterTool(abnt_formatter),
        CitationGeneratorTool(),
    ]
    
    # Registra apenas Citation Generator por enquanto
    registry.register_tool(CitationGeneratorTool())
    
    print(f"Registry inicializado com {len(registry.list_tools())} ferramentas")
    
    return registry

def get_available_tools():
    """
    Retorna lista de ferramentas disponíveis
    """
    registry = get_tool_registry()
    return registry.list_tools()

def get_tool_schemas():
    """
    Retorna schemas de todas as ferramentas para function calling
    """
    registry = get_tool_registry()
    return registry.get_function_schemas()

# Função para inicializar automaticamente na importação
def auto_initialize():
    """
    Inicialização automática do registry
    """
    try:
        initialize_tool_registry()
        print("Tool registry inicializado com sucesso")
    except Exception as e:
        print(f"Erro na inicialização do tool registry: {e}")
        
# Inicializa automaticamente quando o módulo é importado
# auto_initialize()
