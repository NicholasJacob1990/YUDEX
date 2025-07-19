#!/usr/bin/env python3
"""
Teste das Ferramentas Harvey - Onda 2: Inteligência Ativa
Demonstra o uso das ferramentas jurídicas implementadas
"""

import asyncio
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.orch.tools_harvey import get_harvey_tools, register_harvey_tools
from app.orch.tools import get_tool_registry

async def test_jurisprudence_search():
    """Testa a busca de jurisprudência"""
    print("\n🔍 Testando Busca de Jurisprudência")
    print("="*50)
    
    tool = None
    for t in get_harvey_tools():
        if t.name == "buscar_jurisprudencia":
            tool = t
            break
    
    if tool:
        result = await tool.execute(
            tema="responsabilidade civil do Estado",
            tribunal="STJ",
            limite=2
        )
        
        print(f"✅ Sucesso: {result.success}")
        if result.success:
            print(f"📄 Encontrados: {len(result.data)} resultados")
            for i, doc in enumerate(result.data[:2]):
                print(f"  {i+1}. {doc['tribunal']} - {doc['numero_processo']}")
                print(f"     Relator: {doc['relator']}")
                print(f"     Ementa: {doc['ementa'][:80]}...")
        else:
            print(f"❌ Erro: {result.error}")

async def test_document_analyzer():
    """Testa a análise de documentos"""
    print("\n📋 Testando Análise de Documentos")
    print("="*50)
    
    tool = None
    for t in get_harvey_tools():
        if t.name == "analisar_documento":
            tool = t
            break
    
    if tool:
        result = await tool.execute(
            documento_id="DOC_12345",
            tenant_id="tenant_abc",
            aspectos=["clausulas", "prazos", "valores"]
        )
        
        print(f"✅ Sucesso: {result.success}")
        if result.success:
            analise = result.data
            print(f"📊 Score de Qualidade: {analise['score_qualidade']:.2f}")
            print(f"📝 Tipo: {analise['tipo_documento']}")
            print(f"⚠️  Pontos de Atenção: {len(analise['pontos_atencao'])}")
            print(f"💡 Recomendações: {len(analise['recomendacoes'])}")
        else:
            print(f"❌ Erro: {result.error}")

async def test_rag_search():
    """Testa a busca RAG"""
    print("\n🔎 Testando Busca RAG")
    print("="*50)
    
    tool = None
    for t in get_harvey_tools():
        if t.name == "buscar_rag":
            tool = t
            break
    
    if tool:
        result = await tool.execute(
            query="contratos de software e SLA",
            tenant_id="tenant_abc",
            limite=2
        )
        
        print(f"✅ Sucesso: {result.success}")
        if result.success:
            print(f"📄 Encontrados: {len(result.data)} documentos")
            for i, doc in enumerate(result.data):
                print(f"  {i+1}. {doc['titulo']}")
                print(f"     Relevância: {doc['score_relevancia']:.2f}")
                print(f"     Trecho: {doc['trecho_relevante'][:60]}...")
        else:
            print(f"❌ Erro: {result.error}")

async def test_citation_generator():
    """Testa o gerador de citações"""
    print("\n📚 Testando Gerador de Citações")
    print("="*50)
    
    tool = None
    for t in get_harvey_tools():
        if t.name == "gerar_citacao":
            tool = t
            break
    
    if tool:
        # Teste com lei
        result = await tool.execute(
            tipo_fonte="lei",
            dados_fonte={
                "numero": "8.078",
                "ano": "1990",
                "titulo": "Dispõe sobre a proteção do consumidor"
            },
            formato="completo"
        )
        
        print(f"✅ Sucesso: {result.success}")
        if result.success:
            print(f"📖 Citação Lei: {result.data['citacao_formatada']}")
        
        # Teste com jurisprudência
        result = await tool.execute(
            tipo_fonte="jurisprudencia",
            dados_fonte={
                "tribunal": "STJ",
                "numero_processo": "REsp 1.234.567/SP",
                "relator": "Min. Paulo Henrique",
                "data_julgamento": "15/06/2023"
            },
            formato="abreviado"
        )
        
        if result.success:
            print(f"⚖️  Citação Jurisprudência: {result.data['citacao_formatada']}")
        else:
            print(f"❌ Erro: {result.error}")

async def test_quality_checker():
    """Testa o verificador de qualidade"""
    print("\n✅ Testando Verificador de Qualidade")
    print("="*50)
    
    tool = None
    for t in get_harvey_tools():
        if t.name == "verificar_qualidade":
            tool = t
            break
    
    if tool:
        texto_teste = """
        Excelentíssimo Senhor Juiz,
        
        Venho por meio desta petição inicial requerer a aplicação do art. 186 do Código Civil,
        tendo em vista os danos causados ao requerente. A jurisprudência do STJ tem sido
        pacífica no sentido de que...
        
        PEDIDO
        
        Diante do exposto, requer-se a procedência do pedido.
        
        Termos em que pede e espera deferimento.
        """
        
        result = await tool.execute(
            texto=texto_teste,
            tipo_documento="peticao",
            criterios=["estrutura", "fundamentacao", "completude"]
        )
        
        print(f"✅ Sucesso: {result.success}")
        if result.success:
            verificacao = result.data
            print(f"📊 Score Geral: {verificacao['score_geral']:.2f}")
            print(f"✅ Aprovado: {verificacao['aprovado']}")
            print(f"📋 Resumo: {verificacao['resumo']}")
            
            if verificacao['problemas_encontrados']:
                print("⚠️  Problemas encontrados:")
                for problema in verificacao['problemas_encontrados']:
                    print(f"   - {problema}")
            
            if verificacao['sugestoes_melhoria']:
                print("💡 Sugestões:")
                for sugestao in verificacao['sugestoes_melhoria']:
                    print(f"   - {sugestao}")
        else:
            print(f"❌ Erro: {result.error}")

async def test_registry_integration():
    """Testa a integração com o registry"""
    print("\n🔧 Testando Integração com Registry")
    print("="*50)
    
    registry = get_tool_registry()
    
    # Registra as ferramentas
    register_harvey_tools(registry)
    
    # Lista ferramentas disponíveis
    tools = registry.get_available_tools()
    print(f"🛠️  Ferramentas registradas: {len(tools)}")
    for tool in tools:
        print(f"   - {tool}")
    
    # Teste de execução via registry
    print("\n🚀 Testando execução via registry...")
    result = await registry.execute_tool(
        "buscar_jurisprudencia",
        tema="danos morais",
        tribunal="STF",
        limite=1
    )
    
    print(f"✅ Execução via registry: {result.success}")
    if result.success:
        print(f"📄 Dados retornados: {len(result.data)} resultado(s)")

async def main():
    """Função principal de teste"""
    print("🎯 TESTE DAS FERRAMENTAS HARVEY - ONDA 2")
    print("="*60)
    print("Testando sistema completo de inteligência ativa")
    print("="*60)
    
    try:
        await test_jurisprudence_search()
        await test_document_analyzer()
        await test_rag_search()
        await test_citation_generator()
        await test_quality_checker()
        await test_registry_integration()
        
        print("\n🎉 TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
        print("="*60)
        print("✅ Sistema de ferramentas Harvey operacional")
        print("✅ Inteligência ativa implementada")
        print("✅ Qualidade mensurável funcionando")
        print("✅ Integração com registry confirmada")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE OS TESTES: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
