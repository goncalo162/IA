from datetime import datetime
from enum import Enum
from typing import Optional


class EstadoPedido(Enum):
    PENDENTE = 1
    EM_CURSO = 2
    CONCLUIDO = 3


class Pedido:
    """
    Representa um pedido de transporte.
    """

    def __init__(self, pedido_id: int, origem: int, destino: int, passageiros: int,
                 horario_pretendido: datetime, prioridade: int = 0,
                 preferencia_ambiental: int = 0, ride_sharing: bool = False):

        self._id = pedido_id
        self._origem = origem
        self._destino = destino
        self._numero_passageiros = passageiros
        self._horario_pretendido = horario_pretendido
        self._prioridade = prioridade  # Maior valor = maior prioridade (0 a 5)
        self._preferencia_ambiental = preferencia_ambiental
        self._ride_sharing = bool(ride_sharing)
        self._estado: EstadoPedido = EstadoPedido.PENDENTE
        self._atribuir_a: Optional[int] = None

    def __str__(self) -> str:
        return (f"Pedido #{self.id}: {self.origem} → {self.destino} | "
                f"{self.numero_passageiros} pax | prioridade {self.prioridade} | "
                f"estado: {self.estado.name}")

    def __eq__(self, other):
        return isinstance(other, Pedido) and self.id == other.id

    # -------------------- Propriedades (getters/setters) --------------------
    @property
    def id(self) -> int:
        return self._id

    @property
    def origem(self) -> int:
        return self._origem

    @property
    def destino(self) -> int:
        return self._destino

    @property
    def numero_passageiros(self) -> int:
        return self._numero_passageiros

    @property
    def horario_pretendido(self) -> datetime:
        return self._horario_pretendido

    @property
    def prioridade(self) -> int:
        return self._prioridade

    @property
    def preferencia_ambiental(self) -> bool:
        return self._preferencia_ambiental

    @property
    def ride_sharing(self) -> bool:
        return self._ride_sharing

    @property
    def atribuir_a(self) -> Optional[int]:
        return self._atribuir_a

    @atribuir_a.setter
    def atribuir_a(self, value: Optional[int]):
        self._atribuir_a = value

    @property
    def estado(self) -> EstadoPedido:
        return self._estado

    @estado.setter
    def estado(self, value: EstadoPedido):
        if not isinstance(value, EstadoPedido):
            raise ValueError("estado deve ser um EstadoPedido")
        self._estado = value
