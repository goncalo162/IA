"""
Políticas de recarga/abastecimento de veículos.
"""
from abc import ABC, abstractmethod
from typing import Optional
from datetime import timedelta


class RecargaPolicy(ABC):
    """Classe abstrata para políticas de recarga."""
    
    @abstractmethod
    def deve_agendar_recarga(self, veiculo) -> bool:
        """
        Determina se um veículo deve ser agendado para recarga.
        
        Args:
            veiculo: Veículo a verificar
            
        Returns:
            True se deve agendar recarga, False caso contrário
        """
        pass
    
    @abstractmethod
    def permite_recarga(self) -> bool:
        """Retorna True se a política permite recargas automáticas."""
        pass


class RecargaAutomaticaPolicy(RecargaPolicy):
    """
    Política que agenda recargas automaticamente quando veiculo não tem viagens ativas.
    
    Veículos que ficam abaixo do limiar de autonomia são automaticamente
    direcionados para postos de abastecimento.
    """
    
    def permite_recarga(self) -> bool:
        return True
    
    def deve_agendar_recarga(self, veiculo) -> bool:
        """
        Verifica se o veículo precisa de recarga e não tem viagens ativas.
        """
        # Só agendar recarga se não tiver viagens ativas
        if veiculo.viagem_ativa:
            return False
        
        # Verificar se precisa reabastecer
        return veiculo.precisa_reabastecer()


class SemRecargaPolicy(RecargaPolicy):
    """
    Política que não agenda recargas automáticas.
    
    Veículos devem ter autonomia suficiente para toda a simulação,
    ou ficam indisponíveis quando a autonomia acaba.
    """
    
    def permite_recarga(self) -> bool:
        return False
    
    def deve_agendar_recarga(self, veiculo) -> bool:
        """Nunca agenda recarga."""
        return False


class RecargaDuranteViagemPolicy(RecargaPolicy):
    """
    Política que permite agendar recargas durante a viagem.
    """

    def permite_recarga(self) -> bool:
        return True

    def deve_agendar_recarga(self, veiculo) -> bool:
        """
        Agenda recarga se o veículo precisar reabastecer.
        """

        # Se tem viagens ativas, verificar se a autonomia é suficiente
        # para completar as viagens remanescentes (soma das distâncias).
        distancia_remanescente = 0.0

        if len(veiculo.viagens) > 0:
            viagem_total = veiculo.viagens[-1]
            distancia_remanescente = viagem_total.distancia_restante_km()

        # Se não há informação de distância remanescente (== 0) mantém comportamento clássico
        if distancia_remanescente <= 0.0 or not veiculo.viagem_ativa:
            return veiculo.precisa_reabastecer()

        # Se a autonomia atual não for suficiente para a distância remanescente, então deve agendar a recarga.
        return not veiculo.autonomia_suficiente_para(distancia_remanescente)
