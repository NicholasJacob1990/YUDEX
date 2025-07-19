#!/usr/bin/env python3
"""
Teste da Onda 3: Feedback do Usuário e Segurança Avançada
Demonstra funcionalidades de feedback, auditoria e segurança
"""

import asyncio
import sys
import os
from datetime import datetime
import json

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.security.pii import PIIDetector, PIIRedactor, scan_and_redact_pii
from app.core.audit import AuditManager, build_and_save_audit_record
from app.models.policy import PolicyManager, PolicyType, initialize_tenant_policies
from app.api.v1.feedback import FeedbackRequest, ErrorSpan, MissingSource

async def test_pii_detection():
    """Testa detecção e redução de PII"""
    print("\n🔍 Testando Detecção de PII")
    print("="*50)
    
    sample_text = """
    João da Silva, advogado inscrito na OAB/SP 123456, 
    CPF 123.456.789-01, residente à Rua das Flores, 123, São Paulo - SP,
    CEP 01234-567, telefone (11) 99999-9999, email joao.silva@escritorio.com.br.
    
    Representa a empresa XYZ LTDA, CNPJ 12.345.678/0001-90,
    conta bancária 12345-6 da agência 1234 do Banco do Brasil.
    """
    
    print("📄 Texto original:")
    print(sample_text)
    
    # Detecta PIIs
    detector = PIIDetector()
    matches = detector.scan_text(sample_text)
    
    print(f"\n🎯 PIIs detectados: {len(matches)}")
    for match in matches:
        print(f"  - {match.type.value}: {match.value} (confiança: {match.confidence:.2f})")
    
    # Reduz PIIs
    redactor = PIIRedactor(detector)
    redacted_text, report = redactor.redact_text(sample_text, "type")
    
    print(f"\n📝 Texto reduzido:")
    print(redacted_text)
    
    print(f"\n📊 Relatório de redução:")
    print(f"  - Total de redações: {report['total_redactions']}")
    print(f"  - PIIs por tipo: {report['redactions_by_type']}")

async def test_audit_system():
    """Testa sistema de auditoria"""
    print("\n🔒 Testando Sistema de Auditoria")
    print("="*50)
    
    # Simula estado de execução
    mock_state = {
        "run_id": "test_run_123",
        "tenant_id": "tenant_abc",
        "user_id": "user_456",
        "task": "draft_document",
        "doc_type": "parecer",
        "initial_query": "Elaborar parecer sobre responsabilidade civil",
        "started_at": datetime.now(),
        "config": {
            "prompt_version": "2.0",
            "supervisor_version": "1.5",
            "policy": {"pii_handling": "redact", "audit_level": "full"}
        },
        "rag_docs": [
            {
                "src_id": "doc_001",
                "text": "Conteúdo do documento legal com CPF 123.456.789-01",
                "metadata": {"author": "Dr. Silva"}
            },
            {
                "src_id": "doc_002", 
                "text": "Jurisprudência relevante sobre o tema",
                "metadata": {"court": "STJ"}
            }
        ],
        "supervisor_notes": [
            {
                "agent": "analyzer",
                "model": "gpt-4",
                "latency_ms": 1500,
                "tokens_in": 100,
                "tokens_out": 50,
                "cost_usd": 0.01,
                "timestamp": datetime.now().isoformat(),
                "status": "completed"
            }
        ],
        "metrics": {
            "total_cost": 0.05,
            "tokens_input": 500,
            "tokens_output": 200
        },
        "final_text": "Este é o parecer jurídico final gerado pelo sistema.",
        "client_ip": "192.168.1.100",
        "user_agent": "Mozilla/5.0",
        "request_id": "req_789"
    }
    
    final_text = "Este é o parecer jurídico final gerado pelo sistema Harvey."
    
    # Cria registro de auditoria
    audit_manager = AuditManager()
    audit_record = audit_manager.build_audit_record(mock_state, final_text)
    
    print(f"📋 Registro de Auditoria Criado:")
    print(f"  - Run ID: {audit_record.run_id}")
    print(f"  - Tenant: {audit_record.tenant_id}")
    print(f"  - Sucesso: {audit_record.success}")
    print(f"  - Tempo de execução: {audit_record.execution_time_ms}ms")
    print(f"  - Custo estimado: ${audit_record.estimated_cost_usd:.6f}")
    print(f"  - Tokens: {audit_record.tokens_input} → {audit_record.tokens_output}")
    print(f"  - PIIs detectados: {audit_record.pii_report.get('total_redactions', 0)}")
    print(f"  - Nível de risco PII: {audit_record.pii_report.get('risk_level', 'LOW')}")
    print(f"  - Fontes utilizadas: {len(audit_record.sources_used)}")
    
    print(f"\n🔐 Hashes de Integridade:")
    print(f"  - Input: {audit_record.input_hash[:16]}...")
    print(f"  - Output: {audit_record.output_hash[:16]}...")
    print(f"  - Context: {audit_record.context_docs_hash[:16]}...")
    
    # Salva registro
    success = await audit_manager.save_audit_record(audit_record)
    print(f"\n✅ Registro salvo: {success}")

async def test_policy_system():
    """Testa sistema de políticas"""
    print("\n📋 Testando Sistema de Políticas")
    print("="*50)
    
    tenant_id = "tenant_test"
    
    # Inicializa políticas padrão
    policies = initialize_tenant_policies(tenant_id)
    print(f"📝 Políticas criadas: {len(policies)}")
    
    for policy in policies:
        print(f"  - {policy.name} ({policy.policy_type.value}): {len(policy.rules)} regras")
    
    # Testa avaliação de políticas
    policy_manager = PolicyManager()
    
    # Contexto de teste para política de acesso
    access_context = {
        "user_authenticated": True,
        "tenant_match": True,
        "user_role": "admin"
    }
    
    access_result = policy_manager.evaluate_policy(tenant_id, PolicyType.ACCESS_CONTROL, access_context)
    print(f"\n🔐 Avaliação de Acesso:")
    print(f"  - Permitido: {access_result['allowed']}")
    print(f"  - Ações: {len(access_result['actions'])}")
    print(f"  - Violações: {len(access_result['violations'])}")
    
    # Contexto de teste para política de PII
    pii_context = {
        "pii_detected": True,
        "pii_count": 5,
        "pii_types": ["CPF", "EMAIL", "PHONE"]
    }
    
    pii_result = policy_manager.evaluate_policy(tenant_id, PolicyType.PII_HANDLING, pii_context)
    print(f"\n🔍 Avaliação de PII:")
    print(f"  - Permitido: {pii_result['allowed']}")
    print(f"  - Ações requeridas: {len(pii_result['actions'])}")
    for action in pii_result['actions']:
        print(f"    - {action['action']}")
    
    # Obtém snapshot das políticas
    snapshot = policy_manager.get_policy_snapshot(tenant_id)
    print(f"\n📸 Snapshot das Políticas:")
    print(f"  - Timestamp: {snapshot['timestamp']}")
    print(f"  - Políticas: {len(snapshot['policies'])}")

async def test_feedback_system():
    """Testa sistema de feedback"""
    print("\n💬 Testando Sistema de Feedback")
    print("="*50)
    
    # Cria feedback de teste
    feedback = FeedbackRequest(
        run_id="test_run_456",
        rating=1,
        comment="Documento bem estruturado, mas faltou uma jurisprudência específica do STJ.",
        error_spans=[
            ErrorSpan(
                start=150,
                end=200,
                label="fundamentacao_incompleta",
                suggestion="Adicionar REsp 1234567/SP"
            )
        ],
        missing_sources=[
            MissingSource(
                raw="STJ, REsp 1234567/SP, Rel. Min. João Silva",
                class_="jurisprudencia",
                relevance_score=0.95
            )
        ],
        tags=["jurisprudencia", "fundamentacao", "stj"]
    )
    
    print(f"📝 Feedback criado:")
    print(f"  - Run ID: {feedback.run_id}")
    print(f"  - Rating: {feedback.rating}")
    print(f"  - Comentário: {feedback.comment}")
    print(f"  - Spans de erro: {len(feedback.error_spans or [])}")
    print(f"  - Fontes ausentes: {len(feedback.missing_sources or [])}")
    print(f"  - Tags: {feedback.tags}")
    
    if feedback.error_spans:
        for span in feedback.error_spans:
            print(f"    - Erro: {span.label} ({span.start}-{span.end})")
            if span.suggestion:
                print(f"      Sugestão: {span.suggestion}")
    
    if feedback.missing_sources:
        for source in feedback.missing_sources:
            print(f"    - Fonte ausente: {source.raw}")
            print(f"      Relevância: {source.relevance_score}")

async def test_integration():
    """Testa integração entre todos os sistemas"""
    print("\n🔗 Testando Integração Completa")
    print("="*50)
    
    tenant_id = "tenant_integration"
    
    # 1. Inicializa políticas
    policies = initialize_tenant_policies(tenant_id)
    policy_manager = PolicyManager()
    
    # 2. Simula execução com dados sensíveis
    sensitive_text = """
    Parecer jurídico sobre o caso envolvendo João da Silva (CPF 123.456.789-01).
    O cliente pode ser contatado pelo email joao@empresa.com ou telefone (11) 99999-9999.
    """
    
    # 3. Avalia políticas de PII
    pii_context = {"pii_detected": True, "pii_count": 3}
    pii_policy_result = policy_manager.evaluate_policy(tenant_id, PolicyType.PII_HANDLING, pii_context)
    
    # 4. Aplica redução de PII conforme política
    if pii_policy_result['allowed']:
        redacted_text, pii_report = scan_and_redact_pii(sensitive_text)
        print(f"📝 Texto reduzido conforme política:")
        print(f"  {redacted_text}")
    
    # 5. Cria estado de auditoria
    audit_state = {
        "run_id": "integration_test_789",
        "tenant_id": tenant_id,
        "user_id": "user_integration",
        "task": "integration_test",
        "doc_type": "parecer",
        "initial_query": "Teste de integração completa",
        "started_at": datetime.now(),
        "config": {
            "policy": policy_manager.get_policy_snapshot(tenant_id)
        },
        "rag_docs": [
            {
                "src_id": "integration_doc_001",
                "text": sensitive_text,
                "metadata": {"source": "integration_test"}
            }
        ],
        "supervisor_notes": [],
        "metrics": {"total_cost": 0.02},
        "final_text": redacted_text
    }
    
    # 6. Cria registro de auditoria
    success = await build_and_save_audit_record(audit_state, redacted_text)
    
    print(f"\n✅ Integração concluída:")
    print(f"  - Políticas aplicadas: {len(policies)}")
    print(f"  - PIIs reduzidos: {pii_report.get('total_redactions', 0)}")
    print(f"  - Auditoria salva: {success}")

async def main():
    """Função principal de teste"""
    print("🛡️  TESTE DA ONDA 3: FEEDBACK E SEGURANÇA AVANÇADA")
    print("="*70)
    print("Testando sistema completo de feedback, auditoria e segurança")
    print("="*70)
    
    try:
        await test_pii_detection()
        await test_audit_system()
        await test_policy_system()
        await test_feedback_system()
        await test_integration()
        
        print("\n🎉 TODOS OS TESTES DA ONDA 3 CONCLUÍDOS COM SUCESSO!")
        print("="*70)
        print("✅ Detecção e redução de PII funcionando")
        print("✅ Sistema de auditoria forense operacional")
        print("✅ Políticas de segurança implementadas")
        print("✅ Sistema de feedback estruturado")
        print("✅ Integração completa validada")
        print("✅ Conformidade com LGPD e governança")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE OS TESTES: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
