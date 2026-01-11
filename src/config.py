import os
import sys
from dotenv import load_dotenv
from typing import Optional

from infra.policies.recarga_policy import RecargaAutomaticaPolicy, SemRecargaPolicy, RecargaDuranteViagemPolicy
from algoritmos.algoritmos_navegacao import NavegadorBFS, NavegadorCustoUniforme, NavegadorDFS
from algoritmos.algoritmos_alocacao import AlocadorHeuristico, AlocadorSimples, AlocadorPorCusto, AlocadorAEstrela
from infra.policies.reposicionamento_policy import ReposicionamentoAtratividade, ReposicionamentoEstatistico, ReposicionamentoNulo
from infra.policies.ridesharing_policy import SimplesRideSharingPolicy, SemRideSharingPolicy
from algoritmos.criterios import CustoDefault, CustoTempoPercurso, CustoAmbientalTempo
from algoritmos.criterios import ZeroHeuristica, HeuristicaEuclidiana

# Carregar variáveis de ambiente do ficheiro .env
load_dotenv()


class Config:
    """Classe centralizada para todas as configurações da simulação."""

    # Configurações de Simulação
    DURACAO_HORAS = float(os.getenv('DURACAO_HORAS', '8.0'))
    FREQUENCIA_CALCULO = float(os.getenv('FREQUENCIA_CALCULO', '1.0'))
    FREQUENCIA_DISPLAY = float(os.getenv('FREQUENCIA_DISPLAY', '10.0'))
    VELOCIDADE_SIMULACAO = float(os.getenv('VELOCIDADE_SIMULACAO', '1.0'))

    # Configurações de Display
    MOSTRAR_DISPLAY = os.getenv(
        'MOSTRAR_DISPLAY', 'true').lower() not in (
        'false', '0', 'no', 'off')

    # Caminhos dos Datasets
    CAMINHO_GRAFO = os.getenv('CAMINHO_GRAFO', 'dataset/grafo.json')
    CAMINHO_VEICULOS = os.getenv('CAMINHO_VEICULOS', 'dataset/veiculos.json')
    CAMINHO_PEDIDOS = os.getenv('CAMINHO_PEDIDOS', 'dataset/pedidos.json')
    CAMINHO_EVENTOS_TRANSITO = os.getenv(
        'CAMINHO_EVENTOS_TRANSITO',
        'dataset/eventos_transito.json')

    # Algoritmos
    ALGORITMO_NAVEGACAO = os.getenv('ALGORITMO_NAVEGACAO', 'bfs')
    ALGORITMO_ALOCACAO = os.getenv('ALGORITMO_ALOCACAO', 'simples')

    # Função de custo e heurística (lidas do .env)
    FUNCAO_CUSTO = os.getenv('FUNCAO_CUSTO', 'default')
    HEURISTICA = os.getenv('HEURISTICA', 'zero')

    # Políticas de Ride-Sharing
    POLITICA_RIDE_SHARING = os.getenv('POLITICA_RIDE_SHARING', 'simples')

    # Políticas de Recarga
    POLITICA_RECARGA = os.getenv('POLITICA_RECARGA', 'automatica')

    # Politica de Reposicionamento
    POLITICA_REPOSICIONAMENTO = os.getenv('POLITICA_REPOSICIONAMENTO', 'nulo')

    # Penalização aplicada ao custo total por cada pedido rejeitado
    PENALIDADE_PEDIDO_REJEITADO = float(os.getenv('PENALIDADE_PEDIDO_REJEITADO', '100.0'))

    @classmethod
    def get_funcao_custo(self, nome: str = None):
        """Retorna a função de custo especificada (instância)."""

        nome = (nome or self.FUNCAO_CUSTO).lower()
        opcoes = {
            'default': CustoDefault,
            'tempo': CustoTempoPercurso,
            'ambiental': CustoAmbientalTempo
        }

        func_class = opcoes.get(nome)
        if func_class is None:
            print(f"Função de custo inválida: '{nome}'")
            print(f"Use: {', '.join(opcoes.keys())}")
            sys.exit(1)

        return func_class()

    @classmethod
    def get_heuristica(self, nome: str = None):
        """Retorna a heurística especificada (instância)."""

        nome = (nome or self.HEURISTICA).lower()
        opcoes = {
            'zero': ZeroHeuristica,
            'euclidiana': HeuristicaEuclidiana,
        }

        heur_class = opcoes.get(nome)
        if heur_class is None:
            print(f"Heurística inválida: '{nome}'")
            print(f"Use: {', '.join(opcoes.keys())}")
            sys.exit(1)

        return heur_class()

    @classmethod
    def get_navegador(
            self,
            nome: str = None,
            funcao_custo: Optional[object] = None,
            heuristica: Optional[object] = None):
        """Retorna o navegador especificado."""

        nome = nome or self.ALGORITMO_NAVEGACAO
        navegadores = {
            "bfs": NavegadorBFS,
            "dfs": NavegadorDFS,
            "ucs": NavegadorCustoUniforme,
        }

        navegador_class = navegadores.get(nome.lower())
        if navegador_class is None:
            print(f"Algoritmo de navegação inválido: '{nome}'")
            print(f"Use: {', '.join(navegadores.keys())}")
            sys.exit(1)

        return navegador_class(funcao_custo, heuristica)

    @classmethod
    def get_alocador(
            self,
            navegador,
            nome: str = None,
            funcao_custo: Optional[object] = None,
            heuristica: Optional[object] = None):
        """Retorna o alocador especificado."""

        nome = nome or self.ALGORITMO_ALOCACAO
        alocadores = {
            "heuristico": AlocadorHeuristico,
            "simples": AlocadorSimples,
            "custo": AlocadorPorCusto,
            "aestrela": AlocadorAEstrela,
        }

        alocador_class = alocadores.get(nome.lower())
        if alocador_class is None:
            print(f"Algoritmo de alocação inválido: '{nome}'")
            print(f"Use: {', '.join(alocadores.keys())}")
            sys.exit(1)

         # Instanciar alocador com navegador, função de custo e heurística
        return alocador_class(navegador, funcao_custo, heuristica)

    @classmethod
    def parse_args(self):
        """
        Processa argumentos da linha de comando e retorna configurações.
        Prioridade: argumentos CLI > .env > defaults
        """
        config = {}

        # Se foram passados argumentos via linha de comando
        if len(sys.argv) >= 6:
            config['caminho_grafo'] = sys.argv[1]
            config['caminho_veiculos'] = sys.argv[2]
            config['caminho_pedidos'] = sys.argv[3]
            config['algoritmo_navegacao'] = sys.argv[4]
            config['algoritmo_alocacao'] = sys.argv[5]
            config['caminho_eventos_transito'] = self.CAMINHO_EVENTOS_TRANSITO

            # Processar argumentos opcionais
            config['no_display'] = '--no-display' in sys.argv
            config['velocidade_display'] = self.VELOCIDADE_SIMULACAO

            for arg in sys.argv[6:]:
                if arg != '--no-display':
                    try:
                        config['velocidade_display'] = float(arg)
                    except ValueError:
                        pass

        elif len(sys.argv) == 1:
            # Usar valores do .env
            config['caminho_grafo'] = self.CAMINHO_GRAFO
            config['caminho_veiculos'] = self.CAMINHO_VEICULOS
            config['caminho_pedidos'] = self.CAMINHO_PEDIDOS
            config['caminho_eventos_transito'] = self.CAMINHO_EVENTOS_TRANSITO
            config['algoritmo_navegacao'] = self.ALGORITMO_NAVEGACAO
            config['algoritmo_alocacao'] = self.ALGORITMO_ALOCACAO
            config['no_display'] = not self.MOSTRAR_DISPLAY
            config['velocidade_display'] = self.VELOCIDADE_SIMULACAO

        else:
            print(
                "Uso: python src/main.py <grafo.json> <veiculos.json> <pedidos.json> "
                "<algoritmo_nav> <algoritmo_aloc> [velocidade] [--no-display]"
            )
            print("Ou configure as variáveis no ficheiro .env e execute sem argumentos.")
            sys.exit(1)

        # Flag --no-display sempre sobrepõe
        if '--no-display' in sys.argv:
            config['no_display'] = True

        return config

    @classmethod
    def get_ride_sharing_policy(self) -> Optional[object]:
        """Retorna a política de ride-sharing configurada ou None."""

        # Dicionário com as políticas disponíveis
        policies = {
            'simples': SimplesRideSharingPolicy,
            'sem': SemRideSharingPolicy,
        }

        nome_politica = os.getenv('POLITICA_RIDE_SHARING', 'simples')
        policy_class = policies[nome_politica.lower()]
        if policy_class is None:
            print(f"Política de ride-sharing inválida: '{nome_politica}'")
            print(f"Use: {', '.join(policies.keys())}")
            sys.exit(1)

        return policy_class()

    @classmethod
    def get_recarga_policy(self):
        """Retorna a política de recarga configurada."""

        policies = {
            'automatica': RecargaAutomaticaPolicy,
            'durante_viagem': RecargaDuranteViagemPolicy,
            'sem': SemRecargaPolicy,
        }

        nome_politica = os.getenv('POLITICA_RECARGA', 'automatica')
        policy_class = policies[nome_politica.lower()]
        if policy_class is None:
            print(f"Política de recarga inválida: '{nome_politica}'")
            print(f"Use: {', '.join(policies.keys())}")
            sys.exit(1)

        return policy_class()


    @classmethod
    def get_reposicionamento_policy(self):
        """Retorna a política de reposicionamento configurada."""

        policies = {
            'nulo': ReposicionamentoNulo,
            'atratividade': ReposicionamentoAtratividade,
             'estatistico': ReposicionamentoEstatistico,  
        }

        nome_politica = os.getenv('POLITICA_REPOSICIONAMENTO', 'nulo')
        policy_class = policies[nome_politica.lower()]
        if policy_class is None:
            print(f"Política de reposicionamento inválida: '{nome_politica}'")
            print(f"Use: {', '.join(policies.keys())}")
            sys.exit(1)

        return policy_class()
