#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

echo -e "${BLUE}A instalar...${RESET}"

OS="$(uname -s)"
case "${OS}" in
    Linux*)     PLATFORM=Linux;;
    Darwin*)    PLATFORM=Mac;;
    *)          PLATFORM="Unknown";;
esac

echo -e "${YELLOW}Sistema operativo identificado:${RESET} ${PLATFORM}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 não encontrado. Por favor instale Python 3.8+ e corra este script novamente.${RESET}"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo -e "${BLUE}A criar ambiente virtual Python...${RESET}"
    python3 -m venv venv
fi

echo -e "${BLUE}A ativar ambiente virtual Python...${RESET}"
source venv/bin/activate

echo -e "${BLUE}A atualizar/instalar pip...${RESET}"
pip install --upgrade pip

if [ "${PLATFORM}" = "Linux" ]; then
    echo -e "${BLUE}A instalar dependências para Linux (necessário 'sudo')...${RESET}"
    if command -v apt &> /dev/null; then
        sudo apt update -y && sudo apt install -y python3-tk
    elif command -v pacman &> /dev/null; then
        sudo pacman -Sy --noconfirm tk
    else
        echo -e "${YELLOW}Gestor de pacotes não suportado (não é apt nem pacman). Instala manualmente o pacote Tk.${RESET}"
    fi
elif [ "${PLATFORM}" = "Mac" ]; then
    echo -e "${BLUE}A verificar suporte para Tk no macOS...${RESET}"
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}Homebrew não foi encontrado. Instale-o em https://brew.sh se Tk falhar futuramente.${RESET}"
    else
        echo -e "${BLUE}A instalar dependências para macOS...${RESET}"
        brew install python-tk || true
    fi
else
    echo -e "${YELLOW}Plataforma desconhecida. A passar à frente instalação de dependências específicas.${RESET}"
fi

echo -e "${BLUE}A instalar pacotes Python...${RESET}"
pip install \
    matplotlib \
    networkx \
    textual \
    pillow \
    numpy

echo
echo -e "${GREEN}Todos os ficheiros foram instalados com sucesso.${RESET}"
echo -e "${YELLOW}Para correr o programa no futuro é necessário ativar o ambiente virtual Python:${RESET}"
echo "   source venv/bin/activate"
echo
echo -e "${YELLOW}Para correr o programa:${RESET}"
echo "  Num terminal: python3 src/display/display.py dataset/grafo.json <algoritmo de procura>"
echo
echo -e "${GREEN}Instalação concluída.${RESET}"