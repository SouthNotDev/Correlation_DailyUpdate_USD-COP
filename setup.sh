#!/bin/bash

# Setup Script para Análisis Diario USD/COP con LLM
# Este script configura el entorno para ejecución local o en GitHub Actions

set -e

echo "🚀 Iniciando setup del proyecto..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Crear carpetas necesarias
echo -e "${BLUE}[1/5] Creando estructura de carpetas...${NC}"
mkdir -p data/raw/news
mkdir -p data/raw/prices
mkdir -p data/processed
mkdir -p reports/briefings
mkdir -p reports/relations
mkdir -p logs
echo -e "${GREEN}✓ Carpetas creadas${NC}"

# 2. Crear .gitkeep para mantener carpetas vacías
echo -e "${BLUE}[2/5] Configurando .gitkeep...${NC}"
touch data/raw/.gitkeep
touch data/raw/news/.gitkeep
touch data/raw/prices/.gitkeep
touch data/processed/.gitkeep
touch reports/relations/.gitkeep
touch logs/.gitkeep
echo -e "${GREEN}✓ .gitkeep configurados${NC}"

# 3. Crear .env si no existe
echo -e "${BLUE}[3/5] Configurando variables de entorno...${NC}"
if [ ! -f .env ]; then
    cat > .env << EOF
# OpenAI API Configuration
# Obtener en: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-api-key-here

# Opcional
# LOG_LEVEL=INFO
EOF
    echo -e "${YELLOW}⚠️  Archivo .env creado. POR FAVOR actualiza OPENAI_API_KEY${NC}"
else
    echo -e "${GREEN}✓ .env ya existe${NC}"
fi

# 4. Instalar dependencias (si existe venv o en CI)
if [ ! -z "$VIRTUAL_ENV" ] || [ ! -z "$CI" ]; then
    echo -e "${BLUE}[4/5] Instalando dependencias...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencias instaladas${NC}"
else
    echo -e "${YELLOW}⚠️  Saltando instalación de dependencias${NC}"
    echo -e "${YELLOW}   (Activa un venv primero: python -m venv venv && source venv/bin/activate)${NC}"
fi

# 5. Verificar configuración
echo -e "${BLUE}[5/5] Verificando configuración...${NC}"
if [ -f config/settings.yaml ]; then
    echo -e "${GREEN}✓ config/settings.yaml presente${NC}"
else
    echo -e "${YELLOW}⚠️  config/settings.yaml no encontrado${NC}"
fi

if [ -f info_sources.csv ]; then
    echo -e "${GREEN}✓ info_sources.csv presente${NC}"
else
    echo -e "${YELLOW}⚠️  info_sources.csv no encontrado${NC}"
fi

echo ""
echo -e "${GREEN}✅ Setup completado${NC}"
echo ""
echo -e "${BLUE}Próximos pasos:${NC}"
echo "1. Actualiza OPENAI_API_KEY en .env"
echo "2. Ejecuta: python src/scripts/daily_update.py --date today"
echo "3. Para GitHub Actions, agrega el secret OPENAI_API_KEY en Settings → Secrets"
echo ""
echo -e "${YELLOW}Documentación: Ver README.md para más detalles${NC}"
