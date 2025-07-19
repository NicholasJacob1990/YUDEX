# Configuração do Sistema de Contexto Externo

## Configuração de Produção

### 1. Variáveis de Ambiente
```bash
# Limites de processamento
EXTERNAL_CONTEXT_MAX_DOCS=10
EXTERNAL_CONTEXT_MAX_DOC_SIZE=524288  # 512KB
EXTERNAL_CONTEXT_MAX_TOTAL_SIZE=2097152  # 2MB
EXTERNAL_CONTEXT_CHUNK_SIZE=1000
EXTERNAL_CONTEXT_CHUNK_OVERLAP=200

# Cache e performance
EXTERNAL_CONTEXT_CACHE_TTL=3600  # 1 hora
EXTERNAL_CONTEXT_PROCESSING_TIMEOUT=30  # 30 segundos

# Personalização
PERSONALIZATION_DEFAULT_ALPHA=0.25
PERSONALIZATION_ENABLE_BY_DEFAULT=true

# Logging
LOG_LEVEL=INFO
EXTERNAL_CONTEXT_LOG_REQUESTS=true
```

### 2. Configuração Redis
```python
# config/settings.py
import os
from pydantic_settings import BaseSettings

class ExternalContextSettings(BaseSettings):
    """Configurações do sistema de contexto externo"""
    
    # Limites de processamento
    max_docs: int = int(os.getenv("EXTERNAL_CONTEXT_MAX_DOCS", "10"))
    max_doc_size: int = int(os.getenv("EXTERNAL_CONTEXT_MAX_DOC_SIZE", "524288"))
    max_total_size: int = int(os.getenv("EXTERNAL_CONTEXT_MAX_TOTAL_SIZE", "2097152"))
    
    # Chunking
    chunk_size: int = int(os.getenv("EXTERNAL_CONTEXT_CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("EXTERNAL_CONTEXT_CHUNK_OVERLAP", "200"))
    min_chunk_size: int = int(os.getenv("EXTERNAL_CONTEXT_MIN_CHUNK_SIZE", "100"))
    
    # Cache
    cache_ttl: int = int(os.getenv("EXTERNAL_CONTEXT_CACHE_TTL", "3600"))
    enable_cache: bool = os.getenv("EXTERNAL_CONTEXT_ENABLE_CACHE", "true").lower() == "true"
    
    # Performance
    processing_timeout: int = int(os.getenv("EXTERNAL_CONTEXT_PROCESSING_TIMEOUT", "30"))
    max_concurrent_requests: int = int(os.getenv("EXTERNAL_CONTEXT_MAX_CONCURRENT", "5"))
    
    # Personalização
    default_personalization_alpha: float = float(os.getenv("PERSONALIZATION_DEFAULT_ALPHA", "0.25"))
    enable_personalization_by_default: bool = os.getenv("PERSONALIZATION_ENABLE_BY_DEFAULT", "true").lower() == "true"
    
    # Logging
    log_requests: bool = os.getenv("EXTERNAL_CONTEXT_LOG_REQUESTS", "true").lower() == "true"
    log_processing_time: bool = os.getenv("EXTERNAL_CONTEXT_LOG_PROCESSING_TIME", "true").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Instância global
external_context_settings = ExternalContextSettings()
```

### 3. Configuração de Middleware
```python
# app/middleware/external_context.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger(__name__)

class ExternalContextMiddleware(BaseHTTPMiddleware):
    """Middleware para monitoramento de contexto externo"""
    
    async def dispatch(self, request: Request, call_next):
        # Verificar se é requisição de contexto externo
        if "/external-context/" in str(request.url):
            start_time = time.time()
            
            # Log da requisição
            if external_context_settings.log_requests:
                logger.info(f"External context request: {request.method} {request.url}")
            
            # Processar requisição
            response = await call_next(request)
            
            # Log do tempo de processamento
            if external_context_settings.log_processing_time:
                processing_time = time.time() - start_time
                logger.info(f"External context processing time: {processing_time:.2f}s")
                
                # Adicionar header com tempo de processamento
                response.headers["X-Processing-Time"] = str(processing_time)
            
            return response
        else:
            return await call_next(request)
```

### 4. Configuração de Cache
```python
# app/core/cache.py
import redis
import json
import hashlib
from typing import Optional, Dict, Any
from config.settings import external_context_settings

class ExternalContextCache:
    """Cache para documentos externos processados"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            decode_responses=True
        )
    
    def _generate_key(self, docs: list) -> str:
        """Gera chave única para conjunto de documentos"""
        docs_str = json.dumps(
            [{"src_id": doc.src_id, "text": doc.text} for doc in docs],
            sort_keys=True
        )
        return f"external_context:{hashlib.md5(docs_str.encode()).hexdigest()}"
    
    async def get_processed_docs(self, docs: list) -> Optional[list]:
        """Recupera documentos processados do cache"""
        if not external_context_settings.enable_cache:
            return None
        
        key = self._generate_key(docs)
        cached_data = self.redis_client.get(key)
        
        if cached_data:
            return json.loads(cached_data)
        
        return None
    
    async def set_processed_docs(self, docs: list, processed_docs: list):
        """Armazena documentos processados no cache"""
        if not external_context_settings.enable_cache:
            return
        
        key = self._generate_key(docs)
        self.redis_client.setex(
            key,
            external_context_settings.cache_ttl,
            json.dumps(processed_docs)
        )
    
    async def clear_cache(self):
        """Limpa cache de contexto externo"""
        keys = self.redis_client.keys("external_context:*")
        if keys:
            self.redis_client.delete(*keys)

# Instância global
external_context_cache = ExternalContextCache()
```

## Configuração de Desenvolvimento

### 1. Docker Compose
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  harvey-backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - EXTERNAL_CONTEXT_MAX_DOCS=5
      - EXTERNAL_CONTEXT_MAX_DOC_SIZE=262144  # 256KB para dev
      - EXTERNAL_CONTEXT_ENABLE_CACHE=true
      - LOG_LEVEL=DEBUG
      - EXTERNAL_CONTEXT_LOG_REQUESTS=true
    volumes:
      - ./app:/app
      - ./tests:/tests
      - ./docs:/docs
    depends_on:
      - redis
      - postgres
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: harvey_dev
      POSTGRES_USER: harvey
      POSTGRES_PASSWORD: harvey123
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  redis_data:
  postgres_data:
```

### 2. Configuração de Testes
```python
# tests/conftest.py
import pytest
import asyncio
from unittest.mock import Mock, patch
from app.models.schema_api import ExternalDoc
from app.core.cache import ExternalContextCache
from config.settings import external_context_settings

@pytest.fixture
def external_docs():
    """Fixture com documentos externos para testes"""
    return [
        ExternalDoc(
            src_id="test_doc_1",
            text="Documento de teste 1 com conteúdo relevante para análise.",
            meta={"tipo": "teste", "categoria": "unitario"}
        ),
        ExternalDoc(
            src_id="test_doc_2",
            text="Documento de teste 2 com informações adicionais para validação.",
            meta={"tipo": "teste", "categoria": "integracao"}
        )
    ]

@pytest.fixture
def mock_settings():
    """Fixture com configurações mockadas para testes"""
    with patch.object(external_context_settings, 'max_docs', 3), \
         patch.object(external_context_settings, 'max_doc_size', 1000), \
         patch.object(external_context_settings, 'enable_cache', False):
        yield external_context_settings

@pytest.fixture
def mock_cache():
    """Fixture com cache mockado"""
    cache = Mock(spec=ExternalContextCache)
    cache.get_processed_docs.return_value = None
    cache.set_processed_docs.return_value = None
    return cache

@pytest.fixture
def event_loop():
    """Fixture para event loop do asyncio"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

### 3. Configuração de Logging
```python
# config/logging.py
import logging
import sys
from logging.handlers import RotatingFileHandler
from config.settings import external_context_settings

def setup_logging():
    """Configura logging para contexto externo"""
    
    # Configurar logger principal
    logger = logging.getLogger("external_context")
    logger.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para arquivo (produção)
    if not external_context_settings.log_requests:
        file_handler = RotatingFileHandler(
            'logs/external_context.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# Configurar logging global
setup_logging()
```

## Configuração de Monitoramento

### 1. Métricas Prometheus
```python
# app/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps

# Métricas de contexto externo
external_context_requests = Counter(
    'external_context_requests_total',
    'Total de requisições com contexto externo',
    ['tenant_id', 'status']
)

external_context_processing_time = Histogram(
    'external_context_processing_seconds',
    'Tempo de processamento de contexto externo',
    ['operation']
)

external_context_docs_processed = Counter(
    'external_context_docs_processed_total',
    'Total de documentos externos processados',
    ['tenant_id']
)

external_context_validation_errors = Counter(
    'external_context_validation_errors_total',
    'Total de erros de validação',
    ['error_type']
)

def track_external_context_metrics(operation: str):
    """Decorator para rastrear métricas de contexto externo"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                external_context_requests.labels(
                    tenant_id=kwargs.get('tenant_id', 'unknown'),
                    status='success'
                ).inc()
                return result
            except Exception as e:
                external_context_requests.labels(
                    tenant_id=kwargs.get('tenant_id', 'unknown'),
                    status='error'
                ).inc()
                raise
            finally:
                processing_time = time.time() - start_time
                external_context_processing_time.labels(
                    operation=operation
                ).observe(processing_time)
        
        return wrapper
    return decorator
```

### 2. Health Checks
```python
# app/health/external_context.py
from fastapi import HTTPException
from app.core.cache import external_context_cache
from app.models.schema_api import ExternalDoc, ExternalDocProcessor

async def check_external_context_health():
    """Verifica saúde do sistema de contexto externo"""
    health_status = {
        "status": "healthy",
        "components": {},
        "timestamp": time.time()
    }
    
    # Verificar cache
    try:
        await external_context_cache.redis_client.ping()
        health_status["components"]["cache"] = "healthy"
    except Exception as e:
        health_status["components"]["cache"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Verificar processamento
    try:
        test_doc = ExternalDoc(
            src_id="health_check",
            text="Teste de saúde do sistema",
            meta={"tipo": "health"}
        )
        
        validation = ExternalDocProcessor.validate_docs([test_doc])
        if validation.valid:
            health_status["components"]["processor"] = "healthy"
        else:
            health_status["components"]["processor"] = "unhealthy: validation failed"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["processor"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status
```

## Configuração de Segurança

### 1. Rate Limiting
```python
# app/middleware/rate_limit.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time
import redis
from config.settings import external_context_settings

class ExternalContextRateLimit(BaseHTTPMiddleware):
    """Rate limiting para contexto externo"""
    
    def __init__(self, app, redis_client):
        super().__init__(app)
        self.redis_client = redis_client
        self.max_requests = external_context_settings.max_concurrent_requests
        self.time_window = 60  # 1 minuto
    
    async def dispatch(self, request: Request, call_next):
        if "/external-context/" in str(request.url):
            tenant_id = self._extract_tenant_id(request)
            
            if not await self._check_rate_limit(tenant_id):
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded for external context"
                )
        
        return await call_next(request)
    
    async def _check_rate_limit(self, tenant_id: str) -> bool:
        """Verifica se o tenant está dentro do rate limit"""
        key = f"rate_limit:external_context:{tenant_id}"
        current_time = int(time.time())
        
        # Usar sliding window
        pipe = self.redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, current_time - self.time_window)
        pipe.zcard(key)
        pipe.zadd(key, {str(current_time): current_time})
        pipe.expire(key, self.time_window)
        
        results = pipe.execute()
        current_requests = results[1]
        
        return current_requests < self.max_requests
```

### 2. Validação de Conteúdo
```python
# app/security/content_validation.py
import re
from typing import List
from app.models.schema_api import ExternalDoc

class ContentValidator:
    """Validador de conteúdo para documentos externos"""
    
    # Patterns suspeitos
    SUSPICIOUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Scripts
        r'javascript:',               # URLs Javascript
        r'data:text/html',           # Data URLs HTML
        r'vbscript:',                # VBScript
        r'on\w+\s*=',                # Event handlers
    ]
    
    # Palavras proibidas (exemplo)
    FORBIDDEN_WORDS = [
        'confidential_internal',
        'secret_key',
        'password',
        'token_auth'
    ]
    
    @classmethod
    def validate_content(cls, docs: List[ExternalDoc]) -> List[str]:
        """Valida conteúdo dos documentos"""
        errors = []
        
        for doc in docs:
            # Verificar patterns suspeitos
            for pattern in cls.SUSPICIOUS_PATTERNS:
                if re.search(pattern, doc.text, re.IGNORECASE):
                    errors.append(f"Documento {doc.src_id}: conteúdo suspeito detectado")
                    break
            
            # Verificar palavras proibidas
            for word in cls.FORBIDDEN_WORDS:
                if word.lower() in doc.text.lower():
                    errors.append(f"Documento {doc.src_id}: contém conteúdo proibido")
                    break
        
        return errors
```

## Configuração de Backup

### 1. Backup de Cache
```python
# scripts/backup_external_context.py
import json
import gzip
from datetime import datetime
from app.core.cache import external_context_cache

async def backup_external_context_cache():
    """Faz backup do cache de contexto externo"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/external_context_cache_{timestamp}.json.gz"
    
    # Obter todas as chaves do cache
    keys = external_context_cache.redis_client.keys("external_context:*")
    
    backup_data = {}
    for key in keys:
        data = external_context_cache.redis_client.get(key)
        if data:
            backup_data[key] = json.loads(data)
    
    # Salvar backup comprimido
    with gzip.open(backup_file, 'wt') as f:
        json.dump(backup_data, f, indent=2)
    
    print(f"Backup salvo em: {backup_file}")
    print(f"Chaves backup: {len(backup_data)}")
```

### 2. Cron Job para Limpeza
```bash
# crontab -e
# Limpeza diária do cache às 2h da manhã
0 2 * * * /usr/bin/python3 /app/scripts/cleanup_external_context.py

# Backup semanal aos domingos às 3h
0 3 * * 0 /usr/bin/python3 /app/scripts/backup_external_context.py
```

Esta configuração completa garante que o sistema de contexto externo funcione de forma robusta, segura e monitorada em produção.
