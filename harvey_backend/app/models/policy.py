"""
Sistema de Políticas de Segurança - Onda 3
Gerenciamento de políticas de acesso e segurança por tenant
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import json

class PolicyType(str, Enum):
    """Tipos de políticas disponíveis"""
    ACCESS_CONTROL = "access_control"
    DATA_RETENTION = "data_retention"
    PII_HANDLING = "pii_handling"
    AUDIT_LEVEL = "audit_level"
    CONTENT_FILTERING = "content_filtering"
    EXPORT_RESTRICTIONS = "export_restrictions"

class PolicySeverity(str, Enum):
    """Níveis de severidade das políticas"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class PolicyRule(BaseModel):
    """Regra individual de uma política"""
    id: str
    name: str
    description: str
    condition: Dict[str, Any]
    action: Dict[str, Any]
    severity: PolicySeverity
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class SecurityPolicy(BaseModel):
    """Política de segurança completa"""
    id: str
    tenant_id: str
    name: str
    description: str
    policy_type: PolicyType
    version: str
    rules: List[PolicyRule]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: str
    approved_by: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PolicyManager:
    """Gerenciador de políticas de segurança"""
    
    def __init__(self):
        self.policies: Dict[str, SecurityPolicy] = {}
        self.tenant_policies: Dict[str, List[str]] = {}
    
    def create_default_policies(self, tenant_id: str) -> List[SecurityPolicy]:
        """Cria políticas padrão para um novo tenant"""
        
        # Política de controle de acesso
        access_policy = SecurityPolicy(
            id=f"access_policy_{tenant_id}",
            tenant_id=tenant_id,
            name="Política de Controle de Acesso",
            description="Regras de acesso a documentos e funcionalidades",
            policy_type=PolicyType.ACCESS_CONTROL,
            version="1.0",
            rules=[
                PolicyRule(
                    id="access_rule_1",
                    name="Autenticação Obrigatória",
                    description="Usuários devem estar autenticados",
                    condition={"user_authenticated": True},
                    action={"allow": True},
                    severity=PolicySeverity.HIGH
                ),
                PolicyRule(
                    id="access_rule_2",
                    name="Acesso por Tenant",
                    description="Usuários só podem acessar dados do próprio tenant",
                    condition={"tenant_match": True},
                    action={"allow": True},
                    severity=PolicySeverity.CRITICAL
                )
            ],
            created_by="system"
        )
        
        # Política de tratamento de PII
        pii_policy = SecurityPolicy(
            id=f"pii_policy_{tenant_id}",
            tenant_id=tenant_id,
            name="Política de Tratamento de PII",
            description="Regras para tratamento de dados pessoais",
            policy_type=PolicyType.PII_HANDLING,
            version="1.0",
            rules=[
                PolicyRule(
                    id="pii_rule_1",
                    name="Redução Automática de PII",
                    description="PIIs devem ser automaticamente reduzidos",
                    condition={"pii_detected": True},
                    action={"redact": True, "log": True},
                    severity=PolicySeverity.HIGH
                ),
                PolicyRule(
                    id="pii_rule_2",
                    name="Auditoria de PII",
                    description="Detecção de PII deve ser auditada",
                    condition={"pii_count": {"gt": 0}},
                    action={"audit": True, "notify": True},
                    severity=PolicySeverity.MEDIUM
                )
            ],
            created_by="system"
        )
        
        # Política de auditoria
        audit_policy = SecurityPolicy(
            id=f"audit_policy_{tenant_id}",
            tenant_id=tenant_id,
            name="Política de Auditoria",
            description="Regras para auditoria e rastreabilidade",
            policy_type=PolicyType.AUDIT_LEVEL,
            version="1.0",
            rules=[
                PolicyRule(
                    id="audit_rule_1",
                    name="Auditoria Completa",
                    description="Todas as execuções devem ser auditadas",
                    condition={"execution_type": "all"},
                    action={"audit": True, "full_trace": True},
                    severity=PolicySeverity.HIGH
                ),
                PolicyRule(
                    id="audit_rule_2",
                    name="Retenção de Logs",
                    description="Logs devem ser mantidos por 7 anos",
                    condition={"log_type": "audit"},
                    action={"retain_years": 7},
                    severity=PolicySeverity.MEDIUM
                )
            ],
            created_by="system"
        )
        
        # Política de retenção de dados
        retention_policy = SecurityPolicy(
            id=f"retention_policy_{tenant_id}",
            tenant_id=tenant_id,
            name="Política de Retenção de Dados",
            description="Regras para retenção e exclusão de dados",
            policy_type=PolicyType.DATA_RETENTION,
            version="1.0",
            rules=[
                PolicyRule(
                    id="retention_rule_1",
                    name="Retenção de Documentos",
                    description="Documentos devem ser mantidos por 10 anos",
                    condition={"data_type": "documents"},
                    action={"retain_years": 10},
                    severity=PolicySeverity.MEDIUM
                ),
                PolicyRule(
                    id="retention_rule_2",
                    name="Exclusão de Dados Temporários",
                    description="Dados temporários devem ser excluídos em 30 dias",
                    condition={"data_type": "temporary"},
                    action={"delete_after_days": 30},
                    severity=PolicySeverity.LOW
                )
            ],
            created_by="system"
        )
        
        policies = [access_policy, pii_policy, audit_policy, retention_policy]
        
        # Registra as políticas
        for policy in policies:
            self.policies[policy.id] = policy
        
        # Associa ao tenant
        self.tenant_policies[tenant_id] = [policy.id for policy in policies]
        
        return policies
    
    def get_tenant_policies(self, tenant_id: str) -> List[SecurityPolicy]:
        """Obtém todas as políticas de um tenant"""
        policy_ids = self.tenant_policies.get(tenant_id, [])
        return [self.policies[pid] for pid in policy_ids if pid in self.policies]
    
    def get_policy_by_type(self, tenant_id: str, policy_type: PolicyType) -> Optional[SecurityPolicy]:
        """Obtém política específica por tipo"""
        policies = self.get_tenant_policies(tenant_id)
        for policy in policies:
            if policy.policy_type == policy_type:
                return policy
        return None
    
    def evaluate_policy(self, tenant_id: str, policy_type: PolicyType, context: Dict[str, Any]) -> Dict[str, Any]:
        """Avalia uma política contra um contexto"""
        policy = self.get_policy_by_type(tenant_id, policy_type)
        
        if not policy or not policy.active:
            return {"allowed": True, "actions": [], "violations": []}
        
        actions = []
        violations = []
        allowed = True
        
        for rule in policy.rules:
            if not rule.enabled:
                continue
                
            # Avalia condição da regra
            if self._evaluate_condition(rule.condition, context):
                # Executa ação
                if rule.action.get("allow") is False:
                    allowed = False
                    violations.append({
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "severity": rule.severity.value,
                        "description": rule.description
                    })
                else:
                    actions.append({
                        "rule_id": rule.id,
                        "action": rule.action,
                        "severity": rule.severity.value
                    })
        
        return {
            "allowed": allowed,
            "actions": actions,
            "violations": violations,
            "policy_id": policy.id,
            "policy_version": policy.version
        }
    
    def _evaluate_condition(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Avalia uma condição de regra"""
        for key, expected in condition.items():
            if key not in context:
                return False
            
            actual = context[key]
            
            if isinstance(expected, dict):
                # Operadores especiais
                if "gt" in expected:
                    if not (actual > expected["gt"]):
                        return False
                elif "lt" in expected:
                    if not (actual < expected["lt"]):
                        return False
                elif "eq" in expected:
                    if not (actual == expected["eq"]):
                        return False
            else:
                # Comparação direta
                if actual != expected:
                    return False
        
        return True
    
    def get_policy_snapshot(self, tenant_id: str) -> Dict[str, Any]:
        """Obtém snapshot das políticas do tenant para auditoria"""
        policies = self.get_tenant_policies(tenant_id)
        
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "tenant_id": tenant_id,
            "policies": {}
        }
        
        for policy in policies:
            snapshot["policies"][policy.policy_type.value] = {
                "id": policy.id,
                "name": policy.name,
                "version": policy.version,
                "active": policy.active,
                "rules_count": len(policy.rules),
                "rules": [
                    {
                        "id": rule.id,
                        "name": rule.name,
                        "severity": rule.severity.value,
                        "enabled": rule.enabled
                    }
                    for rule in policy.rules
                ]
            }
        
        return snapshot

# Instância global do gerenciador
_policy_manager = PolicyManager()

def get_policy_manager() -> PolicyManager:
    """Obtém instância global do gerenciador de políticas"""
    return _policy_manager

def initialize_tenant_policies(tenant_id: str) -> List[SecurityPolicy]:
    """Inicializa políticas padrão para um tenant"""
    return _policy_manager.create_default_policies(tenant_id)

def evaluate_access_policy(tenant_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Avalia política de acesso"""
    return _policy_manager.evaluate_policy(tenant_id, PolicyType.ACCESS_CONTROL, context)

def evaluate_pii_policy(tenant_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Avalia política de PII"""
    return _policy_manager.evaluate_policy(tenant_id, PolicyType.PII_HANDLING, context)

def evaluate_audit_policy(tenant_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Avalia política de auditoria"""
    return _policy_manager.evaluate_policy(tenant_id, PolicyType.AUDIT_LEVEL, context)

def get_tenant_policy_snapshot(tenant_id: str) -> Dict[str, Any]:
    """Obtém snapshot das políticas do tenant"""
    return _policy_manager.get_policy_snapshot(tenant_id)

# Exemplo de uso
if __name__ == "__main__":
    # Inicializa políticas para um tenant
    policies = initialize_tenant_policies("tenant_test")
    
    print(f"Criadas {len(policies)} políticas para tenant_test")
    
    # Testa avaliação de políticas
    context = {
        "user_authenticated": True,
        "tenant_match": True,
        "pii_detected": True,
        "pii_count": 3
    }
    
    access_result = evaluate_access_policy("tenant_test", context)
    pii_result = evaluate_pii_policy("tenant_test", context)
    
    print(f"Acesso permitido: {access_result['allowed']}")
    print(f"Ações PII: {len(pii_result['actions'])}")
    
    # Obtém snapshot
    snapshot = get_tenant_policy_snapshot("tenant_test")
    print(f"Snapshot contém {len(snapshot['policies'])} políticas")
