"""
Modelos de dados para gestão de recargas/abastecimentos.
"""
from dataclasses import dataclass
from typing import Optional, List
from infra.grafo.node import TipoNodo


@dataclass
class PlanoRecarga:
    """
    Plano de recarga/abastecimento para um veículo.

    Encapsula todas as informações necessárias para decidir e executar
    uma recarga, incluindo rota, custos e validações.
    """
    # Posto selecionado
    posto: str
    tipo_posto: TipoNodo

    # Roteamento
    rota: List[str]
    distancia_km: float

    # Temporização
    tempo_viagem_h: float
    tempo_recarga_min: float

    # Custos e validações
    custo_extra_estimado: float  # Custo adicional da recarga (viagem + tempo)
    autonomia_necessaria_km: float  # Autonomia mínima para chegar ao posto
    margem_seguranca_km: float = 10.0  # Margem de segurança aplicada

    # Desvio (opcional, colocado depois de campos obrigatórios)
    desvio_rota_km: Optional[float] = None  # Quanto desvia da rota original

    # Metadados
    observacoes: Optional[str] = None

    @property
    # TODO: rever porque acho que a rota nao precisa ser maior que 2 por
    # exemplo se estiver no posto, ou isso ja é tratado antes?
    def viavel(self) -> bool:
        """Verifica se o plano é minimamente viável."""
        return (self.posto is not None and
                len(self.rota) >= 2 and
                self.distancia_km > 0)

    @property
    def tempo_total_h(self) -> float:
        """Retorna o tempo total (viagem + recarga) em horas."""
        return self.tempo_viagem_h + (self.tempo_recarga_min / 60.0)

    def __repr__(self) -> str:
        desvio_str = f", desvio={
            self.desvio_rota_km:.1f}km" if self.desvio_rota_km is not None else ""
        return (f"PlanoRecarga(posto={self.posto}, dist={self.distancia_km:.1f}km{desvio_str}, "
                f"tempo={self.tempo_total_h:.2f}h, custo={self.custo_extra_estimado:.2f})")
