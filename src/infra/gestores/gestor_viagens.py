"""
Gestor de viagens: PROPRIETÁRIO EXCLUSIVO de viagens_ativas.
Gerencia todo o ciclo de vida: adição, atualização, conclusão e remoção.
"""
from typing import Dict, List, Tuple


class GestorViagens:
    """
    Responsável EXCLUSIVO por gerenciar viagens_ativas.
    
    Princípio: Este gestor é o ÚNICO que pode adicionar/remover do dicionário.
    Outros gestores apenas INFORMAM sobre eventos, não modificam diretamente.
    """
    
    def __init__(self, ambiente, metricas, logger):
        """
        Inicializa o gestor de viagens.
        
        Args:
            ambiente: Gestão do ambiente (grafo, veículos, pedidos)
            metricas: Sistema de métricas
            logger: Sistema de logging
        """
        self.ambiente = ambiente
        self.metricas = metricas
        self.logger = logger
        self.gestor_recargas = None  # Será configurado externamente
        self.viagens_ativas: Dict = {}  # Propriedade exclusiva deste gestor
    
    def configurar_gestor_recargas(self, gestor_recargas):
        """Configura o gestor de recargas para coordenação."""
        self.gestor_recargas = gestor_recargas
    
    def adicionar_viagem(self, veiculo):
        """
        Adiciona um veículo às viagens ativas.
        
        Este é o ÚNICO método que adiciona ao dicionário.
        
        Args:
            veiculo: Veículo com viagem iniciada
        """
        self.viagens_ativas[veiculo.id_veiculo] = veiculo
    
    def remover_viagem(self, veiculo_id: str):
        """
        Remove um veículo das viagens ativas.
        
        Este é o ÚNICO método que remove do dicionário.
        
        Args:
            veiculo_id: ID do veículo a remover
        """
        if veiculo_id in self.viagens_ativas:
            del self.viagens_ativas[veiculo_id]
    
    def atualizar_viagens_ativas(self, tempo_passo_horas: float,
                                 tempo_simulacao) -> List[Tuple]:
        """
        Atualiza o progresso de todas as viagens em curso.
        
        Args:
            tempo_passo_horas: Tempo simulado decorrido neste passo, em horas
            tempo_simulacao: Tempo atual da simulação
            
        Returns:
            Lista de veículos que chegaram a postos (para gestor de recargas processar)
        """
        if not self.viagens_ativas:
            return []
        
        # Atualizar progresso de viagens usando o ambiente
        viagens_concluidas, veiculos_chegaram_posto = self.ambiente.atualizar_viagens_ativas(
            self.viagens_ativas,
            tempo_passo_horas
        )
        
        # Processar viagens concluídas
        for veiculo_id, veiculo, viagem in viagens_concluidas:
            self._concluir_viagem(veiculo, viagem)
            
            # Remover veículo da lista ativa apenas se não houver mais viagens
            if not veiculo.viagem_ativa:
                self.remover_viagem(veiculo_id)
                
                # Verificar necessidade de recarga após conclusão
                if self.gestor_recargas:
                    self.gestor_recargas.verificar_e_agendar_recarga(
                        veiculo, tempo_simulacao
                    )
        
        # Retornar veículos que chegaram a postos (para o gestor de recargas processar)
        return veiculos_chegaram_posto
    
    def _concluir_viagem(self, veiculo, viagem):
        """
        Processa a conclusão de uma viagem específica.
        
        Args:
            veiculo: Veículo que concluiu a viagem
            viagem: Viagem concluída
        """
        pedido_id = viagem.pedido_id
        
        # Marcar pedido como concluído no ambiente
        self.ambiente.concluir_pedido(pedido_id, viagem)
        
        # Log da conclusão
        log_msg = (
            f"[green]✓[/] Viagem concluída: Pedido #{pedido_id} | "
            f"Veículo {veiculo.id_veiculo} em {veiculo.localizacao_atual}"
        )
        self.logger.log(log_msg)

