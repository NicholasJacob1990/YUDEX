"""
LLM Router com suporte a Tool Use
Sistema que permite que LLMs chamem ferramentas durante a execução
"""

import json
from typing import List, Dict, Any, Optional, Tuple, Union
from app.orch.tools import ToolRegistry
import asyncio
import logging

logger = logging.getLogger(__name__)

class LLMResult:
    """Resultado de uma chamada ao LLM"""
    def __init__(self, content: str, usage: Dict[str, Any], tool_calls: Optional[List[Dict[str, Any]]] = None):
        self.content = content
        self.usage = usage
        self.tool_calls = tool_calls or []

# Simulação de clientes LLM - Na produção, você usaria clientes reais
async def openai_chat_simulation(messages: List[Dict[str, str]], model: str, tools: Optional[List[Dict[str, Any]]] = None, tool_choice: str = "auto", **kwargs) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
    """Simula uma chamada ao OpenAI com function calling"""
    
    # Simula latência de API
    await asyncio.sleep(0.5)
    
    # Se não há ferramentas, resposta normal
    if not tools:
        content = "Resposta simulada do OpenAI sem ferramentas."
        usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        return content, usage, []
    
    # Simula decisão de usar ferramenta baseada no contexto
    last_message = messages[-1].get("content", "")
    
    # Lógica simples para decidir se vai usar ferramenta
    tool_calls = []
    
    if "jurisprudência" in last_message.lower() or "julgado" in last_message.lower():
        tool_calls.append({
            "id": "call_123",
            "function": {
                "name": "buscar_jurisprudencia_recente",
                "arguments": json.dumps({"tema": "contratos administrativos", "tribunal": "STJ", "k": 3})
            }
        })
    
    if "documento" in last_message.lower() and "interno" in last_message.lower():
        tool_calls.append({
            "id": "call_456",
            "function": {
                "name": "buscar_documento_interno",
                "arguments": json.dumps({"doc_id": "DOC_001", "tenant_id": "tenant_123"})
            }
        })
    
    if "valor" in last_message.lower() and "causa" in last_message.lower():
        tool_calls.append({
            "id": "call_789",
            "function": {
                "name": "calcular_valor_causa",
                "arguments": json.dumps({"tipo_acao": "indenizacao", "valor_base": 15000.0})
            }
        })
    
    if tool_calls:
        # O LLM decidiu usar ferramentas, então retorna as chamadas
        content = "Vou buscar as informações necessárias para responder adequadamente."
        usage = {"prompt_tokens": 150, "completion_tokens": 30, "total_tokens": 180}
        return content, usage, tool_calls
    else:
        # Resposta normal sem ferramentas
        content = f"Resposta simulada do OpenAI sobre: {last_message[:100]}..."
        usage = {"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200}
        return content, usage, []

async def anthropic_chat_simulation(messages: List[Dict[str, str]], model: str, tools: Optional[List[Dict[str, Any]]] = None, **kwargs) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
    """Simula uma chamada ao Anthropic Claude com function calling"""
    
    await asyncio.sleep(0.4)
    
    if not tools:
        content = "Resposta simulada do Claude sem ferramentas."
        usage = {"input_tokens": 90, "output_tokens": 60}
        return content, usage, []
    
    last_message = messages[-1].get("content", "")
    
    # Claude é mais conservador na decisão de usar ferramentas
    tool_calls = []
    
    if "validar" in last_message.lower() and "fundamentação" in last_message.lower():
        tool_calls.append({
            "id": "call_claude_1",
            "function": {
                "name": "validar_fundamentacao_legal",
                "arguments": json.dumps({"texto": last_message, "area_direito": "civil"})
            }
        })
    
    if "legislação" in last_message.lower() or "lei" in last_message.lower():
        tool_calls.append({
            "id": "call_claude_2",
            "function": {
                "name": "buscar_legislacao_atualizada",
                "arguments": json.dumps({"norma": "Código Civil", "artigo": "art. 421"})
            }
        })
    
    if tool_calls:
        content = "Preciso consultar algumas informações específicas para fornecer uma resposta completa."
        usage = {"input_tokens": 140, "output_tokens": 25}
        return content, usage, tool_calls
    else:
        content = f"Resposta analítica do Claude sobre: {last_message[:100]}..."
        usage = {"input_tokens": 110, "output_tokens": 90}
        return content, usage, []

# Função principal que orquestra o loop de ferramentas
async def llm_with_tools(
    messages: List[Dict[str, Any]], 
    llm_function,  # A função de chamada do LLM (ex: openai_chat_simulation)
    model_name: str,
    tool_registry: ToolRegistry,
    max_tool_rounds: int = 3,
    **llm_kwargs
) -> str:
    """
    Executa um LLM com a capacidade de chamar ferramentas em um loop.
    
    Args:
        messages: Lista de mensagens do conversation history
        llm_function: Função que chama o LLM
        model_name: Nome do modelo a ser usado
        tool_registry: Registry de ferramentas disponíveis
        max_tool_rounds: Número máximo de rounds de ferramentas
        **llm_kwargs: Argumentos adicionais para o LLM
    
    Returns:
        Resposta final do LLM após usar ferramentas
    """
    history = list(messages)
    
    logger.info(f"Iniciando LLM com ferramentas. Modelo: {model_name}")
    
    for round_num in range(max_tool_rounds):
        logger.info(f"Round {round_num + 1}/{max_tool_rounds}")
        
        # Obtém as especificações das ferramentas
        tool_specs = tool_registry.get_tool_specs_for_llm()
        
        # Chama o LLM com as ferramentas disponíveis
        text_response, usage, tool_calls = await llm_function(
            history, 
            model=model_name, 
            tools=tool_specs,
            **llm_kwargs
        )
        
        logger.info(f"LLM respondeu com {len(tool_calls)} chamadas de ferramenta")
        
        if not tool_calls:
            # O LLM não quis chamar nenhuma ferramenta, terminou.
            logger.info("LLM não chamou ferramentas, finalizando")
            return text_response

        # O LLM quer chamar ferramentas. Adiciona a resposta dele ao histórico.
        history.append({
            "role": "assistant", 
            "content": text_response, 
            "tool_calls": tool_calls
        })
        
        # Executa as ferramentas
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args_str = tool_call["function"]["arguments"]
            
            logger.info(f"Executando ferramenta: {tool_name}")
            
            try:
                tool_result = await tool_registry.call(tool_name, tool_args_str)
                
                # Adiciona o resultado da ferramenta ao histórico
                history.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_name,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })
                
                logger.info(f"Ferramenta {tool_name} executada com sucesso")
                
            except Exception as e:
                logger.error(f"Erro ao executar ferramenta {tool_name}: {e}")
                
                # Adiciona erro ao histórico
                history.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_name,
                    "content": json.dumps({"error": str(e)}, ensure_ascii=False),
                })

    # Se atingir o limite de rounds, faz uma última chamada forçando uma resposta textual
    logger.info("Limite de rounds atingido, fazendo chamada final")
    final_response, _, _ = await llm_function(
        history, 
        model=model_name, 
        tools=[],  # Sem ferramentas na chamada final
        **llm_kwargs
    )
    
    return final_response

# Funções de conveniência para diferentes LLMs
async def openai_with_tools(
    messages: List[Dict[str, Any]], 
    model: str, 
    tool_registry: ToolRegistry,
    **kwargs
) -> str:
    """Chama OpenAI com suporte a ferramentas"""
    return await llm_with_tools(
        messages, 
        openai_chat_simulation, 
        model, 
        tool_registry, 
        **kwargs
    )

async def anthropic_with_tools(
    messages: List[Dict[str, Any]], 
    model: str, 
    tool_registry: ToolRegistry,
    **kwargs
) -> str:
    """Chama Anthropic com suporte a ferramentas"""
    return await llm_with_tools(
        messages, 
        anthropic_chat_simulation, 
        model, 
        tool_registry, 
        **kwargs
    )

# Função de alto nível para facilitar o uso
async def intelligent_llm_call(
    prompt: str,
    system_message: str,
    tool_registry: ToolRegistry,
    model_provider: str = "openai",
    model_name: str = "gpt-4",
    **kwargs
) -> str:
    """
    Faz uma chamada inteligente ao LLM com suporte a ferramentas
    
    Args:
        prompt: Pergunta/prompt do usuário
        system_message: Mensagem do sistema
        tool_registry: Registry de ferramentas
        model_provider: Provedor do modelo (openai, anthropic)
        model_name: Nome específico do modelo
        **kwargs: Argumentos adicionais
    
    Returns:
        Resposta final do LLM
    """
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]
    
    if model_provider == "openai":
        return await openai_with_tools(messages, model_name, tool_registry, **kwargs)
    elif model_provider == "anthropic":
        return await anthropic_with_tools(messages, model_name, tool_registry, **kwargs)
    else:
        raise ValueError(f"Provedor não suportado: {model_provider}")

# Exemplo de uso
async def exemplo_uso_ferramentas():
    """Demonstra como usar o sistema de ferramentas"""
    
    from app.orch.registry_init import build_tool_registry
    
    # Cria registry com ferramentas
    registry = build_tool_registry("demo", {})
    
    # Faz chamada inteligente
    response = await intelligent_llm_call(
        prompt="Preciso de jurisprudência recente sobre contratos administrativos e validar a fundamentação legal de um texto.",
        system_message="Você é um assistente jurídico especializado em direito administrativo.",
        tool_registry=registry,
        model_provider="openai",
        model_name="gpt-4"
    )
    
    print(f"Resposta final: {response}")

if __name__ == "__main__":
    asyncio.run(exemplo_uso_ferramentas())
