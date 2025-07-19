"""
Módulo de Detecção e Mascaramento de PII - Onda 3
Protege informações pessoais identificáveis em documentos jurídicos
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)

class PIIType(str, Enum):
    """Tipos de PII detectáveis"""
    CPF = "CPF"
    CNPJ = "CNPJ"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    RG = "RG"
    PASSPORT = "PASSPORT"
    CREDIT_CARD = "CREDIT_CARD"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    ADDRESS = "ADDRESS"
    NAME = "NAME"

@dataclass
class PIIMatch:
    """Representa uma ocorrência de PII detectada"""
    type: PIIType
    value: str
    start: int
    end: int
    confidence: float
    context: str

# Padrões regex para PIIs comuns no Brasil
PII_PATTERNS = {
    PIIType.CPF: [
        re.compile(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b'),  # 123.456.789-01
        re.compile(r'\b\d{11}\b'),  # 12345678901 (somente números)
    ],
    PIIType.CNPJ: [
        re.compile(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b'),  # 12.345.678/0001-90
        re.compile(r'\b\d{14}\b'),  # 12345678000190 (somente números)
    ],
    PIIType.EMAIL: [
        re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),
    ],
    PIIType.PHONE: [
        re.compile(r'\b\(?\d{2}\)?\s?\d{4,5}-?\d{4}\b'),  # (11) 99999-9999
        re.compile(r'\b\d{2}\s?\d{4,5}\s?\d{4}\b'),  # 11 99999 9999
    ],
    PIIType.RG: [
        re.compile(r'\bRG\s*:?\s*\d{1,2}\.\d{3}\.\d{3}-?\d{1,2}\b', re.IGNORECASE),
        re.compile(r'\b\d{1,2}\.\d{3}\.\d{3}-?\d{1,2}\b'),
    ],
    PIIType.PASSPORT: [
        re.compile(r'\b[A-Z]{2}\d{6}\b'),  # Passaporte brasileiro
    ],
    PIIType.CREDIT_CARD: [
        re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b'),  # Cartão de crédito
    ],
    PIIType.BANK_ACCOUNT: [
        re.compile(r'\bAg\s*:?\s*\d{3,4}-?\d?\s*C/C\s*:?\s*\d{4,}-?\d\b', re.IGNORECASE),
        re.compile(r'\bConta\s*:?\s*\d{4,}-?\d\b', re.IGNORECASE),
    ],
    PIIType.ADDRESS: [
        re.compile(r'\b(?:Rua|Av|Avenida|Travessa|Alameda)\s+[^,\n]{10,50}', re.IGNORECASE),
        re.compile(r'\bCEP\s*:?\s*\d{5}-?\d{3}\b', re.IGNORECASE),
    ],
    PIIType.NAME: [
        # Padrão conservador para nomes próprios em contexto jurídico
        re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'),
    ]
}

class PIIDetector:
    """Detector de informações pessoais identificáveis"""
    
    def __init__(self):
        self.patterns = PII_PATTERNS
        self.context_window = 20  # Caracteres antes e depois para contexto
    
    def scan_text(self, text: str) -> List[PIIMatch]:
        """Escaneia texto em busca de PIIs"""
        if not text:
            return []
        
        matches = []
        
        for pii_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    # Extrai contexto
                    start_ctx = max(0, match.start() - self.context_window)
                    end_ctx = min(len(text), match.end() + self.context_window)
                    context = text[start_ctx:end_ctx]
                    
                    # Calcula confiança baseada no tipo
                    confidence = self._calculate_confidence(pii_type, match.group())
                    
                    matches.append(PIIMatch(
                        type=pii_type,
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=confidence,
                        context=context
                    ))
        
        # Remove duplicatas e ordena por posição
        matches = self._deduplicate_matches(matches)
        return sorted(matches, key=lambda m: m.start)
    
    def _calculate_confidence(self, pii_type: PIIType, value: str) -> float:
        """Calcula confiança da detecção baseada no tipo e valor"""
        if pii_type == PIIType.CPF:
            return 0.95 if self._validate_cpf(value) else 0.7
        elif pii_type == PIIType.CNPJ:
            return 0.95 if self._validate_cnpj(value) else 0.7
        elif pii_type == PIIType.EMAIL:
            return 0.9
        elif pii_type == PIIType.PHONE:
            return 0.8
        elif pii_type == PIIType.NAME:
            return 0.6  # Menos confiável devido a falsos positivos
        else:
            return 0.7
    
    def _validate_cpf(self, cpf: str) -> bool:
        """Valida CPF usando dígitos verificadores"""
        # Remove formatação
        cpf = re.sub(r'[^\d]', '', cpf)
        
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False
        
        # Validação dos dígitos verificadores
        def calc_digit(cpf_digits, weights):
            total = sum(int(digit) * weight for digit, weight in zip(cpf_digits, weights))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder
        
        first_digit = calc_digit(cpf[:9], range(10, 1, -1))
        second_digit = calc_digit(cpf[:10], range(11, 1, -1))
        
        return cpf[9] == str(first_digit) and cpf[10] == str(second_digit)
    
    def _validate_cnpj(self, cnpj: str) -> bool:
        """Valida CNPJ usando dígitos verificadores"""
        # Remove formatação
        cnpj = re.sub(r'[^\d]', '', cnpj)
        
        if len(cnpj) != 14:
            return False
        
        # Validação dos dígitos verificadores
        def calc_digit(cnpj_digits, weights):
            total = sum(int(digit) * weight for digit, weight in zip(cnpj_digits, weights))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder
        
        first_weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        second_weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        
        first_digit = calc_digit(cnpj[:12], first_weights)
        second_digit = calc_digit(cnpj[:13], second_weights)
        
        return cnpj[12] == str(first_digit) and cnpj[13] == str(second_digit)
    
    def _deduplicate_matches(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Remove matches duplicados ou sobrepostos"""
        if not matches:
            return []
        
        # Ordena por posição
        sorted_matches = sorted(matches, key=lambda m: (m.start, m.end))
        deduplicated = [sorted_matches[0]]
        
        for current in sorted_matches[1:]:
            last = deduplicated[-1]
            
            # Se não sobrepõe ou é do mesmo tipo com maior confiança
            if current.start >= last.end or (
                current.start == last.start and 
                current.end == last.end and 
                current.confidence > last.confidence
            ):
                if current.start == last.start and current.end == last.end:
                    deduplicated[-1] = current  # Substitui por maior confiança
                else:
                    deduplicated.append(current)
        
        return deduplicated

class PIIRedactor:
    """Redator de informações pessoais identificáveis"""
    
    def __init__(self, detector: PIIDetector):
        self.detector = detector
    
    def redact_text(self, text: str, replacement_strategy: str = "type") -> Tuple[str, Dict[str, Any]]:
        """
        Redige PIIs no texto
        
        Args:
            text: Texto original
            replacement_strategy: "type" (substitui por tipo), "hash" (substitui por hash), "mask" (substitui por asteriscos)
        
        Returns:
            Tuple com texto reduzido e relatório de redução
        """
        if not text:
            return text, {}
        
        matches = self.detector.scan_text(text)
        
        if not matches:
            return text, {"pii_detected": False, "total_redactions": 0}
        
        # Ordena por posição decrescente para não afetar índices
        matches = sorted(matches, key=lambda m: m.start, reverse=True)
        
        redacted_text = text
        redactions = []
        
        for match in matches:
            replacement = self._generate_replacement(match, replacement_strategy)
            redacted_text = redacted_text[:match.start] + replacement + redacted_text[match.end:]
            
            redactions.append({
                "type": match.type.value,
                "original_length": len(match.value),
                "replacement": replacement,
                "position": match.start,
                "confidence": match.confidence
            })
        
        # Gera relatório
        report = {
            "pii_detected": True,
            "total_redactions": len(redactions),
            "redactions_by_type": self._group_redactions_by_type(redactions),
            "redactions": redactions
        }
        
        return redacted_text, report
    
    def _generate_replacement(self, match: PIIMatch, strategy: str) -> str:
        """Gera substituição baseada na estratégia"""
        if strategy == "type":
            return f"[{match.type.value}_REDACTED]"
        elif strategy == "hash":
            hash_value = hashlib.sha256(match.value.encode()).hexdigest()[:8]
            return f"[{match.type.value}_{hash_value}]"
        elif strategy == "mask":
            return "*" * len(match.value)
        else:
            return f"[{match.type.value}_REDACTED]"
    
    def _group_redactions_by_type(self, redactions: List[Dict]) -> Dict[str, int]:
        """Agrupa redações por tipo"""
        counts = {}
        for redaction in redactions:
            pii_type = redaction["type"]
            counts[pii_type] = counts.get(pii_type, 0) + 1
        return counts

# Funções de conveniência para uso direto
def pii_scan_counts(text: str) -> Dict[str, int]:
    """Conta ocorrências de cada tipo de PII - função legada"""
    if not text:
        return {}
    
    detector = PIIDetector()
    matches = detector.scan_text(text)
    
    counts = {}
    for match in matches:
        counts[match.type.value] = counts.get(match.type.value, 0) + 1
    
    return counts

def redact_pii(text: str, strategy: str = "type") -> str:
    """Substitui PIIs por placeholders - função legada"""
    if not text:
        return ""
    
    detector = PIIDetector()
    redactor = PIIRedactor(detector)
    redacted_text, _ = redactor.redact_text(text, strategy)
    
    return redacted_text

def scan_and_redact_pii(text: str, strategy: str = "type") -> Tuple[str, Dict[str, Any]]:
    """Função principal para escanear e redigir PII"""
    detector = PIIDetector()
    redactor = PIIRedactor(detector)
    return redactor.redact_text(text, strategy)

# Exemplo de uso
if __name__ == "__main__":
    sample_text = """
    João Silva, CPF 123.456.789-01, residente à Rua das Flores, 123, 
    pode ser contatado pelo email joao@email.com ou telefone (11) 99999-9999.
    Empresa ABC LTDA, CNPJ 12.345.678/0001-90.
    """
    
    redacted, report = scan_and_redact_pii(sample_text)
    print("Texto original:")
    print(sample_text)
    print("\nTexto reduzido:")
    print(redacted)
    print("\nRelatório:")
    print(report)
