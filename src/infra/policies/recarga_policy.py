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
    Política que agenda recargas automaticamente quando necessário.
    
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
        return veiculo.precisa_reabastecer() if hasattr(veiculo, 'precisa_reabastecer') else False


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
