#!/bin/bash

# Script de inicialização para Harvey Backend
# Este script configura o ambiente de desenvolvimento completo

set -e

echo "🚀 Iniciando configuração do Harvey Backend..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para logs
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verifica se o Docker está rodando
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        error "Docker não está rodando. Inicie o Docker e tente novamente."
        exit 1
    fi
    log "Docker está rodando ✓"
}

# Verifica se o Docker Compose está disponível
check_docker_compose() {
    if ! command -v docker-compose > /dev/null 2>&1; then
        error "Docker Compose não está instalado."
        exit 1
    fi
    log "Docker Compose está disponível ✓"
}

# Verifica se o Python está instalado
check_python() {
    if ! command -v python3 > /dev/null 2>&1; then
        error "Python 3 não está instalado."
        exit 1
    fi
    log "Python 3 está disponível ✓"
}

# Cria arquivo .env se não existir
create_env() {
    if [ ! -f .env ]; then
        log "Criando arquivo .env a partir do .env.example..."
        cp .env.example .env
        warn "Arquivo .env criado. Configure as variáveis necessárias."
    else
        log "Arquivo .env já existe ✓"
    fi
}

# Instala dependências Python
install_dependencies() {
    log "Instalando dependências Python..."
    
    # Verifica se existe venv
    if [ ! -d "venv" ]; then
        log "Criando ambiente virtual..."
        python3 -m venv venv
    fi
    
    # Ativa ambiente virtual
    source venv/bin/activate
    
    # Instala dependências
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    
    log "Dependências Python instaladas ✓"
}

# Constrói imagens Docker
build_images() {
    log "Construindo imagens Docker..."
    docker-compose -f docker-compose.dev.yml build
    log "Imagens Docker construídas ✓"
}

# Inicia serviços de infraestrutura
start_infrastructure() {
    log "Iniciando serviços de infraestrutura..."
    
    # Para serviços se já estiverem rodando
    docker-compose -f docker-compose.dev.yml down
    
    # Inicia serviços
    docker-compose -f docker-compose.dev.yml up -d postgres redis qdrant
    
    log "Aguardando serviços ficarem prontos..."
    sleep 30
    
    # Verifica se serviços estão rodando
    if ! docker-compose -f docker-compose.dev.yml ps postgres | grep -q "Up"; then
        error "PostgreSQL não está rodando"
        exit 1
    fi
    
    if ! docker-compose -f docker-compose.dev.yml ps redis | grep -q "Up"; then
        error "Redis não está rodando"
        exit 1
    fi
    
    if ! docker-compose -f docker-compose.dev.yml ps qdrant | grep -q "Up"; then
        error "Qdrant não está rodando"
        exit 1
    fi
    
    log "Serviços de infraestrutura iniciados ✓"
}

# Executa migrações do banco
run_migrations() {
    log "Executando migrações do banco de dados..."
    
    # Ativa ambiente virtual
    source venv/bin/activate
    
    # Executa migrações
    alembic upgrade head
    
    log "Migrações executadas ✓"
}

# Executa testes
run_tests() {
    log "Executando testes..."
    
    # Ativa ambiente virtual
    source venv/bin/activate
    
    # Executa testes unitários
    pytest tests/unit -v
    
    log "Testes executados ✓"
}

# Inicia aplicação
start_application() {
    log "Iniciando aplicação Harvey Backend..."
    
    # Ativa ambiente virtual
    source venv/bin/activate
    
    # Inicia aplicação em background
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > app.log 2>&1 &
    
    # Salva PID
    echo $! > app.pid
    
    log "Aplicação iniciada em background ✓"
    log "PID salvo em app.pid"
    log "Logs em app.log"
}

# Verifica se aplicação está rodando
check_application() {
    log "Verificando se aplicação está rodando..."
    
    # Aguarda aplicação iniciar
    sleep 10
    
    # Verifica endpoint de health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "Aplicação está rodando e saudável ✓"
    else
        error "Aplicação não está respondendo"
        exit 1
    fi
}

# Mostra informações finais
show_info() {
    echo ""
    echo "🎉 Harvey Backend configurado com sucesso!"
    echo ""
    echo "📋 Informações importantes:"
    echo "  • API: http://localhost:8000"
    echo "  • Docs: http://localhost:8000/docs"
    echo "  • Health: http://localhost:8000/health"
    echo "  • Metrics: http://localhost:8000/metrics"
    echo ""
    echo "🛠️ Comandos úteis:"
    echo "  • make help - Mostra todos os comandos disponíveis"
    echo "  • make test - Executa testes"
    echo "  • make lint - Verifica qualidade do código"
    echo "  • make docker-compose-logs - Mostra logs dos serviços"
    echo ""
    echo "🔧 Serviços rodando:"
    echo "  • PostgreSQL: localhost:5432"
    echo "  • Redis: localhost:6379"
    echo "  • Qdrant: localhost:6333"
    echo ""
    echo "📊 Monitoramento (opcional):"
    echo "  • make monitor-all - Inicia Prometheus e Grafana"
    echo "  • Prometheus: http://localhost:9090"
    echo "  • Grafana: http://localhost:3000"
    echo ""
}

# Função de limpeza
cleanup() {
    log "Limpando ambiente..."
    
    # Para aplicação se estiver rodando
    if [ -f app.pid ]; then
        kill $(cat app.pid) 2>/dev/null || true
        rm -f app.pid
    fi
    
    # Para serviços Docker
    docker-compose -f docker-compose.dev.yml down
    
    log "Ambiente limpo ✓"
}

# Função principal
main() {
    # Verifica argumentos
    case "${1:-setup}" in
        "setup")
            log "Iniciando configuração completa..."
            check_docker
            check_docker_compose
            check_python
            create_env
            install_dependencies
            build_images
            start_infrastructure
            run_migrations
            run_tests
            start_application
            check_application
            show_info
            ;;
        "start")
            log "Iniciando serviços..."
            start_infrastructure
            start_application
            check_application
            log "Serviços iniciados ✓"
            ;;
        "stop")
            log "Parando serviços..."
            cleanup
            ;;
        "restart")
            log "Reiniciando serviços..."
            cleanup
            sleep 5
            start_infrastructure
            start_application
            check_application
            log "Serviços reiniciados ✓"
            ;;
        "test")
            log "Executando testes..."
            run_tests
            ;;
        "help")
            echo "Uso: $0 {setup|start|stop|restart|test|help}"
            echo ""
            echo "Comandos:"
            echo "  setup   - Configuração completa do ambiente"
            echo "  start   - Inicia serviços"
            echo "  stop    - Para serviços"
            echo "  restart - Reinicia serviços"
            echo "  test    - Executa testes"
            echo "  help    - Mostra esta ajuda"
            ;;
        *)
            error "Comando inválido: $1"
            echo "Use: $0 help"
            exit 1
            ;;
    esac
}

# Trap para limpeza em caso de interrupção
trap cleanup EXIT

# Executa função principal
main "$@"
