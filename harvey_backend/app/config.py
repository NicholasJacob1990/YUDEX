"""
Configurações da aplicação Harvey Backend
Centraliza todas as configurações do sistema jurídico
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configurações principais da aplicação"""
    
    # API Settings
    app_name: str = "Harvey Backend - Sistema Jurídico IA"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Database Settings
    database_url: str = Field(env="DATABASE_URL", default="sqlite:///./harvey.db")
    
    # Redis Settings
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # Qdrant Vector Database
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_collection: str = Field(default="legal_docs", env="QDRANT_COLLECTION")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    
    # LLM Settings
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    
    # Default Models
    default_embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    default_llm_model: str = Field(default="gpt-4o", env="LLM_MODEL")
    default_analysis_model: str = Field(default="claude-3-5-sonnet-20241022", env="ANALYSIS_MODEL")
    default_critic_model: str = Field(default="claude-3-5-sonnet-20241022", env="CRITIC_MODEL")
    
    # RAG Settings
    max_docs_retrieval: int = Field(default=10, env="MAX_DOCS_RETRIEVAL")
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    
    # Reranking Settings
    rerank_top_k: int = Field(default=5, env="RERANK_TOP_K")
    rerank_model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2", env="RERANK_MODEL")
    
    # External Context Settings
    max_external_docs: int = Field(default=20, env="MAX_EXTERNAL_DOCS")
    external_doc_weight: float = Field(default=0.3, env="EXTERNAL_DOC_WEIGHT")
    
    # Legal Document Processing
    supported_formats: List[str] = Field(default=["pdf", "docx", "txt", "md"], env="SUPPORTED_FORMATS")
    max_file_size_mb: int = Field(default=50, env="MAX_FILE_SIZE_MB")
    
    # ABNT Formatting
    abnt_template_path: str = Field(default="templates/abnt_template.md", env="ABNT_TEMPLATE_PATH")
    citation_style: str = Field(default="ABNT", env="CITATION_STYLE")
    
    # Security
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY", default="your-secret-key-change-in-production")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, env="JWT_EXPIRE_MINUTES")
    
    # Monitoring & Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    
    # Centroid Personalization
    centroid_cache_ttl: int = Field(default=3600, env="CENTROID_CACHE_TTL")  # 1 hour
    max_user_preferences: int = Field(default=100, env="MAX_USER_PREFERENCES")
    
    # LangGraph Workflow
    max_workflow_iterations: int = Field(default=5, env="MAX_WORKFLOW_ITERATIONS")
    workflow_timeout_seconds: int = Field(default=300, env="WORKFLOW_TIMEOUT_SECONDS")
    
    # Performance
    max_concurrent_requests: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    request_timeout_seconds: int = Field(default=120, env="REQUEST_TIMEOUT_SECONDS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Instância global das configurações
settings = Settings()


# Configurações específicas por modelo
MODEL_CONFIGS = {
    "gpt-4o": {
        "max_tokens": 4096,
        "temperature": 0.1,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0
    },
    "claude-3-5-sonnet-20241022": {
        "max_tokens": 4096,
        "temperature": 0.1,
        "top_p": 0.9
    },
    "gemini-1.5-pro": {
        "max_tokens": 4096,
        "temperature": 0.1,
        "top_p": 0.9
    }
}

# Configurações de tipos de documento
DOCUMENT_TYPE_CONFIGS = {
    "parecer": {
        "sections": ["fatos", "analise", "fundamentacao", "conclusao"],
        "min_length": 500,
        "max_length": 5000,
        "citation_required": True
    },
    "memorando": {
        "sections": ["introducao", "desenvolvimento", "conclusao"],
        "min_length": 300,
        "max_length": 2000,
        "citation_required": False
    },
    "peticao": {
        "sections": ["preambulo", "fatos", "direito", "pedidos"],
        "min_length": 1000,
        "max_length": 10000,
        "citation_required": True
    }
}
