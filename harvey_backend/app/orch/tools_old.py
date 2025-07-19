"""
Sistema de Ferramentas - Registry e Execução com LLM Integration
Permite que agentes chamem funções específicas durante a execução
"""

from typing import Dict, Any, List, Optional, Callable, Union
from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel, Field
import asyncio
import json
import logging
import inspect
import time

logger = logging.getLogger(__name__)

class ToolType(str, Enum):
    """Tipos de ferramentas disponíveis"""
    RAG_SEARCH = "rag_search"
    JURISPRUDENCE = "jurisprudence"
    DOCUMENT_RETRIEVAL = "document_retrieval"
    VALIDATION = "validation"
    FORMATTING = "formatting"
    EXTERNAL_API = "external_api"
    CALCULATION = "calculation"

class ToolResult(BaseModel):
    """Resultado da execução de uma ferramenta"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = Field(default=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolSchema(BaseModel):
    """Schema de definição de uma ferramenta"""
    name: str
    description: str
    tool_type: ToolType
    parameters: Dict[str, Any]
    required_params: List[str] = Field(default_factory=list)
    async_execution: bool = True
    timeout: float = 30.0

class ToolSpec:
    """Define a especificação de uma ferramenta para o LLM e para execução."""
    def __init__(self, name: str, description: str, json_schema: Dict[str, Any], fn: Callable[..., Any]):
        self.name = name
        self.description = description
        self.json_schema = json_schema  # Schema que o LLM usa para saber como chamar a função
        self.fn = fn  # A função Python real (pode ser sync ou async)

class BaseTool(ABC):
    """Classe base para todas as ferramentas"""
    
    def __init__(self, schema: ToolSchema):
        self.schema = schema
        self.name = schema.name
        self.description = schema.description
        self.tool_type = schema.tool_type
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Executa a ferramenta com os parâmetros fornecidos"""
        pass
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Valida se os parâmetros obrigatórios foram fornecidos"""
        return all(param in params for param in self.schema.required_params)

class ToolRegistry:
    """Registry central de ferramentas com suporte a LLM Function Calling"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._schemas: Dict[str, ToolSchema] = {}
        self._tool_specs: Dict[str, ToolSpec] = {}
    
    def register_tool(self, tool: BaseTool):
        """Registra uma nova ferramenta"""
        self._tools[tool.name] = tool
        self._schemas[tool.name] = tool.schema
        logger.info(f"Ferramenta registrada: {tool.name}")
    
    def register_spec(self, spec: ToolSpec):
        """Registra uma especificação de ferramenta para LLM"""
        self._tool_specs[spec.name] = spec
        logger.info(f"Especificação de ferramenta registrada: {spec.name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Obtém uma ferramenta pelo nome"""
        return self._tools.get(name)
    
    def get_tool_specs_for_llm(self) -> List[Dict[str, Any]]:
        """
        Formata as especificações das ferramentas para as APIs de LLM 
        (formato OpenAI/Anthropic/Gemini).
        """
        specs = []
        for tool_spec in self._tool_specs.values():
            specs.append({
                "type": "function",
                "function": {
                    "name": tool_spec.name,
                    "description": tool_spec.description,
                    "parameters": tool_spec.json_schema,
                },
            })
        return specs
    
    async def call(self, tool_name: str, tool_args_str: str) -> Any:
        """Chama uma ferramenta registrada pelo nome com argumentos em string JSON."""
        spec = self._tool_specs.get(tool_name)
        if not spec:
            return f"Erro: Ferramenta '{tool_name}' não encontrada."

        try:
            args = json.loads(tool_args_str)
            if inspect.iscoroutinefunction(spec.fn):
                return await spec.fn(**args)
            else:
                return spec.fn(**args)
        except Exception as e:
            return f"Erro ao executar a ferramenta '{tool_name}': {e}"
    
    def get_available_tools(self) -> List[str]:
        """Lista todas as ferramentas disponíveis"""
        return list(self._tools.keys())
    
    def get_tool_schemas(self) -> Dict[str, ToolSchema]:
        """Retorna os schemas de todas as ferramentas"""
        return self._schemas.copy()
    
    def get_tools_by_type(self, tool_type: ToolType) -> List[BaseTool]:
        """Obtém ferramentas por tipo"""
        return [tool for tool in self._tools.values() if tool.tool_type == tool_type]
    
    async def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Executa uma ferramenta pelo nome"""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Ferramenta '{name}' não encontrada"
            )
        
        if not tool.validate_parameters(kwargs):
            return ToolResult(
                success=False,
                error=f"Parâmetros obrigatórios ausentes: {tool.schema.required_params}"
            )
        
        try:
            start_time = time.time()
            result = await tool.execute(**kwargs)
            result.execution_time = time.time() - start_time
            return result
        except Exception as e:
            logger.error(f"Erro ao executar ferramenta '{name}': {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )

# Instância global do registry
_global_registry = ToolRegistry()

def get_tool_registry() -> ToolRegistry:
    """Obtém a instância global do registry"""
    return _global_registry

from typing import Dict, Any, List, Optional, Callable, Union
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
from enum import Enum
import json
import asyncio
from datetime import datetime

class ToolType(str, Enum):
    """Tipos de ferramentas disponíveis"""
    RAG_SEARCH = "rag_search"
    JURISPRUDENCE_SEARCH = "jurisprudence_search"
    DOCUMENT_ANALYZER = "document_analyzer"
    CITATION_GENERATOR = "citation_generator"
    ABNT_FORMATTER = "abnt_formatter"
    QUALITY_CHECKER = "quality_checker"
    
class ToolParameter(BaseModel):
    """Parâmetro de uma ferramenta"""
    name: str
    type: str  # "string", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[str]] = None

class ToolSchema(BaseModel):
    """Schema completo de uma ferramenta"""
    name: str
    tool_type: ToolType
    description: str
    parameters: List[ToolParameter]
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    
    def to_function_schema(self) -> Dict[str, Any]:
        """Converte para schema de function calling"""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            
            if param.enum:
                prop["enum"] = param.enum
                
            if param.default is not None:
                prop["default"] = param.default
                
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
                
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }

class ToolResult(BaseModel):
    """Resultado da execução de uma ferramenta"""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
class BaseTool(ABC):
    """Classe base para todas as ferramentas"""
    
    def __init__(self, name: str, tool_type: ToolType):
        self.name = name
        self.tool_type = tool_type
        
    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """Retorna o schema da ferramenta"""
        pass
        
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Executa a ferramenta"""
        pass
        
    def _create_result(self, success: bool, result: Any = None, error: str = None, metadata: Dict[str, Any] = None) -> ToolResult:
        """Helper para criar resultado"""
        return ToolResult(
            tool_name=self.name,
            success=success,
            result=result,
            error=error,
            metadata=metadata or {}
        )

class ToolRegistry:
    """Registry centralizado de ferramentas"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_schemas: Dict[str, ToolSchema] = {}
        
    def register_tool(self, tool: BaseTool):
        """Registra uma ferramenta"""
        self._tools[tool.name] = tool
        self._tool_schemas[tool.name] = tool.get_schema()
        
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Obtém uma ferramenta pelo nome"""
        return self._tools.get(name)
        
    def get_tool_schema(self, name: str) -> Optional[ToolSchema]:
        """Obtém o schema de uma ferramenta"""
        return self._tool_schemas.get(name)
        
    def list_tools(self) -> List[str]:
        """Lista todas as ferramentas registradas"""
        return list(self._tools.keys())
        
    def get_tools_by_type(self, tool_type: ToolType) -> List[BaseTool]:
        """Obtém ferramentas por tipo"""
        return [tool for tool in self._tools.values() if tool.tool_type == tool_type]
        
    def get_function_schemas(self) -> List[Dict[str, Any]]:
        """Obtém schemas no formato de function calling"""
        return [schema.to_function_schema() for schema in self._tool_schemas.values()]
        
    async def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Executa uma ferramenta"""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Ferramenta '{name}' não encontrada"
            )
            
        try:
            start_time = datetime.now()
            result = await tool.execute(**kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            return result
            
        except Exception as e:
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Erro na execução: {str(e)}"
            )
            
    def validate_tool_call(self, name: str, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Valida uma chamada de ferramenta"""
        schema = self.get_tool_schema(name)
        if not schema:
            return False, f"Ferramenta '{name}' não encontrada"
            
        # Valida parâmetros obrigatórios
        required_params = [p.name for p in schema.parameters if p.required]
        missing_params = [p for p in required_params if p not in parameters]
        
        if missing_params:
            return False, f"Parâmetros obrigatórios faltando: {', '.join(missing_params)}"
            
        # Valida tipos (validação básica)
        for param in schema.parameters:
            if param.name in parameters:
                value = parameters[param.name]
                if not self._validate_parameter_type(value, param.type):
                    return False, f"Parâmetro '{param.name}' deve ser do tipo '{param.type}'"
                    
        return True, None
        
    def _validate_parameter_type(self, value: Any, expected_type: str) -> bool:
        """Valida tipo de parâmetro"""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "number":
            return isinstance(value, (int, float))
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "object":
            return isinstance(value, dict)
        else:
            return True  # Tipo não reconhecido, aceita

class ToolCallParser:
    """Parser para chamadas de ferramentas em respostas de LLM"""
    
    @staticmethod
    def parse_function_calls(response: str) -> List[Dict[str, Any]]:
        """Extrai chamadas de função de uma resposta"""
        # TODO: Implementar parsing de function calls
        # Por enquanto, retorna lista vazia
        return []
        
    @staticmethod
    def format_tool_results(results: List[ToolResult]) -> str:
        """Formata resultados para inclusão em prompt"""
        if not results:
            return "Nenhuma ferramenta executada."
            
        formatted = []
        for result in results:
            if result.success:
                formatted.append(f"✓ {result.tool_name}: {result.result}")
            else:
                formatted.append(f"✗ {result.tool_name}: {result.error}")
                
        return "\n".join(formatted)

# Singleton global do registry
_global_registry = ToolRegistry()

def get_tool_registry() -> ToolRegistry:
    """Obtém o registry global de ferramentas"""
    return _global_registry
