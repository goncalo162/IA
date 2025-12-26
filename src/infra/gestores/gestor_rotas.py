"""
Gestor de rotas: recalcula rotas afetadas por eventos de trânsito e outros.
"""
from typing import Dict, List, Set


class GestorRotas:
    """
    Responsável por gerir recálculos de rotas quando ocorrem alterações no grafo.
    
    Identifica viagens afetadas e recalcula rotas usando o navegador.
    """
    
    def __init__(self, ambiente, navegador, metricas, logger):
        """
        Inicializa o gestor de rotas.
        
        Args:
            ambiente: Gestão do ambiente (grafo, veículos, pedidos)
            navegador: Algoritmo de navegação/roteamento
            metricas: Sistema de métricas
            logger: Sistema de logging
        """
        self.ambiente = ambiente
        self.navegador = navegador
        self.metricas = metricas
        self.logger = logger
        self._arestas_alteradas: Set[str] = set()
    
    def registar_aresta_alterada(self, aresta: str):
        """
        Marca uma aresta como alterada para posterior recálculo.
        
        Args:
            aresta: Nome da aresta alterada
        """
        self._arestas_alteradas.add(aresta)
    
    def recalcular_rotas_afetadas(self, viagens_ativas: Dict):
        """
        Verifica todas as viagens ativas e recalcula as rotas que passam pelas arestas alteradas.
        
        Args:
            viagens_ativas: Dicionário {veiculo_id: veiculo} de viagens ativas
        """
        if not self._arestas_alteradas:
            return
        
        viagens_para_recalcular = self.ambiente.identificar_viagens_afetadas(
            self._arestas_alteradas,
            viagens_ativas
        )
        
        total_recalculadas = 0
        total_viagens_afetadas = 0
        
        for veiculo_id, veiculo, viagens_afetadas, aresta in viagens_para_recalcular:
            num_viagens = len(viagens_afetadas)
            total_viagens_afetadas += num_viagens
            
            self.logger.log(
                f"[RECÁLCULO] Veículo {veiculo_id} tem {num_viagens} viagem(ns) "
                f"afetada(s) por '{aresta}'"
            )
            
            # Recalcular rotas usando o navegador
            recalculos = self._recalcular_rotas_veiculo(veiculo, viagens_afetadas)
            
            for rec in recalculos:
                self.logger.log(
                    f"[RECÁLCULO] Viagem #{rec['pedido_id']} recalculada. "
                    f"Diferença: {rec['delta_tempo']:+.1f} min"
                )
                
                # Registar métricas
                self.metricas.registar_recalculo_rota(
                    pedido_id=rec['pedido_id'],
                    veiculo_id=veiculo_id,
                    diferenca_tempo=rec['delta_tempo'],
                    motivo="transito",
                    distancia_anterior=rec['distancia_anterior'],
                    distancia_nova=rec['distancia_nova']
                )
                total_recalculadas += 1
        
        if total_viagens_afetadas > 0:
            self.metricas.registar_evento_recalculo(total_viagens_afetadas)
            self.logger.log(f"[RECÁLCULO] Total de {total_recalculadas} rota(s) recalculada(s)")
        
        # Limpar lista de arestas alteradas após recálculo
        self._arestas_alteradas.clear()
    
    def _recalcular_rotas_veiculo(self, veiculo, viagens_afetadas) -> List[Dict]:
        """
        Recalcula rotas de viagens afetadas usando o navegador.
        
        Args:
            veiculo: Veículo com viagens a recalcular
            viagens_afetadas: Lista de viagens afetadas
            
        Returns:
            Lista de dicts com informações de recálculos
        """
        viagens_ativas = [v for v in viagens_afetadas if v.viagem_ativa]
        if not viagens_ativas:
            return []
        
        # Obter posição atual do veículo a partir da rota combinada
        rota_total = veiculo.rota_total_viagens()
        pos_atual = rota_total[0] if rota_total else None
        if not pos_atual:
            return []
        
        # Obter destinos
        destinos = veiculo.destinos_viagens_ativas()
        
        if len(destinos) == 0:
            return []
        
        # Caso simples: um destino
        if len(destinos) == 1:
            if pos_atual == destinos[0]:
                return []
            
            nova_rota = self.navegador.calcular_rota(self.ambiente.grafo, pos_atual, destinos[0])
            if nova_rota and len(nova_rota) >= 2:
                viagem = viagens_ativas[0]
                info = self.ambiente.aplicar_nova_rota(viagem, nova_rota)
                return [info] if info else []
            return []
        
        # Ride-sharing: rota combinada (múltiplos destinos)
        return self._recalcular_rota_ridesharing(veiculo, viagens_ativas, pos_atual, destinos)
    
    def _recalcular_rota_ridesharing(self, veiculo, todas_viagens_ativas, 
                                    pos_atual: str, destinos: List[str]) -> List[Dict]:
        """
        Recalcula rotas para ride-sharing com múltiplos destinos.
        
        Args:
            veiculo: Veículo com múltiplas viagens
            todas_viagens_ativas: Lista de viagens ativas do veículo
            pos_atual: Posição atual do veículo
            destinos: Lista de destinos das viagens
            
        Returns:
            Lista de informações de recálculo
        """
        # Remover duplicados mantendo a ordem
        destinos_unicos = list(dict.fromkeys(destinos))
        
        # Calcular rota combinada
        rota_combinada = [pos_atual]
        ponto_atual = pos_atual
        
        for destino in destinos_unicos:
            if destino == ponto_atual:
                continue
            segmento = self.navegador.calcular_rota(self.ambiente.grafo, ponto_atual, destino)
            if segmento and len(segmento) > 1:
                rota_combinada.extend(segmento[1:])  # Sem repetir o nó de junção
                ponto_atual = destino
        
        if len(rota_combinada) < 2:
            return []
        
        # Aplicar rota a cada viagem
        recalculos = []
        for viagem in todas_viagens_ativas:
            destino_viagem = viagem.destino
            
            if destino_viagem == pos_atual or destino_viagem not in rota_combinada:
                continue
            
            # A rota desta viagem vai até ao seu destino
            idx_destino = rota_combinada.index(destino_viagem)
            rota_viagem = rota_combinada[:idx_destino + 1]
            
            # Garantir que a rota tem pelo menos 2 nós
            if len(rota_viagem) < 2:
                continue
            
            info = self.ambiente.aplicar_nova_rota(viagem, rota_viagem)
            if info:
                recalculos.append(info)
        
        return recalculos
