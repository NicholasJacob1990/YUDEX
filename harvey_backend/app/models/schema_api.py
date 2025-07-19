"""
Schemas da API para suporte a contexto externo
Permite que clientes enviem documentos de contexto específicos para cada requisição
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

class ExternalDoc(BaseModel):
    """
    Representa um documento de contexto fornecido externamente pelo cliente da API.
    """
    src_id: str = Field(
        ..., 
        description="Um ID único para este documento, para rastreabilidade.",
        example="email_cliente_01"
    )
    
    text: str = Field(
        ..., 
        description="O conteúdo textual do documento/trecho.",
        min_length=10,
        max_length=50000
    )
    
    meta: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Metadados como tipo, autor, data, etc.",
        example={
            "tipo": "comunicacao_cliente",
            "data": "2024-10-26",
            "autor": "João Silva",
            "urgencia": "alta"
        }
    )
    
    priority: Optional[float] = Field(
        default=0.9,
        description="Prioridade do documento na fusão RRF (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    @validator('text')
    def validate_text_content(cls, v):
        if not v.strip():
            raise ValueError("Conteúdo do documento não pode estar vazio")
        return v.strip()

class GenerationRequest(BaseModel):
    """
    Schema completo para a requisição de geração de documentos com contexto externo.
    """
    # Campos existentes
    run_id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID único da execução"
    )
    
    tenant_id: str = Field(
        ...,
        description="ID do tenant/cliente"
    )
    
    task: str = Field(
        ...,
        description="Tipo de tarefa (draft, analyze, review, etc.)",
        example="draft"
    )
    
    doc_type: str = Field(
        ...,
        description="Tipo de documento a ser gerado",
        example="peticao"
    )
    
    query: str = Field(
        ...,
        description="Consulta ou instrução principal",
        min_length=5,
        max_length=5000
    )
    
    theme: Optional[str] = Field(
        default=None,
        description="Tema ou área jurídica específica"
    )
    
    # --- NOVOS CAMPOS PARA CONTEXTO EXTERNO ---
    context_docs_external: Optional[List[ExternalDoc]] = Field(
        default=None,
        description="Lista opcional de documentos de contexto para usar nesta execução específica.",
        max_items=50  # Limite prático
    )
    
    use_internal_rag: bool = Field(
        default=True,
        description="Se true, o sistema também buscará em sua base de dados interna (RAG federado)."
    )
    
    external_docs_priority: float = Field(
        default=0.9,
        description="Prioridade padrão dos documentos externos na fusão RRF",
        ge=0.0,
        le=1.0
    )
    
    # Configurações de busca
    rag_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Configurações específicas do RAG",
        example={
            "k_total": 20,
            "enable_personalization": True,
            "personalization_alpha": 0.25,
            "rerank_results": True
        }
    )
    
    # Configurações gerais
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Configurações adicionais da execução"
    )
    
    @validator('context_docs_external')
    def validate_external_docs(cls, v):
        if v is not None and len(v) > 50:
            raise ValueError("Máximo de 50 documentos externos por requisição")
        
        # Verificar IDs únicos
        if v:
            src_ids = [doc.src_id for doc in v]
            if len(src_ids) != len(set(src_ids)):
                raise ValueError("IDs dos documentos externos devem ser únicos")
        
        return v
    
    @validator('rag_config')
    def validate_rag_config(cls, v):
        if v:
            # Validar k_total
            if 'k_total' in v and not (1 <= v['k_total'] <= 100):
                raise ValueError("k_total deve estar entre 1 e 100")
            
            # Validar personalization_alpha
            if 'personalization_alpha' in v and not (0.0 <= v['personalization_alpha'] <= 1.0):
                raise ValueError("personalization_alpha deve estar entre 0.0 e 1.0")
        
        return v

class GenerationResponse(BaseModel):
    """
    Schema de resposta para geração de documentos.
    """
    success: bool = Field(
        ...,
        description="Se a geração foi bem-sucedida"
    )
    
    run_id: str = Field(
        ...,
        description="ID da execução"
    )
    
    final_document: Optional[str] = Field(
        default=None,
        description="Documento final gerado"
    )
    
    execution_summary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Resumo da execução"
    )
    
    rag_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Informações sobre o contexto RAG utilizado"
    )
    
    external_docs_used: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Lista dos documentos externos que foram utilizados"
    )
    
    execution_log: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Log detalhado da execução"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="Mensagem de erro, se houver"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp da resposta"
    )

# Schemas para endpoints específicos de contexto externo
class ExternalDocValidationRequest(BaseModel):
    """Schema para validar documentos externos antes da submissão"""
    docs: List[ExternalDoc] = Field(
        ...,
        description="Lista de documentos para validar"
    )

class ExternalDocValidationResponse(BaseModel):
    """Resposta da validação de documentos externos"""
    valid: bool = Field(
        ...,
        description="Se todos os documentos são válidos"
    )
    
    total_docs: int = Field(
        ...,
        description="Total de documentos validados"
    )
    
    total_characters: int = Field(
        ...,
        description="Total de caracteres em todos os documentos"
    )
    
    validation_errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Erros de validação encontrados"
    )
    
    estimated_tokens: int = Field(
        ...,
        description="Estimativa de tokens para processamento"
    )

# Utilitários para trabalhar com documentos externos
class ExternalDocProcessor:
    """Classe auxiliar para processar documentos externos"""
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estima o número de tokens em um texto"""
        # Estimativa simples: ~4 caracteres por token
        return len(text) // 4
    
    @staticmethod
    def validate_docs(docs: List[ExternalDoc]) -> ExternalDocValidationResponse:
        """Valida uma lista de documentos externos"""
        validation_errors = []
        total_characters = 0
        
        for i, doc in enumerate(docs):
            try:
                # Validar tamanho
                if len(doc.text) > 50000:
                    validation_errors.append({
                        "doc_index": i,
                        "src_id": doc.src_id,
                        "error": "Documento excede 50.000 caracteres"
                    })
                
                # Validar conteúdo
                if not doc.text.strip():
                    validation_errors.append({
                        "doc_index": i,
                        "src_id": doc.src_id,
                        "error": "Documento não pode estar vazio"
                    })
                
                total_characters += len(doc.text)
                
            except Exception as e:
                validation_errors.append({
                    "doc_index": i,
                    "src_id": doc.src_id,
                    "error": f"Erro de validação: {str(e)}"
                })
        
        # Verificar limite total
        if total_characters > 500000:  # 500KB total
            validation_errors.append({
                "error": "Total de caracteres excede 500.000 (limite por requisição)"
            })
        
        return ExternalDocValidationResponse(
            valid=len(validation_errors) == 0,
            total_docs=len(docs),
            total_characters=total_characters,
            validation_errors=validation_errors,
            estimated_tokens=ExternalDocProcessor.estimate_tokens(
                " ".join(doc.text for doc in docs)
            )
        )
    
    @staticmethod
    def prepare_for_rag(docs: List[ExternalDoc]) -> List[Dict[str, Any]]:
        """Prepara documentos externos para uso no RAG"""
        prepared_docs = []
        
        for doc in docs:
            prepared_docs.append({
                "src_id": doc.src_id,
                "text": doc.text,
                "meta": doc.meta,
                "priority": doc.priority,
                "source": "external",
                "timestamp": datetime.now().isoformat()
            })
        
        return prepared_docs

# Exemplo de uso
EXAMPLE_REQUEST = {
    "tenant_id": "cliente_acme",
    "task": "draft",
    "doc_type": "peticao",
    "query": "A empresa deve responder por danos morais devido ao vazamento de dados?",
    "use_internal_rag": True,
    "context_docs_external": [
        {
            "src_id": "email_cliente_01",
            "text": "E-mail do cliente reclamando: 'Meus dados foram expostos em um fórum online após o incidente de segurança que vocês notificaram. Estou recebendo spam e tentativas de phishing. Isso é inaceitável.'",
            "meta": {
                "tipo": "comunicacao_cliente",
                "data": "2024-10-26",
                "autor": "João Silva",
                "urgencia": "alta"
            },
            "priority": 0.95
        },
        {
            "src_id": "politica_privacidade_v2",
            "text": "Cláusula 5.2: A nossa empresa se compromete a utilizar as melhores práticas de segurança para proteger os dados dos usuários, mas não se responsabiliza por ataques de terceiros inevitáveis.",
            "meta": {
                "tipo": "documento_interno",
                "versao": "2.1",
                "categoria": "politica_privacidade"
            },
            "priority": 0.9
        }
    ],
    "rag_config": {
        "k_total": 20,
        "enable_personalization": True,
        "personalization_alpha": 0.25,
        "rerank_results": True
    }
}

EXAMPLE_RESPONSE = {
    "success": True,
    "run_id": "uuid-xyz-123",
    "final_document": "PETIÇÃO INICIAL\n\nExmo. Sr. Dr. Juiz...",
    "execution_summary": {
        "total_agents_executed": 5,
        "total_execution_time": 45.2,
        "documents_processed": 22
    },
    "rag_context": {
        "total_documents": 22,
        "internal_documents": 20,
        "external_documents": 2,
        "personalization_applied": True
    },
    "external_docs_used": [
        {
            "src_id": "email_cliente_01",
            "usage_score": 0.95,
            "citation_count": 3
        },
        {
            "src_id": "politica_privacidade_v2",
            "usage_score": 0.87,
            "citation_count": 2
        }
    ]
}
