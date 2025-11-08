"""
Simulador de Gestão de Frota de Táxis Inteligente
Projeto de IA - UMinho 2025
"""
import sys
import os
from datetime import datetime
from algoritmos.algoritmos_alocacao import AlocadorSimples
from infra.simulador import Simulador
from algoritmos.algoritmos_navegacao import NavegadorBFS, NavegadorDFS

# Garantir que o root do projecto está no path para imports relativos funcionarem
src_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(src_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

DURACAO_HORAS_DEFAULT = 8.0
# frequencia_calculo: quantas vezes os cálculos são feitos por segundo real (Hz)
FREQUENCIA_CALCULO_DEFAULT = 10.0  # 10 cálculos por segundo real (atualiza a cada 0.1s real)
# frequencia_display: quantas vezes o display mostra informação atualizada por segundo real (Hz)
FREQUENCIA_DISPLAY_DEFAULT = 10.0  # 10 frames por segundo real (redesenha a cada 0.1s real)
# velocidade_simulacao: velocidade com que é mostrada a simulação relativa ao tempo real (1.0 = tempo real)
VELOCIDADE_SIMULACAO_DEFAULT = 1.0  # 1.0 = tempo real

def main():
    """
    Ponto de entrada principal do simulador.
    
    Uso:
        python src/main.py <grafo.json> <veiculos.json> <pedidos.json> <algoritmo> [velocidade]  [--no-display]
        (falta o json dos eventos se necessário) 
    
    Algoritmos disponíveis:
        - bfs: Breadth-First Search
        - dfs: Depth-First Search
    
    Velocidade (opcional):
        - Número decimal que multiplica a velocidade de visualização
        - 1.0 = tempo real (padrão)
        - 2.0 = 2x mais rápido
        - 0.5 = 2x mais lento

    Alocadores disponíveis:

    """
    
    caminho_grafo = sys.argv[1]
    caminho_veiculos = sys.argv[2]
    caminho_pedidos = sys.argv[3]
    # caminho_eventos = sys.argv[4] TODO: receber os eventos por argumento
    algoritmo_navegacao = sys.argv[4].lower()
    #algoritmo_alocacao = sys.argv[5].lower() TODO: receber o algoritmo de alocação por argumento
    
    # Verificar se modo sem display está ativo
    no_display = '--no-display' in sys.argv
    
    # Velocidade de visualização (opcional)
    velocidade_display = 1.0
    if len(sys.argv) > 5:
        # Tentar extrair velocidade (pode ser antes ou depois de --no-display)
        for arg in sys.argv[5:]:
            if arg != '--no-display':
                try:
                    velocidade_display = float(arg)
                    if velocidade_display <= 0:
                        print(" Velocidade deve ser maior que 0")
                        sys.exit(1)
                    break
                except ValueError:
                    print(f" Argumento inválido: {arg}")
                    print("   Use: <velocidade> e/ou --no-display")
                    sys.exit(1)
    
    # Verificar ficheiros
    for caminho in [caminho_grafo, caminho_veiculos, caminho_pedidos]:
        if not os.path.exists(caminho):
            print(f" Ficheiro '{caminho}' não encontrado")
            sys.exit(1)
    
    # Escolher algoritmo de navegação
    navegadores = {
        "bfs": NavegadorBFS(),
        "dfs": NavegadorDFS()
    }

    if algoritmo_navegacao in navegadores:
        navegador = navegadores[algoritmo_navegacao]
    else:
        print(f" Algoritmo '{algoritmo_navegacao}' não reconhecido")
        print("   Algoritmos disponíveis: bfs, dfs")
        sys.exit(1)
    
    # Escolher algoritmo de alocação
    alocadores = {
        "simples": AlocadorSimples()
    }

  #  if algoritmo_alocacao in alocadores:
  #      alocador = alocadores[algoritmo_alocacao]
  #  else:
  #      print(f" Algoritmo de alocação '{algoritmo_alocacao}' não reconhecido")
  #      print("   Algoritmos disponíveis: simples")
  #      sys.exit(1)

    #TODO: passar o alocador como argumento no futuro para permitir diferentes estratégias e fazer como os algoritmos de navegação
    alocador = AlocadorSimples()
    
    # Configuração de timing da simulação
    #TODO: decidir se queremos receber por argumento 
    frequencia_calculo = FREQUENCIA_CALCULO_DEFAULT
    frequencia_display = FREQUENCIA_DISPLAY_DEFAULT

    # Criar display (ou não, se --no-display)
    if no_display:
        display = None
        print(" Modo sem display ativado (execução mais rápida)")

    ''' TODO: juntar com o display aqui
    
        else :
            display = DisplayGrafico(frequencia_display=frequencia_display)
            display.set_velocidade_simulacao(velocidade_display)
    '''
    
    # Criar e configurar simulador
    try:  
        # Tempo inicial da simulação: 2025-01-01 08:00:00 (tempo fixo para ser mais fácil testes)
        tempo_inicial = datetime(2025, 1, 1, 8, 0, 0)
        
        simulador = Simulador(
            alocador=alocador,
            navegador=navegador,
            display=display,
            tempo_inicial=tempo_inicial,
            frequencia_calculo=frequencia_calculo,
            velocidade_simulacao=velocidade_display
        )
        
        # Carregar dados
        simulador.carregar_dados(
            caminho_grafo=caminho_grafo,
            caminho_veiculos=caminho_veiculos,
            caminho_pedidos=caminho_pedidos
        )
        
        # Executar simulação (8 horas de operação valor default, talvez receber por argumento no futuro ou uma constante)
        simulador.executar(duracao_horas=DURACAO_HORAS_DEFAULT)
        
    except Exception as e:
        print(f"\n Erro durante a simulação: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
