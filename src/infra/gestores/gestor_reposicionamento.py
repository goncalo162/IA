"""
Gestor de reposicionamento proativo de veículos.
"""
from typing import List, Optional, Callable
from datetime import datetime
from infra.policies.reposicionamento_policy import ReposicionamentoPolicy, ReposicionamentoNulo


class GestorReposicionamento:
    """
    Responsável por gerir o reposicionamento proativo de veículos.

    Coordena a política de reposicionamento, identifica veículos disponíveis
    e agenda deslocamentos vazios para zonas de alta demanda.
    """

    def __init__(
        self,
        ambiente,
        navegador,
        metricas,
        logger,
        reposicionamento_policy: Optional[ReposicionamentoPolicy] = None
    ):
        """
        Inicializa o gestor de reposicionamento.

        Args:
            ambiente: Gestão do ambiente (grafo, veículos, pedidos)
            navegador: Algoritmo de navegação/roteamento
            metricas: Sistema de métricas
            logger: Sistema de logging
            reposicionamento_policy: Política de reposicionamento (padrão: ReposicionamentoNulo)
        """
        self.ambiente = ambiente
        self.navegador = navegador
        self.metricas = metricas
        self.logger = logger
        self.reposicionamento_policy = reposicionamento_policy or ReposicionamentoNulo()
        self.agendar_viagem_fn: Optional[Callable] = None

    def configurar_agendador(self, agendar_fn: Optional[Callable]):
        """Regista uma função de agendamento de viagem.

        Esta é uma forma de injetar uma dependência de agendamento sem aceder ao GestorViagens.
        """
        self.agendar_viagem_fn = agendar_fn

    def planear_reposicionamentos(self, tempo_simulacao: datetime) -> int:
        """
        Planeia e executa reposicionamentos proativos de veículos.

        Args:
            tempo_simulacao: Tempo atual da simulação

        Returns:
            Número de veículos reposicionados
        """
        # 1. Identificar veículos disponíveis para reposicionamento
        veiculos_disponiveis = self.ambiente.listar_veiculos_disponiveis()

        if not veiculos_disponiveis:
            return 0

        # 2. Consultar política de reposicionamento
        reposicionamentos = self.reposicionamento_policy.decidir_reposicionamentos(
            veiculos_disponiveis=veiculos_disponiveis,
            grafo=self.ambiente.grafo,
            ambiente=self.ambiente,
            tempo_simulacao=tempo_simulacao
        )

        if not reposicionamentos:
            return 0

        # 3. Executar reposicionamentos
        count_reposicionados = 0
        horario_log = tempo_simulacao.strftime('%H:%M:%S')

        for veiculo, nodo_destino in reposicionamentos:
            sucesso = self._executar_reposicionamento(
                veiculo,
                nodo_destino,
                tempo_simulacao,
                horario_log
            )
            if sucesso:
                count_reposicionados += 1

        return count_reposicionados

    def _executar_reposicionamento(
        self,
        veiculo,
        nodo_destino: str,
        tempo_simulacao: datetime,
        horario_log: str
    ) -> bool:
        """
        Executa o reposicionamento de um veículo.

        Args:
            veiculo: Veículo a reposicionar
            nodo_destino: ID do nodo destino
            tempo_simulacao: Tempo atual
            horario_log: String formatada do horário para log

        Returns:
            True se reposicionamento foi executado com sucesso
        """

        try:
            origem = str(veiculo.localizacao_atual)
            destino = str(nodo_destino)

            # Se já está no destino, não faz nada
            if origem == destino:
                return False

            # Calcular rota
            rota = self.navegador.calcular_rota(self.ambiente.grafo, origem, destino)
            if not rota:
                self.logger.log(
                    f"  {horario_log} - [yellow] Reposicionamento V{veiculo.id_veiculo}: "
                    f"sem rota {origem}→{destino}[/]"
                )
                return False

            # Calcular distância
            distancia = self.navegador.calcular_distancia(self.ambiente.grafo, rota)

            # Verificar autonomia
            if veiculo.autonomia_atual < distancia:
                self.logger.log(
                    f"  {horario_log} - [yellow] Reposicionamento V{veiculo.id_veiculo}: "
                    f"autonomia insuficiente ({veiculo.autonomia_atual:.1f} < {distancia:.1f} km)[/]"
                )
                return False

            # Criar e iniciar viagem de reposicionamento
            veiculo.iniciar_viagem_reposicionamento(
                rota=rota,
                distancia=distancia,
                tempo_simulacao=tempo_simulacao,
                grafo=self.ambiente.grafo
            )

            # Adiciona veiculo as viagens ativas em GestorViagens
            if self.agendar_viagem_fn:
                self.agendar_viagem_fn(veiculo)
                
            # Registar métrica
            self.metricas.registar_reposicionamento(
                veiculo_id=veiculo.id_veiculo,
                origem=origem,
                destino=destino,
                distancia=distancia
            )

            # Log
            self.logger.log(
                f"  {horario_log} - [magenta]↻ Reposicionamento V{veiculo.id_veiculo}: "
                f"{origem}→{destino} ({distancia:.1f} km)[/]"
            )

            return True

        except Exception as e:
            self.logger.log(
                f"  {horario_log} - [red]✗ Erro ao reposicionar V{veiculo.id_veiculo}: {e}[/]"
            )
            return False
