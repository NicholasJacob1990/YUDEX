"""
Agents - Nós do grafo LangGraph
Especialistas que executam tarefas específicas no grafo dinâmico
"""

from typing import Dict, Any
from .state import GraphState

# --- Stubs que representam suas funções do core ---
# TODO: Substitua estes stubs por chamadas reais às suas funções em app/core/

async def run_analysis_logic(docs: list, query: str) -> dict:
    """Simula análise macro usando LLM"""
    print("--- (Simulação) Rodando Análise Macro (Gemini/Claude)... ---")
    # Exemplo de chamada: return await app.core.analyzer.run(docs, query)
    return {
        "tese_principal": "O limite de 25% é a regra geral, mas exceções são possíveis.",
        "lacunas": ["jurisprudência TCU 2024"],
        "abordagem_recomendada": "Análise constitucional e administrativa",
        "complexidade": "média"
    }

async def run_drafting_logic(analysis: dict, config: dict) -> str:
    """Simula redação de documento jurídico"""
    print("--- (Simulação) Rodando Redação (GPT-4o)... ---")
    # Exemplo: return await app.core.drafter.run(analysis, config)
    return """## Parecer Jurídico

### I. Dos Fatos
Trata-se de consulta acerca da aplicação do limite de 25% em contratos administrativos.

### II. Análise Jurídica
Conforme a análise realizada, o limite de 25% constitui regra geral estabelecida no art. 65 da Lei 8.666/93.

### III. Fundamentação
[[BUSCAR_JURIS_TCU]] - Necessário complementar com jurisprudência do TCU.

### IV. Conclusão
O limite é aplicável, ressalvadas as exceções legais."""

async def run_critic_logic(draft: str, analysis: dict) -> dict:
    """Simula crítica e revisão do documento"""
    print("--- (Simulação) Rodando Crítica (Claude)... ---")
    # Exemplo: return await app.core.critic.run(draft, analysis)
    
    # Verifica se há lacunas a serem preenchidas
    needs_research = "[[BUSCAR_JURIS_TCU]]" in draft
    
    revised_text = draft
    if needs_research:
        # Simula preenchimento da lacuna
        revised_text = draft.replace(
            "[[BUSCAR_JURIS_TCU]]", 
            "Conforme entendimento do TCU (Acórdão 1234/2024), o limite pode ser flexibilizado em casos excepcionais."
        )
    
    return {
        "report": "O rascunho está bem estruturado, mas necessitava de jurisprudência específica do TCU.",
        "revised_text": revised_text,
        "needs_research": needs_research,
        "quality_score": 0.85,
        "suggestions": ["Adicionar mais fundamentação doutrinária", "Detalhar casos de exceção"]
    }

# --- Nós do Grafo LangGraph ---

async def analyzer_node(state: GraphState) -> Dict[str, Any]:
    """Nó que executa a análise macro dos documentos."""
    print("-> Entrando no nó: Analyzer")
    
    # Executa análise usando os documentos RAG
    rag_docs = state.get("rag_docs", [])
    query = state.get("initial_query", "")
    
    # Contexto externo fornecido pelo cliente
    external_docs_used = state.get("external_docs_used", [])
    context_metadata = state.get("context_metadata", {})
    
    analysis_result = await run_analysis_logic(rag_docs, query)
    
    # Enriquecer análise com informações de contexto externo
    if external_docs_used:
        external_context_summary = {
            "external_docs_count": len(external_docs_used),
            "external_docs_ids": [doc.get("src_id") for doc in external_docs_used],
            "average_external_score": sum(doc.get("score", 0) for doc in external_docs_used) / len(external_docs_used),
            "context_type": context_metadata.get("context_type", "hybrid")
        }
        analysis_result["external_context"] = external_context_summary
    
    # Atualiza notas do supervisor
    notes = state.get("supervisor_notes", [])
    notes.append(f"Análise macro concluída. Complexidade: {analysis_result.get('complexidade', 'indefinida')}")
    
    if external_docs_used:
        notes.append(f"Contexto externo considerado: {len(external_docs_used)} documentos")
    
    return {
        "analysis": analysis_result,
        "supervisor_notes": notes
    }

async def drafter_node(state: GraphState) -> Dict[str, Any]:
    """Nó que gera o rascunho inicial do documento jurídico."""
    print("-> Entrando no nó: Drafter")
    
    # Obtém análise e configurações
    analysis = state.get("analysis", {})
    config = state.get("config", {})
    
    # Gera o draft
    draft = await run_drafting_logic(analysis, config)
    
    # Atualiza notas
    notes = state.get("supervisor_notes", [])
    notes.append(f"Rascunho inicial gerado. Tamanho: {len(draft)} caracteres")
    
    return {
        "draft_markdown": draft,
        "supervisor_notes": notes
    }

async def critic_node(state: GraphState) -> Dict[str, Any]:
    """Nó que revisa e critica o rascunho."""
    print("-> Entrando no nó: Critic")
    
    # Obtém draft para revisão
    draft_to_review = state.get("draft_markdown", "")
    analysis = state.get("analysis", {})
    
    # Executa crítica
    critic_result = await run_critic_logic(draft_to_review, analysis)
    
    # Atualiza relatórios de crítica
    reports = state.get("critic_reports", [])
    reports.append(critic_result["report"])
    
    # Atualiza notas
    notes = state.get("supervisor_notes", [])
    notes.append(f"Ciclo de crítica concluído. Score: {critic_result.get('quality_score', 0)}")
    
    return {
        "critic_latest_markdown": critic_result["revised_text"],
        "critic_reports": reports,
        "supervisor_notes": notes
    }

async def formatter_node(state: GraphState) -> Dict[str, Any]:
    """Nó que aplica formatação ABNT final."""
    print("-> Entrando no nó: Formatter")
    
    # Obtém texto final para formatação
    text_to_format = state.get("critic_latest_markdown") or state.get("draft_markdown", "")
    
    # Simula formatação ABNT
    formatted_text = f"""# PARECER JURÍDICO

{text_to_format}

---
*Documento elaborado conforme normas ABNT*
*Data: {__import__('datetime').datetime.now().strftime('%d/%m/%Y')}*
"""
    
    # Atualiza notas
    notes = state.get("supervisor_notes", [])
    notes.append("Formatação ABNT aplicada.")
    
    return {
        "final_text": formatted_text,
        "supervisor_notes": notes
    }

async def researcher_node(state: GraphState) -> Dict[str, Any]:
    """Nó que busca informações adicionais quando necessário."""
    print("-> Entrando no nó: Researcher")
    
    # Simula busca de informações adicionais
    query = state.get("initial_query", "")
    
    # Simula resultados de pesquisa
    additional_docs = [
        {
            "source": "TCU Acórdão 1234/2024",
            "content": "Jurisprudência relevante sobre limites contratuais",
            "relevance": 0.9
        },
        {
            "source": "Doutrina - Maria Silva",
            "content": "Análise doutrinária sobre exceções legais",
            "relevance": 0.8
        }
    ]
    
    # Adiciona aos documentos RAG existentes
    current_docs = state.get("rag_docs", [])
    updated_docs = current_docs + additional_docs
    
    # Atualiza notas
    notes = state.get("supervisor_notes", [])
    notes.append(f"Pesquisa adicional concluída. Encontrados {len(additional_docs)} documentos relevantes.")
    
    return {
        "rag_docs": updated_docs,
        "supervisor_notes": notes
    }
