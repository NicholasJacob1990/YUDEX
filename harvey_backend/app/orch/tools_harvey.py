"""
Ferramentas Jurídicas para Sistema Harvey - Implementação Onda 2
Sistema completo de ferramentas para inteligência ativa
"""

from typing import Dict, Any, List, Optional
from app.orch.tools import BaseTool, ToolType, ToolResult, ToolSchema
import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class JurisprudenceSearchTool(BaseTool):
    """Ferramenta para busca de jurisprudência em tribunais superiores"""
    
    def __init__(self):
        schema = ToolSchema(
            name="buscar_jurisprudencia",
            description="Busca jurisprudência recente nos tribunais superiores brasileiros sobre um tema específico",
            tool_type=ToolType.JURISPRUDENCE,
            parameters={
                "tema": {
                    "type": "string",
                    "description": "Tema ou assunto para busca de jurisprudência"
                },
                "tribunal": {
                    "type": "string", 
                    "description": "Tribunal para busca (STJ, STF, etc.)",
                    "default": "STJ"
                },
                "limite": {
                    "type": "integer",
                    "description": "Número máximo de resultados",
                    "default": 3
                }
            },
            required_params=["tema"]
        )
        super().__init__(schema)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Executa busca de jurisprudência"""
        try:
            tema = kwargs.get("tema")
            tribunal = kwargs.get("tribunal", "STJ")
            limite = kwargs.get("limite", 3)
            
            logger.info(f"Buscando jurisprudência: tema='{tema}', tribunal='{tribunal}'")
            
            # Simula busca de jurisprudência
            await asyncio.sleep(0.1)
            
            resultados = [
                {
                    "id": f"{tribunal}_001",
                    "tribunal": tribunal,
                    "numero_processo": "123456-78.2023.8.00.0000",
                    "relator": "Min. João Silva",
                    "data_julgamento": "2023-06-15",
                    "ementa": f"Decisão sobre {tema}. Precedente importante para casos similares.",
                    "tese_principal": f"Em casos de {tema}, aplica-se o entendimento consolidado...",
                    "tags": ["civil", "responsabilidade", "estado"],
                    "relevancia": 0.95
                },
                {
                    "id": f"{tribunal}_002", 
                    "tribunal": tribunal,
                    "numero_processo": "654321-12.2023.8.00.0000",
                    "relator": "Min. Maria Santos",
                    "data_julgamento": "2023-08-22",
                    "ementa": f"Análise aprofundada sobre {tema} com precedentes atualizados.",
                    "tese_principal": f"Consolidação do entendimento sobre {tema}...",
                    "tags": ["administrativo", "jurisprudencia"],
                    "relevancia": 0.88
                }
            ]
            
            return ToolResult(
                success=True,
                data=resultados,
                metadata={
                    "tema_pesquisado": tema,
                    "tribunal": tribunal,
                    "total_encontrados": len(resultados)
                }
            )
            
        except Exception as e:
            logger.error(f"Erro na busca de jurisprudência: {e}")
            return ToolResult(
                success=False,
                error=f"Erro na busca: {str(e)}"
            )

class DocumentAnalyzerTool(BaseTool):
    """Ferramenta para análise detalhada de documentos"""
    
    def __init__(self):
        schema = ToolSchema(
            name="analisar_documento",
            description="Analisa um documento jurídico específico extraindo informações relevantes",
            tool_type=ToolType.DOCUMENT_RETRIEVAL,
            parameters={
                "documento_id": {
                    "type": "string",
                    "description": "ID do documento a ser analisado"
                },
                "tenant_id": {
                    "type": "string",
                    "description": "ID do tenant/cliente"
                },
                "aspectos": {
                    "type": "array",
                    "description": "Aspectos específicos para análise",
                    "items": {"type": "string"},
                    "default": ["clausulas", "prazos", "responsabilidades", "valores"]
                }
            },
            required_params=["documento_id", "tenant_id"]
        )
        super().__init__(schema)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Executa análise do documento"""
        try:
            documento_id = kwargs.get("documento_id")
            tenant_id = kwargs.get("tenant_id")
            aspectos = kwargs.get("aspectos", ["clausulas", "prazos", "responsabilidades", "valores"])
                
            logger.info(f"Analisando documento: {documento_id}")
            
            # Simula análise de documento
            await asyncio.sleep(0.2)
            
            analise = {
                "documento_id": documento_id,
                "tipo_documento": "contrato",
                "analise_por_aspecto": {
                    "clausulas": {
                        "total_clausulas": 15,
                        "clausulas_criticas": ["4.1", "7.2", "12.3"],
                        "resumo": "Documento possui cláusulas padrão com algumas específicas para o caso"
                    },
                    "prazos": {
                        "prazo_principal": "24 meses",
                        "prazos_intermediarios": ["60 dias", "90 dias"],
                        "resumo": "Prazos compatíveis com a legislação vigente"
                    },
                    "responsabilidades": {
                        "parte_a": ["Prestação do serviço", "Manutenção de sigilo"],
                        "parte_b": ["Pagamento", "Fornecimento de informações"],
                        "resumo": "Distribuição equilibrada de responsabilidades"
                    },
                    "valores": {
                        "valor_principal": "R$ 250.000,00",
                        "forma_pagamento": "Parcelas mensais",
                        "reajuste": "IPCA anual",
                        "resumo": "Valores e condições financeiras definidas"
                    }
                },
                "pontos_atencao": [
                    "Cláusula 4.1 pode gerar interpretação dúbia",
                    "Prazo de 60 dias pode ser apertado para algumas atividades"
                ],
                "score_qualidade": 0.82,
                "recomendacoes": [
                    "Revisar redação da cláusula 4.1",
                    "Considerar prazo adicional de 15 dias para atividade X"
                ]
            }
            
            return ToolResult(
                success=True,
                data=analise,
                metadata={
                    "documento_id": documento_id,
                    "aspectos_analisados": aspectos,
                    "tenant_id": tenant_id
                }
            )
            
        except Exception as e:
            logger.error(f"Erro na análise do documento: {e}")
            return ToolResult(
                success=False,
                error=f"Erro na análise: {str(e)}"
            )

class RAGSearchTool(BaseTool):
    """Ferramenta para busca RAG especializada"""
    
    def __init__(self):
        schema = ToolSchema(
            name="buscar_rag",
            description="Busca documentos relevantes na base de conhecimento usando RAG",
            tool_type=ToolType.RAG_SEARCH,
            parameters={
                "query": {
                    "type": "string",
                    "description": "Consulta para busca RAG"
                },
                "tenant_id": {
                    "type": "string",
                    "description": "ID do tenant/cliente"
                },
                "limite": {
                    "type": "integer",
                    "description": "Número máximo de resultados",
                    "default": 5
                }
            },
            required_params=["query", "tenant_id"]
        )
        super().__init__(schema)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Executa busca RAG"""
        try:
            query = kwargs.get("query")
            tenant_id = kwargs.get("tenant_id")
            limite = kwargs.get("limite", 5)
            
            logger.info(f"Executando busca RAG: query='{query}', tenant='{tenant_id}'")
            
            # Simula busca RAG
            await asyncio.sleep(0.15)
            
            resultados = [
                {
                    "id": "DOC_001",
                    "titulo": "Contrato de Desenvolvimento de Software",
                    "tipo": "contrato",
                    "data_criacao": "2023-05-15",
                    "score_relevancia": 0.92,
                    "trecho_relevante": "Cláusulas de SLA definindo disponibilidade mínima de 99.5% e tempo de resposta máximo de 2 segundos.",
                    "metadata": {
                        "autor": "Departamento Jurídico",
                        "tags": ["software", "sla", "desenvolvimento"],
                        "paginas": [5, 6, 7]
                    }
                },
                {
                    "id": "DOC_002",
                    "titulo": "Parecer sobre Contratos de TI",
                    "tipo": "parecer",
                    "data_criacao": "2023-07-22",
                    "score_relevancia": 0.85,
                    "trecho_relevante": "Análise de cláusulas típicas em contratos de software, incluindo SLA e responsabilidades técnicas.",
                    "metadata": {
                        "autor": "Dr. Carlos Pereira",
                        "tags": ["ti", "contratos", "analise"],
                        "paginas": [12, 13]
                    }
                }
            ]
            
            return ToolResult(
                success=True,
                data=resultados,
                metadata={
                    "query": query,
                    "tenant_id": tenant_id,
                    "total_encontrados": len(resultados)
                }
            )
            
        except Exception as e:
            logger.error(f"Erro na busca RAG: {e}")
            return ToolResult(
                success=False,
                error=f"Erro na busca: {str(e)}"
            )

class CitationGeneratorTool(BaseTool):
    """Ferramenta para geração de citações e referências jurídicas"""
    
    def __init__(self):
        schema = ToolSchema(
            name="gerar_citacao",
            description="Gera citações e referências jurídicas no formato ABNT",
            tool_type=ToolType.FORMATTING,
            parameters={
                "tipo_fonte": {
                    "type": "string",
                    "description": "Tipo de fonte (lei, jurisprudencia, doutrina, etc.)"
                },
                "dados_fonte": {
                    "type": "object",
                    "description": "Dados da fonte para citação"
                },
                "formato": {
                    "type": "string",
                    "description": "Formato da citação (completo, abreviado)",
                    "default": "completo"
                }
            },
            required_params=["tipo_fonte", "dados_fonte"]
        )
        super().__init__(schema)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Executa geração de citação"""
        try:
            tipo_fonte = kwargs.get("tipo_fonte")
            dados_fonte = kwargs.get("dados_fonte", {})
            formato = kwargs.get("formato", "completo")
            
            logger.info(f"Gerando citação: tipo='{tipo_fonte}', formato='{formato}'")
            
            # Simula geração de citação
            await asyncio.sleep(0.05)
            
            if tipo_fonte == "lei":
                if formato == "completo":
                    citacao = f"BRASIL. Lei nº {dados_fonte.get('numero', '')}, de {dados_fonte.get('ano', '')}. {dados_fonte.get('titulo', '')}. Disponível em: [URL]. Acesso em: {datetime.now().strftime('%d %b. %Y')}."
                else:
                    citacao = f"Lei {dados_fonte.get('numero', '')}/{dados_fonte.get('ano', '')}"
            elif tipo_fonte == "jurisprudencia":
                if formato == "completo":
                    citacao = f"{dados_fonte.get('tribunal', '')}. {dados_fonte.get('numero_processo', '')}. Relator: {dados_fonte.get('relator', '')}. {dados_fonte.get('data_julgamento', '')}."
                else:
                    citacao = f"{dados_fonte.get('tribunal', '')} {dados_fonte.get('numero_processo', '')}"
            else:
                citacao = f"Citação para {tipo_fonte} - {dados_fonte}"
            
            resultado = {
                "citacao_formatada": citacao,
                "tipo_fonte": tipo_fonte,
                "formato": formato,
                "elementos_utilizados": list(dados_fonte.keys())
            }
            
            return ToolResult(
                success=True,
                data=resultado,
                metadata={
                    "tipo_fonte": tipo_fonte,
                    "formato": formato
                }
            )
            
        except Exception as e:
            logger.error(f"Erro na geração de citação: {e}")
            return ToolResult(
                success=False,
                error=f"Erro na geração: {str(e)}"
            )

class QualityCheckerTool(BaseTool):
    """Ferramenta para verificação de qualidade de documentos jurídicos"""
    
    def __init__(self):
        schema = ToolSchema(
            name="verificar_qualidade",
            description="Verifica a qualidade e completude de documentos jurídicos",
            tool_type=ToolType.VALIDATION,
            parameters={
                "texto": {
                    "type": "string",
                    "description": "Texto do documento para verificação"
                },
                "tipo_documento": {
                    "type": "string",
                    "description": "Tipo de documento (peticao, contrato, parecer, etc.)"
                },
                "criterios": {
                    "type": "array",
                    "description": "Critérios específicos para verificação",
                    "items": {"type": "string"},
                    "default": ["estrutura", "fundamentacao", "clareza", "completude"]
                }
            },
            required_params=["texto", "tipo_documento"]
        )
        super().__init__(schema)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Executa verificação de qualidade"""
        try:
            texto = kwargs.get("texto", "")
            tipo_documento = kwargs.get("tipo_documento", "")
            criterios = kwargs.get("criterios", ["estrutura", "fundamentacao", "clareza", "completude"])
            
            # Validação básica
            if not texto:
                return ToolResult(
                    success=False,
                    error="Texto não pode ser vazio"
                )
                
            logger.info(f"Verificando qualidade: tipo='{tipo_documento}', critérios={criterios}")
            
            # Simula verificação de qualidade
            await asyncio.sleep(0.3)
            
            scores = {}
            problemas = []
            sugestoes = []
            
            for criterio in criterios:
                if criterio == "estrutura":
                    score = 0.85
                    if "Excelentíssimo" not in texto:
                        problemas.append("Vocativo formal não encontrado")
                        score -= 0.1
                    if "Termos em que" not in texto:
                        problemas.append("Fórmula de encerramento não encontrada")
                        score -= 0.1
                    scores[criterio] = max(0, score)
                    
                elif criterio == "fundamentacao":
                    score = 0.80
                    if "art." not in texto.lower() and "artigo" not in texto.lower():
                        problemas.append("Nenhuma fundamentação legal encontrada")
                        score -= 0.2
                    if "jurisprudência" not in texto.lower():
                        sugestoes.append("Considerar adicionar jurisprudência")
                        score -= 0.1
                    scores[criterio] = max(0, score)
                    
                elif criterio == "clareza":
                    score = 0.75
                    palavras = len(texto.split())
                    if palavras > 1000:
                        problemas.append("Texto muito extenso, pode prejudicar clareza")
                        score -= 0.15
                    scores[criterio] = max(0, score)
                    
                elif criterio == "completude":
                    score = 0.90
                    if tipo_documento == "peticao":
                        if "PEDIDO" not in texto.upper():
                            problemas.append("Seção de pedido não encontrada")
                            score -= 0.2
                    scores[criterio] = max(0, score)
            
            score_geral = sum(scores.values()) / len(scores) if scores else 0
            
            verificacao = {
                "score_geral": score_geral,
                "scores_por_criterio": scores,
                "problemas_encontrados": problemas,
                "sugestoes_melhoria": sugestoes,
                "aprovado": score_geral >= 0.7,
                "resumo": f"Documento {'aprovado' if score_geral >= 0.7 else 'reprovado'} com score {score_geral:.2f}"
            }
            
            return ToolResult(
                success=True,
                data=verificacao,
                metadata={
                    "tipo_documento": tipo_documento,
                    "criterios_verificados": criterios,
                    "tamanho_texto": len(texto)
                }
            )
            
        except Exception as e:
            logger.error(f"Erro na verificação de qualidade: {e}")
            return ToolResult(
                success=False,
                error=f"Erro na verificação: {str(e)}"
            )

# Função para inicializar todas as ferramentas
def get_harvey_tools() -> List[BaseTool]:
    """Retorna todas as ferramentas Harvey disponíveis"""
    return [
        JurisprudenceSearchTool(),
        DocumentAnalyzerTool(),
        RAGSearchTool(),
        CitationGeneratorTool(),
        QualityCheckerTool()
    ]

# Função para registrar todas as ferramentas
def register_harvey_tools(registry):
    """Registra todas as ferramentas Harvey no registry"""
    for tool in get_harvey_tools():
        registry.register_tool(tool)
        print(f"✅ Ferramenta registrada: {tool.name}")
    
    print(f"🎯 Total de {len(get_harvey_tools())} ferramentas Harvey registradas!")
