#!/bin/bash

# Setup script para Harvey Backend
# Configura ambiente de desenvolvimento

echo "🚀 Configurando Harvey Backend..."

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Instale Python 3.8+ primeiro."
    exit 1
fi

# Criar ambiente virtual se não existir
if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python3 -m venv venv
fi

# Ativar ambiente virtual
echo "🔧 Ativando ambiente virtual..."
source venv/bin/activate

# Atualizar pip
echo "⬆️ Atualizando pip..."
pip install --upgrade pip

# Instalar dependências
echo "📚 Instalando dependências..."
pip install -r requirements.txt

# Criar arquivo .env se não existir
if [ ! -f ".env" ]; then
    echo "⚙️ Criando arquivo .env..."
    cp .env.example .env
    echo "✏️ Edite o arquivo .env com suas configurações"
fi

echo "✅ Setup concluído!"
echo ""
echo "Para usar o Harvey Backend:"
echo "1. Ative o ambiente virtual: source venv/bin/activate"
echo "2. Configure o arquivo .env com suas API keys"
echo "3. Execute: python example_usage.py"
echo "4. Ou inicie o servidor: uvicorn app.main:app --reload"
