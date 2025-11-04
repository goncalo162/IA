# models/pedido.py
from datetime import datetime
from enum import Enum
from typing import Optional, Union


class EstadoPedido(Enum):
    PENDENTE = 1
    EM_CURSO = 2
    CONCLUIDO = 3

class Pedido:
    """
    Representa um pedido de transporte feito por um cliente da TaxiGreen.
    """

    def __init__(self, pedido_id: int, origem: int, destino: int, passageiros: int,
                 horario_pretendido: datetime, prioridade: int = 1,
                 preferencia_ambiental: int = 0):

        # atributos protegidos — aceder via propriedades
        self._id = pedido_id
        self._origem = origem
        self._destino = destino
        self._passageiros = passageiros
        self._horario_pretendido = horario_pretendido
        self._prioridade = prioridade
        self._preferencia_ambiental = preferencia_ambiental
        self._estado: EstadoPedido = EstadoPedido.PENDENTE



    def __str__(self) -> str:
        # representação mais amigável para impressão ao utilizador
        return (f"Pedido #{self.id}: {self.origem} → {self.destino} | "
                f"{self.passageiros} pax | prioridade {self.prioridade} | "
                f"estado: {self.estado.name}")

    def __eq__(self, other):
        return isinstance(other, Request) and self.id == other.id

    # -------------------- Propriedades (getters/setters) --------------------
    @property
    def id(self) -> int:
        return self._id

    @property
    def origem(self) -> str:
        return self._origem

    @property
    def destino(self) -> str:
        return self._destino

    @property
    def passageiros(self) -> int:
        return self._passageiros

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
    def atribuir_a(self) -> Optional[int]:
        return self._atribuir_a

    @property
    def estado(self) -> EstadoPedido:
        return self._estado

    @estado.setter
    def estado(self, value: EstadoPedido):
        if not isinstance(value, EstadoPedido):
            raise ValueError("estado deve ser um EstadoPedido")
        self._estado = value

