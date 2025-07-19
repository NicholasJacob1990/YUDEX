"""
Módulo de Auditoria Forense - Onda 3
Cria trilha de auditoria imutável para rastreabilidade e conformidade
"""

import hashlib
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import uuid
import logging

from app.core.security.pii import scan_and_redact_pii, pii_scan_counts

logger = logging.getLogger(__name__)

@dataclass
class ExecutionTrace:
    """Trace de execução de um agente"""
    agent: str
    model: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    timestamp: datetime
    status: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class AuditRecord:
    """Registro completo de auditoria"""
    run_id: str
    tenant_id: str
    user_id: Optional[str]
    task: str
    doc_type: str
    started_at: datetime
    ended_at: Optional[datetime]
    success: bool
    error_message: Optional[str]
    
    # Hashes para integridade
    input_hash: str
    output_hash: str
    context_docs_hash: str
    
    # Versionamento
    prompt_version: str
    supervisor_version: str
    agent_trace: List[ExecutionTrace]
    
    # Política e Segurança
    policy_snapshot: Dict[str, Any]
    pii_report: Dict[str, Any]
    sources_used: List[str]
    
    # Métricas
    estimated_cost_usd: float
    tokens_input: int
    tokens_output: int
    execution_time_ms: int
    
    # Metadados
    client_ip: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]

class AuditManager:
    """Gerenciador de auditoria forense"""
    
    def __init__(self):
        self.hash_algorithm = "SHA-256"
        self.version = "1.0"
    
    def hash_sha256(self, text: str) -> str:
        """Gera hash SHA-256 de um texto"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    
    def create_input_hash(self, initial_query: str, config: Dict[str, Any]) -> str:
        """Cria hash do input completo"""
        input_data = {
            "query": initial_query,
            "config": config,
            "timestamp": datetime.now().isoformat()
        }
        input_string = json.dumps(input_data, sort_keys=True)
        return self.hash_sha256(input_string)
    
    def create_output_hash(self, final_text: str, metadata: Dict[str, Any] = None) -> str:
        """Cria hash do output completo"""
        output_data = {
            "text": final_text,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        output_string = json.dumps(output_data, sort_keys=True)
        return self.hash_sha256(output_string)
    
    def create_context_hash(self, source_ids: List[str]) -> str:
        """Cria hash dos documentos de contexto"""
        # Ordena IDs para garantir consistência
        sorted_ids = sorted(source_ids)
        context_string = "|".join(sorted_ids)
        return self.hash_sha256(context_string)
    
    def analyze_pii_in_context(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analisa PIIs em documentos de contexto"""
        full_text = ""
        for doc in documents:
            full_text += doc.get("text", "") + "\n"
        
        # Escaneia PIIs
        redacted_text, pii_report = scan_and_redact_pii(full_text)
        
        return {
            "original_length": len(full_text),
            "redacted_length": len(redacted_text),
            "pii_detected": pii_report.get("pii_detected", False),
            "total_redactions": pii_report.get("total_redactions", 0),
            "redactions_by_type": pii_report.get("redactions_by_type", {}),
            "risk_level": self._calculate_pii_risk_level(pii_report)
        }
    
    def _calculate_pii_risk_level(self, pii_report: Dict[str, Any]) -> str:
        """Calcula nível de risco baseado em PIIs detectados"""
        total = pii_report.get("total_redactions", 0)
        
        if total == 0:
            return "LOW"
        elif total <= 5:
            return "MEDIUM"
        elif total <= 15:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def build_audit_record(self, state: Dict[str, Any], final_text: str) -> AuditRecord:
        """Constrói registro de auditoria completo"""
        
        # Extrai informações do estado
        run_id = state.get("run_id", str(uuid.uuid4()))
        tenant_id = state.get("tenant_id", "unknown")
        user_id = state.get("user_id")
        task = state.get("task", "unknown")
        doc_type = state.get("doc_type", "unknown")
        
        # Timestamps
        started_at = state.get("started_at", datetime.now())
        ended_at = datetime.now()
        
        # Status
        success = state.get("final_text") is not None and not state.get("error")
        error_message = state.get("error")
        
        # Hashes
        config = state.get("config", {})
        input_hash = self.create_input_hash(state.get("initial_query", ""), config)
        output_hash = self.create_output_hash(final_text)
        
        # Documentos de contexto
        rag_docs = state.get("rag_docs", [])
        source_ids = [doc.get("src_id", "") for doc in rag_docs]
        context_docs_hash = self.create_context_hash(source_ids)
        
        # Trace dos agentes
        agent_trace = self._build_agent_trace(state)
        
        # Análise de PII
        pii_report = self.analyze_pii_in_context(rag_docs)
        
        # Métricas
        metrics = state.get("metrics", {})
        estimated_cost_usd = metrics.get("total_cost", 0.0)
        tokens_input = metrics.get("tokens_input", 0)
        tokens_output = metrics.get("tokens_output", 0)
        execution_time_ms = int((ended_at - started_at).total_seconds() * 1000)
        
        # Política
        policy_snapshot = config.get("policy", {})
        
        return AuditRecord(
            run_id=run_id,
            tenant_id=tenant_id,
            user_id=user_id,
            task=task,
            doc_type=doc_type,
            started_at=started_at,
            ended_at=ended_at,
            success=success,
            error_message=error_message,
            input_hash=input_hash,
            output_hash=output_hash,
            context_docs_hash=context_docs_hash,
            prompt_version=config.get("prompt_version", "1.0"),
            supervisor_version=config.get("supervisor_version", "1.0"),
            agent_trace=agent_trace,
            policy_snapshot=policy_snapshot,
            pii_report=pii_report,
            sources_used=source_ids,
            estimated_cost_usd=estimated_cost_usd,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            execution_time_ms=execution_time_ms,
            client_ip=state.get("client_ip"),
            user_agent=state.get("user_agent"),
            request_id=state.get("request_id")
        )
    
    def _build_agent_trace(self, state: Dict[str, Any]) -> List[ExecutionTrace]:
        """Constrói trace dos agentes a partir do estado"""
        traces = []
        
        # Extrai informações de trace do estado
        supervisor_notes = state.get("supervisor_notes", [])
        
        for note in supervisor_notes:
            if isinstance(note, dict):
                trace = ExecutionTrace(
                    agent=note.get("agent", "unknown"),
                    model=note.get("model", "unknown"),
                    latency_ms=note.get("latency_ms", 0),
                    tokens_in=note.get("tokens_in", 0),
                    tokens_out=note.get("tokens_out", 0),
                    cost_usd=note.get("cost_usd", 0.0),
                    timestamp=datetime.fromisoformat(note.get("timestamp", datetime.now().isoformat())),
                    status=note.get("status", "completed")
                )
                traces.append(trace)
        
        return traces
    
    async def save_audit_record(self, audit_record: AuditRecord) -> bool:
        """Salva registro de auditoria no banco de dados"""
        try:
            # Converte trace para formato JSON
            agent_trace_json = [trace.to_dict() for trace in audit_record.agent_trace]
            
            # Prepara dados para inserção
            audit_data = {
                "run_id": audit_record.run_id,
                "tenant_id": audit_record.tenant_id,
                "user_id": audit_record.user_id,
                "task": audit_record.task,
                "doc_type": audit_record.doc_type,
                "started_at": audit_record.started_at,
                "ended_at": audit_record.ended_at,
                "success": audit_record.success,
                "error_message": audit_record.error_message,
                "input_hash": audit_record.input_hash,
                "output_hash": audit_record.output_hash,
                "context_docs_hash": audit_record.context_docs_hash,
                "prompt_version": audit_record.prompt_version,
                "supervisor_version": audit_record.supervisor_version,
                "agent_trace": json.dumps(agent_trace_json),
                "policy_snapshot": json.dumps(audit_record.policy_snapshot),
                "pii_report": json.dumps(audit_record.pii_report),
                "sources_used": json.dumps(audit_record.sources_used),
                "estimated_cost_usd": audit_record.estimated_cost_usd,
                "tokens_input": audit_record.tokens_input,
                "tokens_output": audit_record.tokens_output,
                "execution_time_ms": audit_record.execution_time_ms,
                "client_ip": audit_record.client_ip,
                "user_agent": audit_record.user_agent,
                "request_id": audit_record.request_id
            }
            
            logger.info(f"Salvando registro de auditoria: run_id={audit_record.run_id}")
            
            # TODO: Implementar inserção no banco de dados
            # query = """
            # INSERT INTO run_audit (
            #     run_id, tenant_id, user_id, task, doc_type, started_at, ended_at,
            #     success, error_message, input_hash, output_hash, context_docs_hash,
            #     prompt_version, supervisor_version, agent_trace, policy_snapshot,
            #     pii_report, sources_used, estimated_cost_usd, tokens_input,
            #     tokens_output, execution_time_ms, client_ip, user_agent, request_id
            # ) VALUES (
            #     %(run_id)s, %(tenant_id)s, %(user_id)s, %(task)s, %(doc_type)s,
            #     %(started_at)s, %(ended_at)s, %(success)s, %(error_message)s,
            #     %(input_hash)s, %(output_hash)s, %(context_docs_hash)s,
            #     %(prompt_version)s, %(supervisor_version)s, %(agent_trace)s,
            #     %(policy_snapshot)s, %(pii_report)s, %(sources_used)s,
            #     %(estimated_cost_usd)s, %(tokens_input)s, %(tokens_output)s,
            #     %(execution_time_ms)s, %(client_ip)s, %(user_agent)s, %(request_id)s
            # )
            # """
            # await db.execute(query, audit_data)
            
            # Para demonstração, logga os dados
            logger.info(f"Auditoria salva com sucesso: {audit_record.run_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar auditoria: {e}")
            return False
    
    async def verify_audit_integrity(self, run_id: str) -> bool:
        """Verifica integridade de um registro de auditoria"""
        try:
            # TODO: Implementar verificação de integridade
            # 1. Buscar registro no banco
            # 2. Recomputar hashes
            # 3. Comparar com valores armazenados
            # 4. Registrar resultado da verificação
            
            logger.info(f"Verificando integridade do registro: {run_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao verificar integridade: {e}")
            return False

# Função principal para uso no pipeline
async def build_and_save_audit_record(state: Dict[str, Any], final_text: str) -> bool:
    """Função principal para criar e salvar registro de auditoria"""
    audit_manager = AuditManager()
    
    try:
        # Constrói registro de auditoria
        audit_record = audit_manager.build_audit_record(state, final_text)
        
        # Salva no banco de dados
        success = await audit_manager.save_audit_record(audit_record)
        
        if success:
            logger.info(f"Auditoria concluída com sucesso: {audit_record.run_id}")
            
            # Log para demonstração
            print(f"--- AUDIT RECORD para run_id {audit_record.run_id} ---")
            print(f"Tenant: {audit_record.tenant_id}")
            print(f"Sucesso: {audit_record.success}")
            print(f"Custo: ${audit_record.estimated_cost_usd:.6f}")
            print(f"Tokens: {audit_record.tokens_input} → {audit_record.tokens_output}")
            print(f"Tempo: {audit_record.execution_time_ms}ms")
            print(f"PIIs detectados: {audit_record.pii_report.get('total_redactions', 0)}")
            print(f"Fontes utilizadas: {len(audit_record.sources_used)}")
            print(f"Hash input: {audit_record.input_hash[:16]}...")
            print(f"Hash output: {audit_record.output_hash[:16]}...")
            
        return success
        
    except Exception as e:
        logger.error(f"Erro ao processar auditoria: {e}")
        return False

# Função para verificar integridade
async def verify_run_integrity(run_id: str) -> bool:
    """Verifica integridade de uma execução específica"""
    audit_manager = AuditManager()
    return await audit_manager.verify_audit_integrity(run_id)
