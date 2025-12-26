"""
Interface base para algoritmos de alocação de veículos.
Todos os algoritmos de escolha de veículo devem herdar desta classe.
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from infra.entidades.veiculos import Veiculo
from infra.entidades.pedidos import Pedido
from infra.grafo.grafo import Grafo
from algoritmos.criterios import FuncaoCusto, Heuristica, CustoDefault, ZeroHeuristica
from infra.entidades.veiculos import EstadoVeiculo
from infra.entidades.recarga import PlanoRecarga


class AlocadorBase(ABC):
    """
    Classe abstrata que define a interface para algoritmos de alocação.

    Um alocador é responsável por escolher qual veículo deve atender
    um pedido específico, considerando critérios como disponibilidade,
    distância, capacidade, autonomia, custo, etc.
    """

    def __init__(
            self,
            navegador,
            funcao_custo: Optional[FuncaoCusto] = None,
            heuristica: Optional[Heuristica] = None):
        """Inicializa o alocador com navegador e funções opcionais de custo/heurística.

        O `navegador` é usado pelos algoritmos de alocação para calcular rotas
        entre veículo e cliente sem precisar ser passado a cada chamada.

        Args:
            navegador: Navegador para cálculo de rotas
            funcao_custo: Função de custo para avaliação de rotas
            heuristica: Heurística para estimativas
            gestor_recargas: Gestor de recargas (opcional, para planeamento de recarga)
        """
        self.navegador = navegador
        self.funcao_custo: FuncaoCusto = funcao_custo if funcao_custo is not None else CustoDefault()
        self.heuristica: Heuristica = heuristica if heuristica is not None else ZeroHeuristica()
        self.gestor_recargas = None  # a ser configurado externamente

        # adicionar estrutura auxiliar talvez dicionario de idveiulo para infos
        # dos calculos do custo para escolher melhor os veiculos

    def configurar_gestor_recargas(self, gestor_recargas):
        """Configura o gestor de recargas para coordenação."""
        self.gestor_recargas = gestor_recargas

    @abstractmethod
    def escolher_veiculo(
            self,
            pedido: Pedido,
            veiculos_disponiveis: List[Veiculo],
            grafo: Grafo,
            rota_pedido: List[str],
            distancia_pedido: float) -> Optional[Veiculo]:
        """Escolhe o melhor veículo para atender um pedido.

        Args:
            pedido: O pedido a ser atendido.
            veiculos_disponiveis: Lista de veículos disponíveis.
            grafo: Grafo da cidade para cálculo de distâncias.
            rota_pedido: Rota origem->destino do pedido (em nomes de nós).
            distancia_pedido: Distância total dessa rota.

        Returns:
            O veículo escolhido, ou None se nenhum veículo for adequado
        """
        pass

    @abstractmethod
    def nome_algoritmo(self) -> str:
        """Retorna o nome do algoritmo para identificação."""
        pass

    def _verificar_capacidade(self, veiculo: Veiculo, pedido: Pedido) -> bool:
        """Verifica se o veículo tem capacidade para o número de passageiros."""
        return veiculo.capacidade_passageiros >= veiculo.numero_passageiros + pedido.numero_passageiros

    def _verificar_autonomia(self, veiculo: Veiculo, distancia: float) -> bool:
        """Verifica se o veículo tem autonomia suficiente para a distância.

        Args:
            veiculo: Veículo a verificar
            distancia: Distância total que o veículo precisa percorrer (até cliente + viagem)

        Returns:
            True se o veículo tem autonomia suficiente
        """
        return veiculo.autonomia_suficiente_para(distancia)

    def _veiculo_passa_pela_origem(self, veiculo: Veiculo, pedido: Pedido, grafo: Grafo) -> bool:
        """Quando veículo está em andamento, valida se a sua rota restante passa pela origem do pedido.
        """
        if veiculo.estado != EstadoVeiculo.EM_ANDAMENTO:
            return True

        origem_pedido_nome = grafo.getNodeName(pedido.origem)
        return veiculo.passa_por(origem_pedido_nome)

    def verificar_ou_planear_recarga(self, veiculo: Veiculo, distancia_total: float,
                                     rota_completa: Optional[List[str]] = None) -> bool:
        """
        Verifica autonomia e planeia recarga se necessário.

        Se veículo não tem autonomia suficiente, tenta planear recarga.
        Armazena plano em veiculo.plano_recarga_pendente se viável.

        Args:
            veiculo: Veículo a verificar
            distancia_total: Distância total a percorrer
            rota_completa: Rota completa planeada (util para políticas que considerem desvio)

        Returns:
            True se veículo é elegível (tem autonomia ou plano de recarga viável),
            False caso contrário
        """
        # Verificar autonomia direta
        if veiculo.autonomia_suficiente_para(distancia_total):
            veiculo.plano_recarga_pendente = None  # Limpar plano antigo se houver
            return True

        # Sem autonomia e sem gestor de recargas, veículo inelegível
        if not self.gestor_recargas:
            veiculo.plano_recarga_pendente = None
            return False

        # Planear recarga
        plano = self.gestor_recargas.planear_recarga(veiculo, rota_completa)

        if plano and plano.viavel:
            # Armazenar plano para scoring
            veiculo.plano_recarga_pendente = plano
            return True
        else:
            # Sem plano viável, veículo inelegível
            veiculo.plano_recarga_pendente = None
            return False
