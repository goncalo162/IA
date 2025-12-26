"""
Gestor de pedidos: processa chegada de pedidos, validação e alocação de veículos.
"""
from typing import Optional, Tuple, List, Dict
from infra.policies.ridesharing_policy import RideSharingPolicy, SimplesRideSharingPolicy


class GestorPedidos:
    """
    Responsável por processar pedidos de transporte.
    
    Coordena validação de rotas, escolha de veículos e início de viagens.
    Retorna veículos com viagens iniciadas.
    """
    
    def __init__(self, ambiente, alocador, navegador, metricas, logger,
                 ridesharing_policy: Optional[RideSharingPolicy] = None):
        """
        Inicializa o gestor de pedidos.
        
        Args:
            ambiente: Gestão do ambiente (grafo, veículos, pedidos)
            alocador: Algoritmo de alocação de veículos
            navegador: Algoritmo de navegação/roteamento
            metricas: Sistema de métricas
            logger: Sistema de logging
            ridesharing_policy: Política de ride-sharing (padrão: SimplesRideSharingPolicy)
        """
        self.ambiente = ambiente
        self.alocador = alocador
        self.navegador = navegador
        self.metricas = metricas
        self.logger = logger
        self.ridesharing_policy = ridesharing_policy or SimplesRideSharingPolicy()
        self.display = None  # Será configurado externamente se necessário
    
    def configurar_display(self, display):
        """Configura o display para atualizações visuais."""
        self.display = display
    
    def processar_pedido(self, pedido, tempo_simulacao) -> Optional[object]:
        """
        Processa um pedido individual.
        
        Args:
            pedido: Pedido a processar
            tempo_simulacao: Tempo atual da simulação
            
        Returns:
            Veículo com viagem iniciada, ou None se pedido rejeitado
        """
        horario_log = tempo_simulacao.strftime('%H:%M:%S')
        self.logger.log(f"\n {horario_log} - [cyan]Processando Pedido #{pedido.id}[/]")
        
        # 1. Validar e calcular rota do pedido
        rota_viagem, distancia_viagem, origem_nome, destino_nome = self._validar_rota_pedido(pedido)
        if rota_viagem is None:
            return False
        
        # 2. Escolher veículo apropriado
        veiculo = self._escolher_veiculo_para_pedido(pedido, rota_viagem, distancia_viagem)
        if veiculo is None:
            return False
        
        self.logger.log(f"  [✓][/] Veículo alocado: {veiculo.id_veiculo}")
        self.ambiente.atribuir_pedido_a_veiculo(pedido, veiculo)
        
        # 3. Ajustar rotas para ride-sharing se aplicável
        if pedido.ride_sharing and self.ridesharing_policy.permite_ridesharing():
            ajuste = self.ridesharing_policy.ajustar_rotas(
                veiculo, origem_nome, destino_nome, self.navegador, self.ambiente.grafo
            )
            if ajuste:
                rota_viagem, distancia_viagem = ajuste
        
        # 4. Recuperar rota veículo -> cliente
        rota_ate_cliente = veiculo.rota_ate_cliente
        distancia_ate_cliente = veiculo.distancia_ate_cliente
        distancia_total = distancia_ate_cliente + distancia_viagem
        
        # 5. Calcular métricas da viagem
        metricas_viagem = self._calcular_metricas_viagem(
            rota_ate_cliente, rota_viagem, veiculo, distancia_viagem
        )
        
        # 6. Log de informações
        self.logger.info_viagem(rota_ate_cliente, rota_viagem, distancia_total, metricas_viagem)
        
        # 7. Iniciar viagem
        if not self._iniciar_viagem_pedido(
            veiculo, pedido, rota_ate_cliente, rota_viagem,
            distancia_ate_cliente, distancia_viagem, tempo_simulacao
        ):
            return None
        
        # 8. Registar métricas
        self.metricas.registar_pedido_atendido(
            pedido_id=pedido.id,
            veiculo_id=veiculo.id_veiculo,
            tempo_resposta=metricas_viagem['tempo_ate_cliente'],
            distancia=distancia_viagem,
            custo=metricas_viagem['custo'],
            emissoes=metricas_viagem['emissoes']
        )
        
        self.logger.log(
            f"  [✓][/] Viagem iniciada - ETA: "
            f"{metricas_viagem['tempo_ate_cliente'] + metricas_viagem['tempo_viagem']:.1f} min"
        )
        
        # 9. Atualizar display se disponível
        if self.display:
            nova_viagem_rota = veiculo.viagens[-1].rota if veiculo.viagens else []
            self.display.atualizar(pedido, veiculo, nova_viagem_rota)
        
        # Retornar veículo para que GestorViagens o adicione às viagens ativas
        return veiculo
    
    def _validar_rota_pedido(self, pedido) -> Tuple[Optional[List[str]], float, str, str]:
        """
        Valida e calcula a rota do pedido.
        
        Returns:
            Tupla (rota_viagem, distancia_viagem, origem_nome, destino_nome)
            ou (None, 0, origem, destino) se inválido
        """
        origem_nome, destino_nome = self.ambiente.obter_nomes_nos_pedido(pedido)
        
        rota_viagem = self.navegador.calcular_rota(
            self.ambiente.grafo, origem_nome, destino_nome
        )
        
        if rota_viagem is None or len(rota_viagem) < 2:
            self.logger.log(
                f"  [X][/] Rota pedido não encontrada ({origem_nome} -> {destino_nome})"
            )
            self.metricas.registar_pedido_rejeitado(pedido.id, "Rota pedido não encontrada")
            if self.display and hasattr(self.display, 'registrar_rejeicao'):
                self.display.registrar_rejeicao()
            return (None, 0, origem_nome, destino_nome)
        
        distancia_viagem = self.ambiente.grafo.calcular_distancia_rota(rota_viagem)
        return (rota_viagem, distancia_viagem, origem_nome, destino_nome)
    
    def _escolher_veiculo_para_pedido(self, pedido, rota_viagem, distancia_viagem):
        """
        Escolhe o veículo apropriado para o pedido.
        
        Returns:
            Veículo escolhido ou None se nenhum disponível
        """
        # Determinar lista de veículos elegíveis
        if pedido.ride_sharing and self.ridesharing_policy.permite_ridesharing():
            lista_veiculos = self.ambiente.listar_veiculos_ridesharing()
        else:
            lista_veiculos = self.ambiente.listar_veiculos_disponiveis()
        
        # Usar alocador para escolher veículo
        veiculo = self.alocador.escolher_veiculo(
            pedido=pedido,
            veiculos_disponiveis=lista_veiculos,
            grafo=self.ambiente.grafo,
            rota_pedido=rota_viagem,
            distancia_pedido=distancia_viagem,
        )
        
        if veiculo is None:
            self.logger.log(
                f"  [!][/] Nenhum veículo disponível/autónomo para o pedido #{pedido.id}"
            )
            self.metricas.registar_pedido_rejeitado(
                pedido.id, "Sem veículos com autonomia suficiente"
            )
            if self.display and hasattr(self.display, 'registrar_rejeicao'):
                self.display.registrar_rejeicao()
        
        return veiculo
    
    def _calcular_metricas_viagem(self, rota_ate_cliente, rota_viagem, veiculo, distancia_viagem) -> Dict:
        """
        Calcula métricas da viagem.
        
        Returns:
            Dict com tempo_ate_cliente, tempo_viagem, custo, emissoes
        """
        tempo_ate_cliente = self.ambiente._calcular_tempo_rota(rota_ate_cliente) * 60
        tempo_viagem = self.ambiente._calcular_tempo_rota(rota_viagem) * 60
        custo = distancia_viagem * veiculo.custo_operacional_km
        emissoes = self.ambiente._calcular_emissoes(veiculo, distancia_viagem)
        
        return {
            'tempo_ate_cliente': tempo_ate_cliente,
            'tempo_viagem': tempo_viagem,
            'custo': custo,
            'emissoes': emissoes
        }
    
    def _iniciar_viagem_pedido(self, veiculo, pedido, rota_ate_cliente, rota_viagem,
                               distancia_ate_cliente, distancia_viagem, tempo_inicio) -> bool:
        """
        Inicia a viagem do veículo.
        
        Returns:
            True se iniciou com sucesso, False caso contrário
        """
        iniciou = veiculo.iniciar_viagem(
            pedido=pedido,
            rota_ate_cliente=rota_ate_cliente,
            rota_pedido=rota_viagem,
            distancia_ate_cliente=distancia_ate_cliente,
            distancia_pedido=distancia_viagem,
            tempo_inicio=tempo_inicio,
            grafo=self.ambiente.grafo
        )
        
        if not iniciou:
            self.logger.log(
                f"  [yellow]![/] Capacidade excedida para ride-sharing no veículo {veiculo.id_veiculo}"
            )
            self.metricas.registar_pedido_rejeitado(
                pedido.id, "Capacidade ride-sharing excedida"
            )
            if self.display and hasattr(self.display, 'registrar_rejeicao'):
                self.display.registrar_rejeicao()
        
        return iniciou
