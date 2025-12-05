# Makefile para Simulador de Gestão de Frota de Táxis Inteligente
# Projeto de IA - UMinho 2025

.PHONY: help install run clean test lint format check run-1 run-10 run-60 run-turbo test test-ridesharing test-transito run-env

# Variáveis
PYTHON := python
VENV := venv
SRC := src
DATASET := dataset

# Algoritmo e velocidade padrão
ALGO := bfs
SPEED := 1.0

# Algoritmos disponíveis
ALGO_BFS := bfs
ALGO_DFS := dfs

# Algoritmos de alocação disponíveis
ALGO_HEURISTICO := Heuristico
ALGO_SIMPLES := simples

# Algoritmo de alocação padrão
ALGO_ALOC := Heuristico

help:
	@echo "======================================================================"
	@echo "Simulador de Gestão de Frota de Táxis Inteligente"
	@echo "======================================================================"
	@echo ""
	@echo "Comandos disponíveis:"
	@echo "  make install        - Instalar dependências e configurar ambiente"
	@echo "  make run            - Executar simulação (padrão: dijkstra, velocidade 1.0)"
	@echo "  make run SPEED=X    - Executar com velocidade customizada"
	@echo "  make run-1          - Executar com velocidade 1x (tempo real)"
	@echo "  make run-10         - Executar com velocidade 10x"
	@echo "  make run-60         - Executar com velocidade 60x"
	@echo "  make run-turbo      - Executar com velocidade 100x"
	@echo "  make run-fast       - Executar sem display, velocidade 500x (muito rápido)"
	@echo "  make run-ultra      - Executar sem display, velocidade 5000x (ultra rápido)"
	@echo "  make run-env        - Executar usando configurações do ficheiro .env"
	@echo "  make clean          - Limpar ficheiros temporários e cache"
	@echo "  make lint           - Verificar código com flake8"
	@echo "  make format         - Formatar código com autopep8"
	@echo "  make test           - Executar testes (se existirem)"
	@echo ""
	@echo "Exemplos:"
	@echo "  make install        # Primeiro passo: instalar"
	@echo "  make run            # Executar com velocidade padrão (1.0)"
	@echo "  make run SPEED=50   # Executar com velocidade 50x"
	@echo "  make run-fast       # Executar sem display a 500x (rápido)"
	@echo "  make run-ultra      # Executar sem display a 5000x (ultra rápido)"
	@echo "======================================================================"

#deps:
#	@echo "A instalar dependências..."
#	$(PYTHON) -m venv $(VENV)
#	@echo "Ambiente virtual criado. Ative-o manualmente:"
#	@echo "  Linux/Mac: source venv/bin/activate"
#	@echo ""
#	@echo "Depois execute: pip install -r requirements.txt"


#install:
#	@echo "A instalar/atualizar dependências..."
#	pip install -r requirements.txt

# Comandos de desenvolvimento
dev-install:
	@echo "A instalar ferramentas de desenvolvimento..."
	pip install flake8 autopep8 pytest black


clean:
	@echo "A limpar ficheiros temporários..."
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist $(SRC)\__pycache__ rmdir /s /q $(SRC)\__pycache__
	@if exist $(SRC)\core\__pycache__ rmdir /s /q $(SRC)\core\__pycache__
	@if exist $(SRC)\algorithms\__pycache__ rmdir /s /q $(SRC)\algorithms\__pycache__
	@if exist $(SRC)\infra\__pycache__ rmdir /s /q $(SRC)\infra\__pycache__
	@if exist $(SRC)\display\__pycache__ rmdir /s /q $(SRC)\display\__pycache__
	@if exist *.pyc del /s /q *.pyc
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@echo "Limpeza concluída!"

lint:
	@echo "A verificar código com flake8..."
	@flake8 $(SRC) --max-line-length=100 --exclude=venv,__pycache__ || echo "flake8 não instalado. Execute: pip install flake8"

format:
	@echo "A formatar código com autopep8..."
	@autopep8 --in-place --aggressive --recursive $(SRC) || echo "autopep8 não instalado. Execute: pip install autopep8"


# Verificação rápida de erros de sintaxe e linters opcionais
check:
	@echo "Executando verificação de sintaxe recursiva em src/ ..."
	@python3 -m compileall -q -f src || \
		(echo "Erros de sintaxe encontrados em src/"; exit 1)
	@echo "Verificação concluída sem erros."


linter:
	@echo "Executando linters opcionais (flake8, pylint) se instalados..."
	@command -v flake8 >/dev/null 2>&1 && flake8 $(SRC) --max-line-length=100 --exclude=venv,__pycache__ || true
	@command -v pylint >/dev/null 2>&1 && pylint $(SRC) || true
	@echo "Verificação concluída."


# Comandos de execução
run:
	@echo "A executar simulação com navegação $(ALGO) e alocação $(ALGO_ALOC) a velocidade $(SPEED)x..."
	$(PYTHON) $(SRC)/main.py $(DATASET)/grafo.json $(DATASET)/veiculos.json $(DATASET)/pedidos.json $(ALGO) $(ALGO_ALOC) $(SPEED)

run-1:
	@echo "A executar simulação com navegação $(ALGO) e alocação $(ALGO_ALOC) a velocidade 1x (tempo real)..."
	$(PYTHON) $(SRC)/main.py $(DATASET)/grafo.json $(DATASET)/veiculos.json $(DATASET)/pedidos.json $(ALGO) $(ALGO_ALOC) 1.0

run-10:
	@echo "A executar simulação com navegação $(ALGO) e alocação $(ALGO_ALOC) a velocidade 10x..."
	$(PYTHON) $(SRC)/main.py $(DATASET)/grafo.json $(DATASET)/veiculos.json $(DATASET)/pedidos.json $(ALGO) $(ALGO_ALOC) 10.0

run-60:
	@echo "A executar simulação com navegação $(ALGO) e alocação $(ALGO_ALOC) a velocidade 60x..."
	$(PYTHON) $(SRC)/main.py $(DATASET)/grafo.json $(DATASET)/veiculos.json $(DATASET)/pedidos.json $(ALGO) $(ALGO_ALOC) 60.0

run-turbo:
	@echo "A executar simulação SEM DISPLAY com navegação $(ALGO) e alocação $(ALGO_ALOC) a velocidade 500x (muito rápido)..."
	$(PYTHON) $(SRC)/main.py $(DATASET)/grafo.json $(DATASET)/veiculos.json $(DATASET)/pedidos.json $(ALGO) $(ALGO_ALOC) 500.0 --no-display

test:
	PYTHONPATH=src pytest -q

test-ridesharing:
	PYTHONPATH=src pytest -q tests/test_ridesharing.py

test-transito:
	PYTHONPATH=src pytest -v tests/test_eventos_transito.py

# Executar usando configurações do ficheiro .env
run-env:
	@echo "A executar simulação usando configurações do ficheiro .env..."
	$(PYTHON) $(SRC)/main.py





