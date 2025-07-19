# Harvey Backend - Makefile
# Comandos para desenvolvimento, build e deploy

.PHONY: help install test lint format build run docker-build docker-run deploy clean

# Variáveis
PYTHON = python3
PIP = pip3
DOCKER_IMAGE = harvey-backend
DOCKER_TAG = latest
HELM_CHART = ./helm/harvey
NAMESPACE = production

# Cores para output
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

# Comando padrão
help: ## Mostra esta ajuda
	@echo "$(GREEN)Harvey Backend - Comandos Disponíveis$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

## Desenvolvimento
install: ## Instala dependências de desenvolvimento
	@echo "$(GREEN)Instalando dependências...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)Dependências instaladas com sucesso!$(NC)"

install-prod: ## Instala apenas dependências de produção
	@echo "$(GREEN)Instalando dependências de produção...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)Dependências de produção instaladas!$(NC)"

run: ## Executa a aplicação em modo desenvolvimento
	@echo "$(GREEN)Iniciando Harvey Backend...$(NC)"
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-prod: ## Executa a aplicação em modo produção
	@echo "$(GREEN)Iniciando Harvey Backend (produção)...$(NC)"
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

## Qualidade de Código
lint: ## Executa linting com ruff
	@echo "$(GREEN)Executando linting...$(NC)"
	ruff check .
	@echo "$(GREEN)Linting concluído!$(NC)"

lint-fix: ## Executa linting e corrige problemas automaticamente
	@echo "$(GREEN)Executando linting com correção automática...$(NC)"
	ruff check . --fix
	@echo "$(GREEN)Linting com correção concluído!$(NC)"

format: ## Formata código com black
	@echo "$(GREEN)Formatando código...$(NC)"
	black .
	@echo "$(GREEN)Formatação concluída!$(NC)"

format-check: ## Verifica formatação sem modificar
	@echo "$(GREEN)Verificando formatação...$(NC)"
	black --check --diff .

type-check: ## Verifica tipos com mypy
	@echo "$(GREEN)Verificando tipos...$(NC)"
	mypy app/

security-check: ## Verifica segurança com bandit
	@echo "$(GREEN)Verificando segurança...$(NC)"
	bandit -r app/ -f json -o security-report.json
	@echo "$(GREEN)Relatório de segurança salvo em security-report.json$(NC)"

quality: lint format type-check security-check ## Executa todas as verificações de qualidade

## Testes
test: ## Executa todos os testes
	@echo "$(GREEN)Executando testes...$(NC)"
	pytest

test-unit: ## Executa apenas testes unitários
	@echo "$(GREEN)Executando testes unitários...$(NC)"
	pytest tests/unit

test-integration: ## Executa apenas testes de integração
	@echo "$(GREEN)Executando testes de integração...$(NC)"
	pytest tests/integration

test-coverage: ## Executa testes com cobertura
	@echo "$(GREEN)Executando testes com cobertura...$(NC)"
	pytest --cov=app --cov-report=html --cov-report=term

test-watch: ## Executa testes em modo watch
	@echo "$(GREEN)Executando testes em modo watch...$(NC)"
	pytest-watch

## Banco de Dados
db-upgrade: ## Executa migrações do banco
	@echo "$(GREEN)Executando migrações...$(NC)"
	alembic upgrade head

db-downgrade: ## Desfaz última migração
	@echo "$(YELLOW)Desfazendo última migração...$(NC)"
	alembic downgrade -1

db-migration: ## Cria nova migração (uso: make db-migration NAME="nome_da_migracao")
	@echo "$(GREEN)Criando migração: $(NAME)$(NC)"
	alembic revision --autogenerate -m "$(NAME)"

db-reset: ## Reseta banco de dados (CUIDADO!)
	@echo "$(RED)ATENÇÃO: Isso vai apagar todos os dados!$(NC)"
	@read -p "Tem certeza? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		alembic downgrade base; \
		alembic upgrade head; \
		echo "$(GREEN)Banco resetado!$(NC)"; \
	else \
		echo "$(YELLOW)Operação cancelada.$(NC)"; \
	fi

## Docker
docker-build: ## Constrói imagem Docker
	@echo "$(GREEN)Construindo imagem Docker...$(NC)"
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

docker-build-dev: ## Constrói imagem Docker para desenvolvimento
	@echo "$(GREEN)Construindo imagem Docker (desenvolvimento)...$(NC)"
	docker build --target development -t $(DOCKER_IMAGE):dev .

docker-run: ## Executa container Docker
	@echo "$(GREEN)Executando container Docker...$(NC)"
	docker run -p 8000:8000 --env-file .env.example $(DOCKER_IMAGE):$(DOCKER_TAG)

docker-compose-up: ## Sobe ambiente completo com Docker Compose
	@echo "$(GREEN)Subindo ambiente completo...$(NC)"
	docker-compose -f docker-compose.dev.yml up -d

docker-compose-down: ## Derruba ambiente Docker Compose
	@echo "$(GREEN)Derrubando ambiente...$(NC)"
	docker-compose -f docker-compose.dev.yml down

docker-compose-logs: ## Mostra logs do Docker Compose
	@echo "$(GREEN)Mostrando logs...$(NC)"
	docker-compose -f docker-compose.dev.yml logs -f

docker-compose-build: ## Reconstrói containers do Docker Compose
	@echo "$(GREEN)Reconstruindo containers...$(NC)"
	docker-compose -f docker-compose.dev.yml build

## Personalização e Centroides
centroids-calculate: ## Calcula centroides para um tenant (uso: make centroids-calculate TENANT=cliente_acme)
	@echo "$(GREEN)Calculando centroides para tenant: $(TENANT)$(NC)"
	$(PYTHON) scripts/calculate_centroids.py --tenant $(TENANT)

centroids-calculate-all: ## Calcula centroides para todos os tenants
	@echo "$(GREEN)Calculando centroides para todos os tenants...$(NC)"
	$(PYTHON) scripts/calculate_centroids.py --all

centroids-stats: ## Mostra estatísticas dos centroides
	@echo "$(GREEN)Mostrando estatísticas dos centroides...$(NC)"
	$(PYTHON) scripts/calculate_centroids.py --stats

centroids-test: ## Testa o sistema de personalização
	@echo "$(GREEN)Testando sistema de personalização...$(NC)"
	$(PYTHON) -c "import asyncio; from app.core.personalization import test_personalization; asyncio.run(test_personalization())"

rag-test: ## Testa o sistema de busca federada
	@echo "$(GREEN)Testando sistema de busca federada...$(NC)"
	$(PYTHON) -c "import asyncio; from app.core.rag_bridge import test_federated_search; asyncio.run(test_federated_search())"

centroids-load-test: ## Executa teste de carga no sistema de personalização
	@echo "$(GREEN)Executando teste de carga de personalização...$(NC)"
	$(PYTHON) scripts/test_personalization_load.py --tenants 5 --queries 50 --concurrency 10 --output load_test_report.txt

centroids-load-test-full: ## Executa teste de carga completo com centroides
	@echo "$(GREEN)Executando teste de carga completo...$(NC)"
	$(PYTHON) scripts/test_personalization_load.py --tenants 10 --queries 100 --concurrency 20 --test-centroids --output full_load_test_report.txt
	docker-compose -f docker-compose.dev.yml build

## Kubernetes/Helm
k8s-deploy: ## Deploy no Kubernetes com Helm
	@echo "$(GREEN)Fazendo deploy no Kubernetes...$(NC)"
	helm upgrade --install harvey-backend $(HELM_CHART) \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--wait

k8s-deploy-dev: ## Deploy no ambiente de desenvolvimento
	@echo "$(GREEN)Fazendo deploy no desenvolvimento...$(NC)"
	helm upgrade --install harvey-dev $(HELM_CHART) \
		--namespace development \
		--create-namespace \
		--set environment=development \
		--set replicaCount=1 \
		--wait

k8s-status: ## Verifica status do deployment
	@echo "$(GREEN)Verificando status do deployment...$(NC)"
	kubectl get pods -n $(NAMESPACE)
	kubectl get services -n $(NAMESPACE)
	kubectl get ingress -n $(NAMESPACE)

k8s-logs: ## Mostra logs do Kubernetes
	@echo "$(GREEN)Mostrando logs do Kubernetes...$(NC)"
	kubectl logs -n $(NAMESPACE) -l app=harvey-backend --tail=100 -f

k8s-shell: ## Abre shell no pod
	@echo "$(GREEN)Abrindo shell no pod...$(NC)"
	kubectl exec -it -n $(NAMESPACE) deployment/harvey-backend -- /bin/bash

k8s-port-forward: ## Faz port forward da API
	@echo "$(GREEN)Fazendo port forward da API...$(NC)"
	kubectl port-forward -n $(NAMESPACE) svc/harvey-backend 8000:8000

k8s-uninstall: ## Remove deployment do Kubernetes
	@echo "$(RED)Removendo deployment...$(NC)"
	helm uninstall harvey-backend -n $(NAMESPACE)

## Monitoring
monitor-metrics: ## Mostra métricas da aplicação
	@echo "$(GREEN)Mostrando métricas...$(NC)"
	curl -s http://localhost:8000/metrics | grep -E "(harvey_|http_)"

monitor-health: ## Verifica saúde da aplicação
	@echo "$(GREEN)Verificando saúde...$(NC)"
	curl -f http://localhost:8000/health && echo "$(GREEN)API saudável!$(NC)" || echo "$(RED)API com problemas!$(NC)"

monitor-prometheus: ## Abre Prometheus
	@echo "$(GREEN)Abrindo Prometheus...$(NC)"
	open http://localhost:9090

monitor-grafana: ## Abre Grafana
	@echo "$(GREEN)Abrindo Grafana...$(NC)"
	open http://localhost:3000

## Utilitários
clean: ## Limpa arquivos temporários
	@echo "$(GREEN)Limpando arquivos temporários...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "htmlcov" -delete
	find . -type d -name ".mypy_cache" -delete
	find . -type d -name ".ruff_cache" -delete
	@echo "$(GREEN)Limpeza concluída!$(NC)"

generate-docs: ## Gera documentação da API
	@echo "$(GREEN)Gerando documentação...$(NC)"
	$(PYTHON) -c "
import json
from app.main import app
with open('docs/openapi.json', 'w') as f:
    json.dump(app.openapi(), f, indent=2)
"
	@echo "$(GREEN)Documentação gerada em docs/openapi.json$(NC)"

backup-db: ## Faz backup do banco de dados
	@echo "$(GREEN)Fazendo backup do banco...$(NC)"
	@if [ -z "$(DATABASE_URL)" ]; then \
		echo "$(RED)Erro: DATABASE_URL não está definida$(NC)"; \
		exit 1; \
	fi
	pg_dump $(DATABASE_URL) > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Backup concluído!$(NC)"

env-check: ## Verifica variáveis de ambiente
	@echo "$(GREEN)Verificando variáveis de ambiente...$(NC)"
	@$(PYTHON) -c "
import os
required_vars = ['DATABASE_URL', 'REDIS_URL', 'OPENAI_API_KEY']
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    print('$(RED)Variáveis ausentes:', ', '.join(missing), '$(NC)')
else:
    print('$(GREEN)Todas as variáveis estão definidas!$(NC)')
"

## Segurança
security-scan: ## Executa scan de segurança completo
	@echo "$(GREEN)Executando scan de segurança...$(NC)"
	bandit -r app/
	safety check
	@echo "$(GREEN)Scan de segurança concluído!$(NC)"

audit-deps: ## Auditoria de dependências
	@echo "$(GREEN)Auditando dependências...$(NC)"
	pip-audit
	@echo "$(GREEN)Auditoria concluída!$(NC)"

## CI/CD
ci-test: ## Executa testes como no CI
	@echo "$(GREEN)Executando testes como no CI...$(NC)"
	$(MAKE) quality
	$(MAKE) test-coverage
	$(MAKE) security-scan

ci-build: ## Constrói como no CI
	@echo "$(GREEN)Construindo como no CI...$(NC)"
	$(MAKE) docker-build
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) $(DOCKER_IMAGE):ci

pre-commit: ## Executa verificações antes do commit
	@echo "$(GREEN)Executando verificações pre-commit...$(NC)"
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) test-unit
	@echo "$(GREEN)Pronto para commit!$(NC)"

## Relatórios
report-coverage: ## Gera relatório de cobertura HTML
	@echo "$(GREEN)Gerando relatório de cobertura...$(NC)"
	pytest --cov=app --cov-report=html
	@echo "$(GREEN)Relatório disponível em htmlcov/index.html$(NC)"

report-performance: ## Gera relatório de performance
	@echo "$(GREEN)Gerando relatório de performance...$(NC)"
	$(PYTHON) -m pytest tests/performance/ --benchmark-only --benchmark-json=performance-report.json
	@echo "$(GREEN)Relatório salvo em performance-report.json$(NC)"

## Desenvolvimento Avançado
debug: ## Executa em modo debug
	@echo "$(GREEN)Executando em modo debug...$(NC)"
	$(PYTHON) -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

profile: ## Executa com profiling
	@echo "$(GREEN)Executando com profiling...$(NC)"
	$(PYTHON) -m cProfile -o profile_output.prof -m uvicorn app.main:app --host 0.0.0.0 --port 8000

stress-test: ## Executa teste de stress
	@echo "$(GREEN)Executando teste de stress...$(NC)"
	@if command -v artillery >/dev/null 2>&1; then \
		artillery run tests/load/stress-test.yml; \
	else \
		echo "$(RED)Artillery não está instalado. Instale com: npm install -g artillery$(NC)"; \
	fi

## Informações
version: ## Mostra versão atual
	@echo "$(GREEN)Harvey Backend$(NC)"
	@echo "Versão: $(shell grep -E '^version = ' pyproject.toml | cut -d '"' -f2)"
	@echo "Python: $(shell python --version)"
	@echo "Docker: $(shell docker --version)"
	@echo "Kubernetes: $(shell kubectl version --client --short 2>/dev/null || echo 'Não instalado')"

status: ## Mostra status dos serviços
	@echo "$(GREEN)Status dos Serviços$(NC)"
	@echo "API: $(shell curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health || echo 'Indisponível')"
	@echo "Postgres: $(shell pg_isready -q && echo 'Ativo' || echo 'Inativo')"
	@echo "Redis: $(shell redis-cli ping 2>/dev/null || echo 'Inativo')"
	@echo "Qdrant: $(shell curl -s -o /dev/null -w '%{http_code}' http://localhost:6333/health || echo 'Indisponível')"

## Exemplo de uso com parâmetros
MIGRATION_NAME ?= "nova_migracao"
migration: ## Cria nova migração (uso: make migration MIGRATION_NAME="nome")
	@echo "$(GREEN)Criando migração: $(MIGRATION_NAME)$(NC)"
	alembic revision --autogenerate -m "$(MIGRATION_NAME)"

TAG ?= latest
docker-tag: ## Adiciona tag à imagem Docker (uso: make docker-tag TAG="v1.2.3")
	@echo "$(GREEN)Adicionando tag $(TAG) à imagem...$(NC)"
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) $(DOCKER_IMAGE):$(TAG)

## Desenvolvimento local completo
dev-setup: ## Configura ambiente de desenvolvimento completo
	@echo "$(GREEN)Configurando ambiente de desenvolvimento...$(NC)"
	$(MAKE) install
	$(MAKE) docker-compose-up
	@echo "$(YELLOW)Aguardando serviços ficarem prontos...$(NC)"
	sleep 30
	$(MAKE) db-upgrade
	@echo "$(GREEN)Ambiente de desenvolvimento configurado!$(NC)"
	@echo "$(YELLOW)Acesse: http://localhost:8000$(NC)"

dev-reset: ## Reseta ambiente de desenvolvimento
	@echo "$(RED)Resetando ambiente de desenvolvimento...$(NC)"
	$(MAKE) docker-compose-down
	$(MAKE) clean
	$(MAKE) dev-setup

## Monitoramento completo
monitor-all: ## Inicia todos os serviços de monitoramento
	@echo "$(GREEN)Iniciando monitoramento completo...$(NC)"
	docker-compose -f docker-compose.dev.yml --profile monitoring up -d
	@echo "$(GREEN)Monitoramento iniciado!$(NC)"
	@echo "$(YELLOW)Prometheus: http://localhost:9090$(NC)"
	@echo "$(YELLOW)Grafana: http://localhost:3000 (admin/harvey_admin)$(NC)"
