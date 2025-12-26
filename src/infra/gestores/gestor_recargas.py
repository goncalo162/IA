"""
Gestor de recargas: agenda e processa recargas de veículos conforme política configurada.
"""
from typing import Optional, Callable, List
from datetime import timedelta
from infra.evento import TipoEvento
from infra.entidades.veiculos import EstadoVeiculo
from infra.entidades.recarga import PlanoRecarga
from infra.policies.recarga_policy import RecargaPolicy, RecargaAutomaticaPolicy


class GestorRecargas:
    """
    Responsável por gerir o processo de recarga/abastecimento de veículos.

    Coordena agendamento, início e término de recargas conforme política configurada.
    """

    def __init__(self, ambiente, navegador, gestor_eventos, metricas, logger,
                 recarga_policy: Optional[RecargaPolicy] = None):
        """
        Inicializa o gestor de recargas.

        Args:
            ambiente: Gestão do ambiente (grafo, veículos, pedidos)
            navegador: Algoritmo de navegação/roteamento
            gestor_eventos: Gestor de eventos temporais
            metricas: Sistema de métricas
            logger: Sistema de logging
            recarga_policy: Política de recarga (padrão: RecargaAutomaticaPolicy)
        """
        self.ambiente = ambiente
        self.navegador = navegador
        self.gestor_eventos = gestor_eventos
        self.metricas = metricas
        self.logger = logger
        self.recarga_policy = recarga_policy or RecargaAutomaticaPolicy()
        self.adicionar_viagem_callback: Optional[Callable] = None
        self.remover_viagem_callback: Optional[Callable] = None

    def configurar_callbacks(self, adicionar_viagem_fn, remover_viagem_fn):
        """
        Configura callbacks para notificar mudanças em viagens ativas.

        Args:
            adicionar_viagem_fn: Função para adicionar veículo às viagens ativas
            remover_viagem_fn: Função para remover veículo das viagens ativas
        """
        self.adicionar_viagem_callback = adicionar_viagem_fn
        self.remover_viagem_callback = remover_viagem_fn

    def verificar_e_agendar_recarga(self, veiculo, tempo_simulacao, fim_viagem: bool = False):
        """
        Verifica se um veículo precisa de recarga e agenda se necessário.

        Args:
            veiculo: Veículo a verificar
            tempo_simulacao: Tempo atual da simulação
        """
        # Verificar política de recarga (passar contexto de fim_viagem quando aplicável)
        if not self.recarga_policy.deve_agendar_recarga(veiculo, fim_viagem=fim_viagem):
            return

        autonomia_pct = veiculo.percentual_autonomia_atual
        self.logger.log(
            f"  [yellow]AVISO[/] Veículo {veiculo.id_veiculo} precisa recarga "
            f"(autonomia: {veiculo.autonomia_atual:.1f}/{veiculo.autonomia_maxima} km, {autonomia_pct:.1f}%)"
        )

        # Planar recarga
        plano = self.planear_recarga(veiculo)

        if plano and self.validar_plano(plano, veiculo, tempo_simulacao):
            self.agendar_recarga(veiculo, plano, tempo_simulacao)
        else:
            # Se não há plano viável, registar veículo sem autonomia
            self.logger.log(
                f"  [red]✗[/] Nenhum plano de recarga viável para veículo {veiculo.id_veiculo}"
            )
            veiculo.estado = EstadoVeiculo.INDISPONIVEL
            self.metricas.registar_veiculo_sem_autonomia(veiculo.id_veiculo)

    def planear_recarga(self,
                        veiculo,
                        rota_restante: Optional[List[str]] = None) -> Optional[PlanoRecarga]:
        """
        Planeia uma recarga para o veículo sem alterar estado.

        Método puro que consulta a política e retorna o melhor plano viável.

        Args:
            veiculo: Veículo que necessita recarga
            rota_restante: Rota restante do veículo (para políticas que consideram desvio)

        Returns:
            PlanoRecarga se houver plano viável, None caso contrário
        """
        # Verificar se já está num posto adequado
        if veiculo.pode_reabastecer_em(veiculo.localizacao_atual, self.ambiente.grafo):
            # Criar plano para recarga imediata no local atual
            tempo_recarga_min = veiculo.tempoReabastecimento()
            return PlanoRecarga(
                posto=veiculo.localizacao_atual,
                tipo_posto=veiculo.tipo_posto_necessario(),
                rota=[veiculo.localizacao_atual],
                distancia_km=0.0,
                desvio_rota_km=0.0,
                tempo_viagem_h=0.0,
                tempo_recarga_min=tempo_recarga_min,
                custo_extra_estimado=tempo_recarga_min * (veiculo.custo_operacional_km * 0.5),
                autonomia_necessaria_km=0.0,
                margem_seguranca_km=0.0,
                observacoes="Veículo já está em posto adequado"
            )

        # Consultar política para encontrar planos
        planos = self.recarga_policy.encontrar_planos_recarga(
            veiculo=veiculo,
            grafo=self.ambiente.grafo,
            navegador=self.navegador,
            ambiente=self.ambiente,
            rota_restante=rota_restante,
            tempo_simulacao=self.gestor_eventos._tempo_atual
        )

        # Retornar melhor plano (primeiro da lista, já ordenados pela policy)
        return planos[0] if planos else None

    def validar_plano(self, plano: PlanoRecarga, veiculo, tempo_simulacao) -> bool:
        """
        Valida um plano de recarga antes de agendamento.

        Revalidation step: verifica condições runtime (autonomia, estado do veículo, posto disponível).

        Args:
            plano: Plano a validar
            veiculo: Veículo que será recarregado
            tempo_simulacao: Tempo atual da simulação

        Returns:
            True se plano é válido, False caso contrário
        """
        if not plano or not plano.viavel:
            return False

        # Verificar se veículo não está em reabastecimento
        if veiculo.estado == EstadoVeiculo.EM_REABASTECIMENTO:
            self.logger.log(
                f"  [yellow]![/] Veículo {veiculo.id_veiculo} já está em reabastecimento"
            )
            return False

        # Verificar autonomia para chegar ao posto
        if not veiculo.autonomia_suficiente_para(plano.distancia_km, margem_seguranca=0):
            self.logger.log(
                f"  [red]✗[/] Veículo {veiculo.id_veiculo} não tem autonomia para "
                f"chegar ao posto {plano.posto} ({plano.distancia_km:.1f} km)"
            )
            return False

        # Verificar se posto ainda existe no grafo
        node_posto = self.ambiente.grafo.get_node_by_name(plano.posto)
        if not node_posto:
            self.logger.log(
                f"  [red]✗[/] Posto {plano.posto} não encontrado no grafo"
            )
            return False

        # Verificar tipo de posto compatível
        if node_posto.getTipoNodo() != plano.tipo_posto:
            self.logger.log(
                f"  [red]✗[/] Posto {plano.posto} não é do tipo esperado {plano.tipo_posto.name}"
            )
            return False

        return True

    def agendar_recarga(self, veiculo, plano: PlanoRecarga, tempo_simulacao):
        """
        Agenda recarga de um veículo usando um plano validado.

        Executa side-effects: inicia viagem de recarga e agenda eventos.

        Args:
            veiculo: Veículo a recarregar
            plano: Plano de recarga validado
            tempo_simulacao: Tempo atual da simulação
        """
        # Se já está no posto, agendar início imediato
        if plano.distancia_km == 0:
            self.gestor_eventos.agendar_evento(
                tempo=tempo_simulacao,
                tipo=TipoEvento.INICIO_RECARGA,
                callback=self._iniciar_recarga,
                dados={'veiculo': veiculo},
                prioridade=5
            )
            return

        # Iniciar viagem até o posto
        if veiculo.iniciar_viagem_recarga(
            plano.rota, plano.posto, plano.distancia_km,
            tempo_simulacao, self.ambiente.grafo
        ):
            # Notificar que veículo precisa ser adicionado às viagens ativas
            if self.adicionar_viagem_callback:
                self.adicionar_viagem_callback(veiculo)

            desvio_info = f", desvio: {plano.desvio_rota_km:.1f}km" if plano.desvio_rota_km else ""
            self.logger.log(
                f"  [INFO] Veículo {veiculo.id_veiculo} a caminho do posto '{plano.posto}' "
                f"({plano.distancia_km:.1f} km, ~{plano.tempo_viagem_h * 60:.1f} min{desvio_info})"
            )
            if plano.observacoes:
                self.logger.log(f"    {plano.observacoes}")
        else:
            self.logger.log(
                f"  [red]✗[/] Falha ao iniciar viagem de recarga para veículo {veiculo.id_veiculo}"
            )

    def processar_chegada_posto(self, veiculo, tempo_simulacao):
        """
        Processa a chegada de um veículo a um posto de abastecimento.

        Args:
            veiculo: Veículo que chegou ao posto
            tempo_simulacao: Tempo atual da simulação
        """
        # Concluir a viagem de recarga (atualiza localização para o posto)
        veiculo.concluir_viagem_recarga()
        self.logger.log(
            f"[INFO] Veículo {veiculo.id_veiculo} chegou ao posto em {veiculo.localizacao_atual}"
        )

        # Verificar se pode reabastecer neste posto
        if veiculo.pode_reabastecer_em(veiculo.localizacao_atual, self.ambiente.grafo):
            # Agendar início da recarga
            self.gestor_eventos.agendar_evento(
                tempo=tempo_simulacao,
                tipo=TipoEvento.INICIO_RECARGA,
                callback=self._iniciar_recarga,
                dados={'veiculo': veiculo},
                prioridade=5
            )
        else:
            self.logger.log(
                f"  [yellow]![/] Veículo {veiculo.id_veiculo} não pode reabastecer "
                f"em {veiculo.localizacao_atual}"
            )
            # Remover da lista de viagens ativas se não vai reabastecer
            if not veiculo.viagem_ativa and self.remover_viagem_callback:
                self.remover_viagem_callback(veiculo.id_veiculo)


    def _iniciar_recarga(self, veiculo):
        """
        Processa o início de recarga/abastecimento de um veículo.

        Args:
            veiculo: Veículo a reabastecer
        """
        # Verificar se está num posto adequado
        if not veiculo.pode_reabastecer_em(veiculo.localizacao_atual, self.ambiente.grafo):
            tipo_posto = veiculo.tipo_posto_necessario()
            self.logger.log(
                f"  [red]✗[/] Veículo {veiculo.id_veiculo} não está num {tipo_posto.name}. "
                f"Localização: {veiculo.localizacao_atual}"
            )
            return

        veiculo.iniciar_recarga(self.gestor_eventos._tempo_atual, veiculo.localizacao_atual)

        # Calcular tempo de recarga
        tempo_recarga_minutos = veiculo.tempoReabastecimento()
        tempo_fim_recarga = self.gestor_eventos._tempo_atual + \
            timedelta(minutes=tempo_recarga_minutos)

        self.logger.log(
            f"[INFO] Veículo {
                veiculo.id_veiculo} iniciou recarga em {
                veiculo.localizacao_abastecimento}")
        self.logger.log(
            f"    Tempo estimado: {tempo_recarga_minutos:.1f} min | "
            f"Fim previsto: {tempo_fim_recarga.strftime('%H:%M:%S')}"
        )

        # Agendar fim da recarga
        self.gestor_eventos.agendar_evento(
            tempo=tempo_fim_recarga,
            tipo=TipoEvento.FIM_RECARGA,
            callback=self._finalizar_recarga,
            dados={'veiculo': veiculo, 'tempo_recarga': tempo_recarga_minutos},
            prioridade=5
        )

    def _finalizar_recarga(self, veiculo, tempo_recarga: float):
        """
        Processa o fim de recarga/abastecimento de um veículo.

        Args:
            veiculo: Veículo que terminou a recarga
            tempo_recarga: Tempo gasto em recarga (minutos)
        """
        autonomia_anterior = veiculo.autonomia_atual
        autonomia_recarregada = self.ambiente.executar_recarga(veiculo)

        self.logger.log(f"[green]OK[/] Veículo {veiculo.id_veiculo} terminou recarga")
        self.logger.log(
            f"    Autonomia: {autonomia_anterior} km -> {veiculo.autonomia_atual} km "
            f"({veiculo.percentual_autonomia_atual:.1f}%)"
        )

        self.metricas.registar_recarga(
            veiculo_id=veiculo.id_veiculo,
            tempo_recarga=tempo_recarga,
            autonomia_recarregada=autonomia_recarregada,
            localizacao=veiculo.localizacao_atual
        )
