"""
Configurações para o sistema de personalização por centroides
"""

import os
from typing import Dict, Any, Optional
from pydantic import BaseSettings, Field

class PersonalizationSettings(BaseSettings):
    """Configurações de personalização"""
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379",
        env="REDIS_URL",
        description="URL do Redis para armazenar centroides"
    )
    
    # Centralização de configurações
    centroid_ttl_seconds: int = Field(
        default=7 * 24 * 3600,  # 7 dias
        env="CENTROID_TTL_SECONDS",
        description="TTL dos centroides no Redis (segundos)"
    )
    
    centroid_cache_ttl_seconds: int = Field(
        default=300,  # 5 minutos
        env="CENTROID_CACHE_TTL_SECONDS",
        description="TTL do cache local de centroides (segundos)"
    )
    
    # Personalização
    default_personalization_alpha: float = Field(
        default=0.25,
        env="DEFAULT_PERSONALIZATION_ALPHA",
        description="Força padrão da personalização (0.0-1.0)"
    )
    
    min_personalization_alpha: float = Field(
        default=0.0,
        env="MIN_PERSONALIZATION_ALPHA",
        description="Valor mínimo para alpha de personalização"
    )
    
    max_personalization_alpha: float = Field(
        default=1.0,
        env="MAX_PERSONALIZATION_ALPHA",
        description="Valor máximo para alpha de personalização"
    )
    
    # Busca
    default_k_total: int = Field(
        default=20,
        env="DEFAULT_K_TOTAL",
        description="Número padrão de resultados retornados"
    )
    
    max_k_total: int = Field(
        default=100,
        env="MAX_K_TOTAL",
        description="Número máximo de resultados permitidos"
    )
    
    rrf_k_parameter: int = Field(
        default=60,
        env="RRF_K_PARAMETER",
        description="Parâmetro K para Reciprocal Rank Fusion"
    )
    
    # Cálculo de centroides
    min_vectors_for_centroid: int = Field(
        default=10,
        env="MIN_VECTORS_FOR_CENTROID",
        description="Número mínimo de vetores para calcular centroide"
    )
    
    max_vectors_for_centroid: int = Field(
        default=10000,
        env="MAX_VECTORS_FOR_CENTROID",
        description="Número máximo de vetores para calcular centroide"
    )
    
    centroid_calculation_batch_size: int = Field(
        default=1000,
        env="CENTROID_CALCULATION_BATCH_SIZE",
        description="Tamanho do batch para cálculo de centroides"
    )
    
    # Embedding
    embedding_dimension: int = Field(
        default=768,
        env="EMBEDDING_DIMENSION",
        description="Dimensão dos embeddings"
    )
    
    # Tags temáticas
    default_tags: list = Field(
        default=[
            "contratos_imobiliarios",
            "litigios_tributarios",
            "direito_trabalhista",
            "direito_civil",
            "direito_penal",
            "direito_empresarial",
            "direito_administrativo",
            "direito_constitucional"
        ],
        description="Tags temáticas padrão"
    )
    
    # Inferência de tags
    tag_inference_method: str = Field(
        default="keyword",
        env="TAG_INFERENCE_METHOD",
        description="Método de inferência de tags (keyword, llm, hybrid)"
    )
    
    # Keywords para inferência
    tag_keywords: Dict[str, list] = Field(
        default={
            "contratos_imobiliarios": [
                "imóvel", "casa", "apartamento", "aluguel", "locação",
                "compra", "venda", "propriedade", "terreno", "edificação",
                "habitação", "residencial", "comercial", "iptu"
            ],
            "litigios_tributarios": [
                "imposto", "tributo", "fisco", "receita", "icms", "ipi",
                "irpf", "irpj", "iss", "cofins", "pis", "csll",
                "autuação", "multa", "sonegação", "elisão"
            ],
            "direito_trabalhista": [
                "trabalho", "empregado", "empregador", "salário", "férias",
                "rescisão", "clt", "sindicato", "greve", "fgts",
                "inss", "acidente", "doença", "jornada", "hora extra"
            ],
            "direito_civil": [
                "civil", "família", "divórcio", "sucessão", "herança",
                "responsabilidade", "dano", "contrato", "obrigação",
                "propriedade", "posse", "usufruto", "servidão"
            ],
            "direito_penal": [
                "crime", "penal", "processo", "denúncia", "prisão",
                "sentença", "pena", "delito", "furto", "roubo",
                "homicídio", "lesão", "estelionato", "tráfico"
            ],
            "direito_empresarial": [
                "empresa", "societário", "sociedade", "negócio", "comercial",
                "cnpj", "falência", "recuperação", "sócio", "quotas",
                "ações", "mercado", "concorrência", "marca", "patente"
            ],
            "direito_administrativo": [
                "administrativo", "público", "licitação", "concurso",
                "servidor", "autarquia", "fundação", "agência",
                "poder", "estado", "município", "união", "decreto"
            ],
            "direito_constitucional": [
                "constitucional", "constituição", "direitos", "garantias",
                "liberdades", "cidadania", "democracia", "república",
                "federação", "supremo", "stf", "stj", "mandado"
            ]
        },
        description="Palavras-chave para inferência de tags"
    )
    
    # Monitoramento
    enable_metrics: bool = Field(
        default=True,
        env="ENABLE_PERSONALIZATION_METRICS",
        description="Habilitar coleta de métricas de personalização"
    )
    
    metrics_retention_days: int = Field(
        default=30,
        env="METRICS_RETENTION_DAYS",
        description="Retenção de métricas em dias"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        env="PERSONALIZATION_LOG_LEVEL",
        description="Nível de logging para personalização"
    )
    
    enable_debug_logging: bool = Field(
        default=False,
        env="ENABLE_PERSONALIZATION_DEBUG",
        description="Habilitar logging debug para personalização"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Instância global das configurações
_personalization_settings: Optional[PersonalizationSettings] = None

def get_personalization_settings() -> PersonalizationSettings:
    """Retorna configurações de personalização (singleton)"""
    global _personalization_settings
    if _personalization_settings is None:
        _personalization_settings = PersonalizationSettings()
    return _personalization_settings

def validate_personalization_alpha(alpha: float) -> float:
    """Valida e normaliza o valor de alpha"""
    settings = get_personalization_settings()
    
    if alpha < settings.min_personalization_alpha:
        return settings.min_personalization_alpha
    elif alpha > settings.max_personalization_alpha:
        return settings.max_personalization_alpha
    else:
        return alpha

def validate_k_total(k: int) -> int:
    """Valida e normaliza o valor de k_total"""
    settings = get_personalization_settings()
    
    if k < 1:
        return settings.default_k_total
    elif k > settings.max_k_total:
        return settings.max_k_total
    else:
        return k

def get_tag_keywords(tag: str) -> list:
    """Retorna palavras-chave para uma tag"""
    settings = get_personalization_settings()
    return settings.tag_keywords.get(tag, [])

def get_all_tags() -> list:
    """Retorna todas as tags disponíveis"""
    settings = get_personalization_settings()
    return settings.default_tags

# Configurações específicas por ambiente
class DevelopmentSettings(PersonalizationSettings):
    """Configurações para desenvolvimento"""
    
    log_level: str = "DEBUG"
    enable_debug_logging: bool = True
    centroid_ttl_seconds: int = 3600  # 1 hora
    centroid_cache_ttl_seconds: int = 60  # 1 minuto

class ProductionSettings(PersonalizationSettings):
    """Configurações para produção"""
    
    log_level: str = "INFO"
    enable_debug_logging: bool = False
    centroid_ttl_seconds: int = 7 * 24 * 3600  # 7 dias
    centroid_cache_ttl_seconds: int = 300  # 5 minutos

def get_environment_settings() -> PersonalizationSettings:
    """Retorna configurações baseadas no ambiente"""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionSettings()
    elif environment == "development":
        return DevelopmentSettings()
    else:
        return PersonalizationSettings()

# Configurações de exemplo para .env
EXAMPLE_ENV_CONFIG = """
# Configurações de Personalização por Centroides

# Redis
REDIS_URL=redis://localhost:6379

# Personalização
DEFAULT_PERSONALIZATION_ALPHA=0.25
MIN_PERSONALIZATION_ALPHA=0.0
MAX_PERSONALIZATION_ALPHA=1.0

# Busca
DEFAULT_K_TOTAL=20
MAX_K_TOTAL=100
RRF_K_PARAMETER=60

# Cálculo de centroides
MIN_VECTORS_FOR_CENTROID=10
MAX_VECTORS_FOR_CENTROID=10000
CENTROID_CALCULATION_BATCH_SIZE=1000

# Embedding
EMBEDDING_DIMENSION=768

# Inferência de tags
TAG_INFERENCE_METHOD=keyword

# Monitoramento
ENABLE_PERSONALIZATION_METRICS=true
METRICS_RETENTION_DAYS=30

# Logging
PERSONALIZATION_LOG_LEVEL=INFO
ENABLE_PERSONALIZATION_DEBUG=false
"""

if __name__ == "__main__":
    # Exemplo de uso
    settings = get_personalization_settings()
    print(f"Configurações carregadas:")
    print(f"  - Redis URL: {settings.redis_url}")
    print(f"  - Alpha padrão: {settings.default_personalization_alpha}")
    print(f"  - K total padrão: {settings.default_k_total}")
    print(f"  - Tags disponíveis: {len(settings.default_tags)}")
    
    # Exemplo de validação
    print(f"\nValidações:")
    print(f"  - Alpha 0.5 → {validate_personalization_alpha(0.5)}")
    print(f"  - Alpha 1.5 → {validate_personalization_alpha(1.5)}")
    print(f"  - K 50 → {validate_k_total(50)}")
    print(f"  - K 200 → {validate_k_total(200)}")
    
    # Exemplo de configuração de ambiente
    print(f"\nExemplo de .env:")
    print(EXAMPLE_ENV_CONFIG)
