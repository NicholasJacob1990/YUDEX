"""
Integração das Ferramentas Harvey com LangGraph - Onda 2
Demonstra como usar as ferramentas no workflow de orquestração
"""

from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
import json
import logging

from app.orch.tools_harvey import get_harvey_tools, register_harvey_tools
from app.orch.tools import get_tool_registry
from app.orch.rag_node import rag_node, context_validator_node, should_validate_context
from app.models.schema_api import ExternalDoc

logger = logging.getLogger(__name__)

class WorkflowState(TypedDict):
    """Estado do workflow com suporte a ferramentas e contexto externo"""
    messages: List[Dict[str, Any]]
    current_task: str
    context: Dict[str, Any]
    tool_results: Dict[str, Any]
    quality_score: float
    documents: List[Dict[str, Any]]
    citations: List[str]
    final_output: str
    
    # Campos para contexto externo
    external_docs: Optional[List[ExternalDoc]]
    external_context_summary: Optional[Dict[str, Any]]
    context_validation_result: Optional[Dict[str, Any]]
    rag_docs: List[Dict[str, Any]]  # Documentos do RAG (internos + externos)
    context_metadata: Dict[str, Any]  # Metadados do contexto usado
    external_docs_used: List[Dict[str, Any]]  # Documentos externos efetivamente utilizados

class HarveyToolsWorkflow:
    """Workflow integrado com ferramentas Harvey"""
    
    def __init__(self):
        self.registry = get_tool_registry()
        register_harvey_tools(self.registry)
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Constrói o grafo de workflow com ferramentas e contexto externo"""
        graph = StateGraph(WorkflowState)
        
        # Nós do workflow
        graph.add_node("analyze_request", self._analyze_request)
        graph.add_node("validate_external_context", self._validate_external_context)
        graph.add_node("execute_rag", self._execute_rag)
        graph.add_node("search_jurisprudence", self._search_jurisprudence)
        graph.add_node("search_documents", self._search_documents)
        graph.add_node("analyze_documents", self._analyze_documents)
        graph.add_node("generate_content", self._generate_content)
        graph.add_node("check_quality", self._check_quality)
        graph.add_node("generate_citations", self._generate_citations)
        graph.add_node("finalize_output", self._finalize_output)
        
        # Fluxo do workflow com contexto externo
        graph.add_edge("analyze_request", "validate_external_context")
        graph.add_edge("validate_external_context", "execute_rag")
        graph.add_edge("execute_rag", "search_jurisprudence")
        graph.add_edge("search_jurisprudence", "search_documents")
        graph.add_edge("search_documents", "analyze_documents")
        graph.add_edge("analyze_documents", "generate_content")
        graph.add_edge("generate_content", "check_quality")
        graph.add_edge("check_quality", "generate_citations")
        graph.add_edge("generate_citations", "finalize_output")
        graph.add_edge("finalize_output", END)
        
        # Ponto de entrada
        graph.set_entry_point("analyze_request")
        
        return graph.compile()
    
    async def _analyze_request(self, state: WorkflowState) -> WorkflowState:
        """Analisa a solicitação inicial"""
        logger.info("🔍 Analisando solicitação")
        
        # Extrai informações da solicitação
        if state.get("messages"):
            last_message = state["messages"][-1]
            task = last_message.get("content", "")
            
            state["current_task"] = task
            state["context"] = {
                "tema": self._extract_theme(task),
                "tipo_documento": self._extract_document_type(task),
                "requisitos": self._extract_requirements(task)
            }
            
            state["messages"].append({
                "role": "system",
                "content": f"Análise da solicitação concluída. Tema: {state['context']['tema']}"
            })
        
        return state
    
    async def _validate_external_context(self, state: WorkflowState) -> WorkflowState:
        """Valida contexto externo se fornecido"""
        logger.info("🔍 Validando contexto externo")
        
        external_docs = state.get("external_docs")
        
        if external_docs:
            # Adaptar para usar o contexto do GraphState
            temp_state = {
                "config": {"context_docs_external": external_docs}
            }
            
            validation_result = await context_validator_node(temp_state)
            
            state["context_validation_result"] = validation_result.get("validation_result")
            
            if validation_result.get("error_messages"):
                state["messages"].extend([
                    {"role": "system", "content": f"Erro na validação: {err}"}
                    for err in validation_result["error_messages"]
                ])
            else:
                state["messages"].append({
                    "role": "system",
                    "content": f"Contexto externo validado: {len(external_docs)} documentos"
                })
        
        return state
    
    async def _execute_rag(self, state: WorkflowState) -> WorkflowState:
        """Executa busca RAG com contexto externo"""
        logger.info("🔍 Executando busca RAG")
        
        # Adaptar para usar o contexto do GraphState
        temp_state = {
            "initial_query": state["current_task"],
            "tenant_id": "default_tenant",
            "config": {
                "context_docs_external": state.get("external_docs"),
                "use_internal_rag": True,
                "rag_config": {
                    "k_total": 20,
                    "enable_personalization": True
                }
            }
        }
        
        rag_result = await rag_node(temp_state)
        
        # Transferir resultados para o estado do workflow
        state["rag_docs"] = rag_result.get("rag_docs", [])
        state["context_metadata"] = rag_result.get("context_metadata", {})
        state["external_docs_used"] = rag_result.get("external_docs_used", [])
        
        # Adicionar mensagens de log
        if rag_result.get("supervisor_notes"):
            state["messages"].extend([
                {"role": "system", "content": note}
                for note in rag_result["supervisor_notes"]
            ])
        
        return state
    
    async def _search_jurisprudence(self, state: WorkflowState) -> WorkflowState:
        """Busca jurisprudência relevante"""
        logger.info("⚖️ Buscando jurisprudência")
        
        tema = state["context"].get("tema", "")
        
        # Usa a ferramenta de busca de jurisprudência
        result = await self.registry.execute_tool(
            "buscar_jurisprudencia",
            tema=tema,
            tribunal="STJ",
            limite=3
        )
        
        if result.success:
            state["tool_results"]["jurisprudencia"] = result.data
            state["messages"].append({
                "role": "system",
                "content": f"Encontrados {len(result.data)} precedentes jurisprudenciais relevantes"
            })
        else:
            logger.error(f"Erro na busca de jurisprudência: {result.error}")
        
        return state
    
    async def _search_documents(self, state: WorkflowState) -> WorkflowState:
        """Busca documentos na base de conhecimento"""
        logger.info("📄 Buscando documentos")
        
        tema = state["context"].get("tema", "")
        
        # Usa a ferramenta RAG
        result = await self.registry.execute_tool(
            "buscar_rag",
            query=tema,
            tenant_id="default_tenant",
            limite=5
        )
        
        if result.success:
            state["tool_results"]["documentos"] = result.data
            state["documents"] = result.data
            state["messages"].append({
                "role": "system",
                "content": f"Encontrados {len(result.data)} documentos relevantes na base de conhecimento"
            })
        else:
            logger.error(f"Erro na busca de documentos: {result.error}")
        
        return state
    
    async def _analyze_documents(self, state: WorkflowState) -> WorkflowState:
        """Analisa documentos encontrados"""
        logger.info("📊 Analisando documentos")
        
        # Analisa cada documento encontrado
        for doc in state.get("documents", []):
            result = await self.registry.execute_tool(
                "analisar_documento",
                documento_id=doc["id"],
                tenant_id="default_tenant",
                aspectos=["clausulas", "fundamentacao", "estrutura"]
            )
            
            if result.success:
                doc["analise"] = result.data
                state["messages"].append({
                    "role": "system",
                    "content": f"Documento {doc['id']} analisado. Score: {result.data['score_qualidade']:.2f}"
                })
        
        return state
    
    async def _generate_content(self, state: WorkflowState) -> WorkflowState:
        """Gera conteúdo baseado nas informações coletadas"""
        logger.info("✍️ Gerando conteúdo")
        
        # Simula geração de conteúdo baseado nos dados coletados
        jurisprudencia = state["tool_results"].get("jurisprudencia", [])
        documentos = state["tool_results"].get("documentos", [])
        
        content = self._build_content(
            tema=state["context"]["tema"],
            tipo_documento=state["context"]["tipo_documento"],
            jurisprudencia=jurisprudencia,
            documentos=documentos
        )
        
        state["final_output"] = content
        state["messages"].append({
            "role": "assistant",
            "content": f"Conteúdo gerado com {len(content)} caracteres"
        })
        
        return state
    
    async def _check_quality(self, state: WorkflowState) -> WorkflowState:
        """Verifica qualidade do conteúdo gerado"""
        logger.info("✅ Verificando qualidade")
        
        content = state.get("final_output", "")
        tipo_documento = state["context"].get("tipo_documento", "parecer")
        
        # Usa a ferramenta de verificação de qualidade
        result = await self.registry.execute_tool(
            "verificar_qualidade",
            texto=content,
            tipo_documento=tipo_documento,
            criterios=["estrutura", "fundamentacao", "clareza", "completude"]
        )
        
        if result.success:
            state["quality_score"] = result.data["score_geral"]
            state["tool_results"]["qualidade"] = result.data
            
            # Se qualidade baixa, pode regenerar ou sugerir melhorias
            if result.data["score_geral"] < 0.7:
                state["messages"].append({
                    "role": "system",
                    "content": f"Qualidade baixa detectada (score: {result.data['score_geral']:.2f}). Sugestões: {result.data['sugestoes_melhoria']}"
                })
            else:
                state["messages"].append({
                    "role": "system",
                    "content": f"Qualidade aprovada (score: {result.data['score_geral']:.2f})"
                })
        
        return state
    
    async def _generate_citations(self, state: WorkflowState) -> WorkflowState:
        """Gera citações para as fontes utilizadas"""
        logger.info("📚 Gerando citações")
        
        citations = []
        
        # Cita jurisprudência
        for juris in state["tool_results"].get("jurisprudencia", []):
            result = await self.registry.execute_tool(
                "gerar_citacao",
                tipo_fonte="jurisprudencia",
                dados_fonte={
                    "tribunal": juris["tribunal"],
                    "numero_processo": juris["numero_processo"],
                    "relator": juris["relator"],
                    "data_julgamento": juris["data_julgamento"]
                },
                formato="completo"
            )
            
            if result.success:
                citations.append(result.data["citacao_formatada"])
        
        # Cita documentos
        for doc in state.get("documents", []):
            result = await self.registry.execute_tool(
                "gerar_citacao",
                tipo_fonte="documento",
                dados_fonte={
                    "titulo": doc["titulo"],
                    "autor": doc["metadata"].get("autor", ""),
                    "data": doc["data_criacao"]
                },
                formato="completo"
            )
            
            if result.success:
                citations.append(result.data["citacao_formatada"])
        
        state["citations"] = citations
        state["messages"].append({
            "role": "system",
            "content": f"Geradas {len(citations)} citações"
        })
        
        return state
    
    async def _finalize_output(self, state: WorkflowState) -> WorkflowState:
        """Finaliza o output com citations e metadados"""
        logger.info("🎯 Finalizando output")
        
        final_content = state.get("final_output", "")
        citations = state.get("citations", [])
        quality_score = state.get("quality_score", 0.0)
        
        # Adiciona citações ao final
        if citations:
            final_content += "\n\n**REFERÊNCIAS:**\n"
            for i, citation in enumerate(citations, 1):
                final_content += f"{i}. {citation}\n"
        
        # Adiciona metadados de qualidade
        final_content += f"\n\n**METADADOS:**\n"
        final_content += f"- Score de Qualidade: {quality_score:.2f}\n"
        final_content += f"- Jurisprudência consultada: {len(state['tool_results'].get('jurisprudencia', []))}\n"
        final_content += f"- Documentos analisados: {len(state.get('documents', []))}\n"
        
        state["final_output"] = final_content
        state["messages"].append({
            "role": "assistant",
            "content": "Documento finalizado com citações e metadados"
        })
        
        return state
    
    def _extract_theme(self, task: str) -> str:
        """Extrai tema principal da solicitação"""
        # Lógica simplificada de extração de tema
        if "responsabilidade civil" in task.lower():
            return "responsabilidade civil"
        elif "contrato" in task.lower():
            return "contratos"
        elif "consumidor" in task.lower():
            return "direito do consumidor"
        else:
            return "direito geral"
    
    def _extract_document_type(self, task: str) -> str:
        """Extrai tipo de documento da solicitação"""
        if "petição" in task.lower():
            return "peticao"
        elif "contrato" in task.lower():
            return "contrato"
        elif "parecer" in task.lower():
            return "parecer"
        else:
            return "documento"
    
    def _extract_requirements(self, task: str) -> List[str]:
        """Extrai requisitos específicos"""
        requirements = []
        if "jurisprudência" in task.lower():
            requirements.append("incluir_jurisprudencia")
        if "fundamentação" in task.lower():
            requirements.append("fundamentacao_detalhada")
        if "citações" in task.lower():
            requirements.append("citacoes_completas")
        return requirements
    
    def _build_content(self, tema: str, tipo_documento: str, jurisprudencia: List[Dict], documentos: List[Dict]) -> str:
        """Constrói o conteúdo do documento"""
        content = f"""
{tipo_documento.upper()} - {tema.upper()}

FUNDAMENTAÇÃO LEGAL:

Com base na análise jurisprudencial e documental realizada, apresentamos os seguintes fundamentos:

"""
        
        # Adiciona jurisprudência
        if jurisprudencia:
            content += "JURISPRUDÊNCIA:\n\n"
            for juris in jurisprudencia:
                content += f"- {juris['tribunal']}: {juris['ementa']}\n"
                content += f"  Tese: {juris['tese_principal']}\n\n"
        
        # Adiciona análise de documentos
        if documentos:
            content += "ANÁLISE DOCUMENTAL:\n\n"
            for doc in documentos:
                content += f"- {doc['titulo']}: {doc['trecho_relevante']}\n\n"
        
        content += """
CONCLUSÃO:

Diante do exposto e com base nos precedentes jurisprudenciais e documentação analisada, 
conclui-se que os fundamentos apresentados sustentam a tese defendida.

Termos em que se apresenta o presente documento.
"""
        
        return content
    
    async def process_request(self, request: str, external_docs: Optional[List[ExternalDoc]] = None) -> Dict[str, Any]:
        """Processa uma solicitação usando o workflow completo"""
        initial_state: WorkflowState = {
            "messages": [{"role": "user", "content": request}],
            "current_task": "",
            "context": {},
            "tool_results": {},
            "quality_score": 0.0,
            "documents": [],
            "citations": [],
            "final_output": "",
            
            # Campos para contexto externo
            "external_docs": external_docs,
            "external_context_summary": None,
            "context_validation_result": None,
            "rag_docs": [],
            "context_metadata": {},
            "external_docs_used": []
        }
        
        # Executa o workflow
        final_state = await self.graph.ainvoke(initial_state)
        
        return {
            "content": final_state["final_output"],
            "quality_score": final_state["quality_score"],
            "citations": final_state["citations"],
            "external_context_summary": final_state.get("external_context_summary"),
            "external_docs_used": final_state.get("external_docs_used", []),
            "context_metadata": final_state.get("context_metadata", {}),
            "metadata": {
                "jurisprudencia_consultada": len(final_state["tool_results"].get("jurisprudencia", [])),
                "documentos_analisados": len(final_state.get("documents", [])),
                "rag_docs_total": len(final_state.get("rag_docs", [])),
                "external_docs_provided": len(external_docs) if external_docs else 0,
                "messages": final_state["messages"]
            }
        }

# Exemplo de uso
async def example_usage():
    """Exemplo de uso do workflow integrado"""
    workflow = HarveyToolsWorkflow()
    
    request = """
    Preciso de um parecer jurídico sobre responsabilidade civil do Estado por danos causados 
    por obras públicas. Inclua jurisprudência relevante e fundamentação legal completa.
    """
    
    result = await workflow.process_request(request)
    
    print("📄 RESULTADO DO WORKFLOW:")
    print("="*50)
    print(f"Qualidade: {result['quality_score']:.2f}")
    print(f"Citações: {len(result['citations'])}")
    print(f"Jurisprudência: {result['metadata']['jurisprudencia_consultada']}")
    print(f"Documentos: {result['metadata']['documentos_analisados']}")
    print("\nConteúdo:")
    print(result['content'][:500] + "..." if len(result['content']) > 500 else result['content'])

if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
