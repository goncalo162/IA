"""
Sistema de eventos dinâmicos para a simulação.
Permite modelar situações como alterações de trânsito, falhas, etc.
"""
from enum import Enum
from typing import Optional, Callable
from datetime import datetime
import heapq

# TODO: rever estes eventos e adicionar os que sejam necessários


class TipoEvento(Enum):
    """Tipos de eventos que podem ocorrer na simulação."""
    ALTERACAO_TRANSITO = 1
    FALHA_VEICULO = 2
    ESTACAO_INDISPONIVEL = 3
    CONDICAO_METEOROLOGICA = 4
    # Eventos temporais da simulação
    CHEGADA_PEDIDO = 5
    INICIO_VIAGEM = 6
    FIM_VIAGEM = 7
    CHEGADA_ORIGEM = 8  # Veículo chegou ao cliente
    NECESSITA_RECARGA = 9


class Evento:
    """
    Representa um evento dinâmico na simulação.
    """

    def __init__(self, tipo: TipoEvento, timestamp: datetime,
                 duracao_minutos: Optional[float] = None,
                 dados_extra: Optional[dict] = None):
        self.tipo = tipo
        self.timestamp = timestamp
        self.duracao_minutos = duracao_minutos
        self.dados_extra = dados_extra or {}
        self.ativo = False


# NOTA: ativar e desativar não deveria deveria ter um metodo associado que altera internamente o estado do sistema?


    def ativar(self):
        """Ativa o evento."""
        self.ativo = True

    def desativar(self):
        """Desativa o evento."""
        self.ativo = False

    def __str__(self) -> str:
        estado = "ATIVO" if self.ativo else "INATIVO"
        return (f"Evento {self.tipo.name} [{estado}] às {self.timestamp} "
                f"(duração: {self.duracao_minutos} min)")


class EventoTemporal:
    """
    Evento temporal para a fila de eventos da simulação.
    Usa heap queue para ordenação eficiente por tempo.
    """

    def __init__(self, tempo: datetime, tipo: TipoEvento,
                 callback: Callable, dados: Optional[dict] = None,
                 prioridade: int = 0):
        """
        Args:
            tempo: Momento em que o evento deve ocorrer
            tipo: Tipo do evento
            callback: Função a ser chamada quando o evento ocorrer
            dados: Dados adicionais para o callback
        """
        self.tempo = tempo
        self.tipo = tipo
        self.callback = callback
        self.dados = dados or {}
        # Prioridade do evento (maior valor == maior prioridade)
        self.prioridade = int(prioridade)

    def executar(self):
        """Executa o callback do evento."""
        return self.callback(**self.dados)

    def __lt__(self, other):
        """Permite ordenar eventos por tempo na heap."""
        return self.tempo < other.tempo

    def __str__(self) -> str:
        return f"EventoTemporal[{self.tipo.name} @ {self.tempo.strftime('%H:%M:%S')}]"


class FilaEventos:
    """
    Fila de prioridade para eventos temporais.
    Eventos são ordenados por tempo de ocorrência.
    """

    def __init__(self):
        self._fila = []
        self._contador = 0  # Para desempate quando tempos são iguais

    def adicionar(self, evento: EventoTemporal):
        """Adiciona um evento à fila."""
        # Usar tupla (tempo, -prioridade, contador, evento) para garantir que
        # quando tempos forem iguais, eventos com maior prioridade sejam
        # processados primeiro. O contador garante ordem estável em desempates.
        heapq.heappush(self._fila, (evento.tempo, -evento.prioridade, self._contador, evento))
        self._contador += 1

    def proximo(self) -> Optional[EventoTemporal]:
        """Remove e retorna o próximo evento (mais cedo)."""
        if self._fila:
            _, _, _, evento = heapq.heappop(self._fila)
            return evento
        return None

    def espiar_proximo(self) -> Optional[EventoTemporal]:
        """Retorna o próximo evento sem removê-lo."""
        if self._fila:
            return self._fila[0][3]
        return None

    def tem_eventos(self) -> bool:
        """Verifica se há eventos na fila."""
        return len(self._fila) > 0

    def limpar(self):
        """Remove todos os eventos da fila."""
        self._fila.clear()
        self._contador = 0

    def tamanho(self) -> int:
        """Retorna o número de eventos na fila."""
        return len(self._fila)


class GestorEventos:
    """
    Classe responsável por gerir eventos durante a simulação.
    Inclui tanto eventos dinâmicos (trânsito, falhas) quanto eventos temporais.
    """

    def __init__(self):
        self.eventos = []
        self.eventos_ativos = []
        self.fila_temporal = FilaEventos()

    def adicionar_evento(self, evento: Evento):
        """Adiciona um novo evento dinâmico ao sistema."""
        self.eventos.append(evento)

    def agendar_evento(self, tempo: datetime, tipo: TipoEvento,
                       callback: Callable, dados: Optional[dict] = None,
                       prioridade: int = 0):
        """
        Agenda um evento temporal para execução futura.

        Args:
            tempo: Momento em que o evento deve ocorrer
            tipo: Tipo do evento
            callback: Função a ser chamada
            dados: Dados para passar ao callback
        """
        evento = EventoTemporal(tempo, tipo, callback, dados, prioridade=prioridade)
        self.fila_temporal.adicionar(evento)
        return evento

    def processar_eventos_ate(self, tempo_atual: datetime):
        """
        Processa todos os eventos temporais até o tempo especificado.

        Args:
            tempo_atual: Tempo limite para processar eventos

        Returns:
            Lista de eventos processados
        """
        eventos_processados = []

        while self.fila_temporal.tem_eventos():
            proximo = self.fila_temporal.espiar_proximo()
            if proximo and proximo.tempo <= tempo_atual:
                evento = self.fila_temporal.proximo()
                try:
                    evento.executar()
                    eventos_processados.append(evento)
                except Exception as e:
                    print(f"Erro ao executar evento {evento}: {e}")
            else:
                break

        return eventos_processados

    def atualizar(self, tempo_atual: datetime):
        """
        Atualiza o estado dos eventos dinâmicos baseado no tempo atual.
        Ativa eventos que devem começar e desativa eventos expirados.
        """
        for evento in self.eventos:
            # Verificar se evento deve ser ativado
            if not evento.ativo and tempo_atual >= evento.timestamp:
                evento.ativar()
                self.eventos_ativos.append(evento)

            # Verificar se evento deve ser desativado
            if evento.ativo and evento.duracao_minutos:
                tempo_fim = evento.timestamp
                # Adicionar duração (simplificado, assumindo timedelta)
                if (tempo_atual - evento.timestamp).total_seconds() / 60 > evento.duracao_minutos:
                    evento.desativar()
                    if evento in self.eventos_ativos:
                        self.eventos_ativos.remove(evento)

    def obter_eventos_ativos(self):
        """Retorna lista de eventos dinâmicos atualmente ativos."""
        return self.eventos_ativos.copy()

    # -------------------- Exemplos de criação de eventos --------------------

    # TODO: adicionar mais eventos conforme necessário

    # TODO: ler eventos de ficheiro json

    def aplicar_evento_transito(self, aresta_nome: str, fator_multiplicador: float):
        """
        Cria um evento de alteração de trânsito numa aresta específica.
        fator_multiplicador > 1.0 significa trânsito mais lento
        """
        evento = Evento(
            tipo=TipoEvento.ALTERACAO_TRANSITO,
            timestamp=datetime.now(),
            duracao_minutos=60,  # 1 hora por defeito
            dados_extra={
                'aresta': aresta_nome,
                'fator': fator_multiplicador
            }
        )
        self.adicionar_evento(evento)
        return evento
