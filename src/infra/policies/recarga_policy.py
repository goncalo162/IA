"""
Políticas de recarga/abastecimento de veículos.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from infra.entidades.recarga import PlanoRecarga


class RecargaPolicy(ABC):
    """Classe abstrata para políticas de recarga."""

    @abstractmethod
    def nome_politica(self) -> str:
        """Retorna o nome da política de recarga."""
        pass

    @abstractmethod
    def deve_agendar_recarga(self, veiculo, fim_viagem: bool = False) -> bool:
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

    @abstractmethod
    def encontrar_planos_recarga(
        self,
        veiculo,
        grafo,
        navegador,
        ambiente,
        rota_restante: Optional[List[str]] = None,
        tempo_simulacao: Optional[datetime] = None
    ) -> List[PlanoRecarga]:
        """
        Encontra planos de recarga viáveis para um veículo.

        Método puro que não altera estado - apenas calcula e retorna planos.

        Args:
            veiculo: Veículo que necessita recarga
            grafo: Grafo do ambiente
            navegador: Navegador para cálculo de rotas
            ambiente: Ambiente para acessar postos e calcular tempos
            rota_restante: Rota restante do veículo (para políticas que consideram desvio)
            tempo_simulacao: Tempo atual da simulação (para políticas time-aware)

        Returns:
            Lista de PlanoRecarga ordenados por viabilidade (melhor primeiro).
            Lista vazia se não houver planos viáveis.
        """
        pass

    def calcular_penalizacao_recarga(self, plano: Optional[PlanoRecarga]) -> float:
        """
        Calcula penalização para score de alocação quando veículo precisa de recarga.

        Args:
            plano: Plano de recarga do veículo (None se não houver plano)

        Returns:
            Penalização a adicionar ao score (0 se não há plano ou plano inviável)
        """
        if not plano or not plano.viavel:
            return 0.0

        # Calcular penalização baseada nos componentes do plano
        penalizacao = plano.tempo_recarga_min + plano.distancia_km + plano.custo_extra_estimado

        return penalizacao

    def _encontrar_posto_mais_proximo(
            self,
            veiculo,
            grafo,
            navegador,
            ambiente,
            postos,
            margem_seguranca: float = 5.0):
        """Fallback genérico: encontra posto mais próximo quando não há rota restante.

        Esta implementação é utilizada por políticas que precisam de um plano
        simples baseado no posto mais próximo acessível. Mantemos como método
        protegido (privado para uso interno nas subclasses).
        """
        melhor_plano = None
        distancia_minima = float('inf')
        tipo_posto = veiculo.tipo_posto_necessario()

        for posto_nome in postos:
            rota = navegador.calcular_rota(grafo, veiculo.localizacao_atual, posto_nome)

            if not rota or len(rota) < 2:
                continue

            distancia = grafo.calcular_distancia_rota(rota)
            if distancia is None or distancia >= distancia_minima:
                continue

            # Verifica autonomia para chegar
            if not veiculo.autonomia_suficiente_para(distancia, margem_seguranca=0):
                continue

            tempo_viagem_h = ambiente._calcular_tempo_rota(rota) if hasattr(
                ambiente, '_calcular_tempo_rota') else distancia / 50.0
            tempo_recarga_min = veiculo.tempoReabastecimento()
            custo_viagem = distancia * veiculo.custo_operacional_km
            custo_tempo = tempo_recarga_min * (veiculo.custo_operacional_km * 0.5)

            melhor_plano = PlanoRecarga(
                posto=posto_nome,
                tipo_posto=tipo_posto,
                rota=rota,
                distancia_km=distancia,
                desvio_rota_km=None,
                tempo_viagem_h=tempo_viagem_h,
                tempo_recarga_min=tempo_recarga_min,
                custo_extra_estimado=custo_viagem + custo_tempo,
                autonomia_necessaria_km=distancia + margem_seguranca,
                margem_seguranca_km=margem_seguranca,
                observacoes="Posto mais próximo (política base)"
            )
            distancia_minima = distancia

        return [melhor_plano] if melhor_plano else []


class RecargaAutomaticaPolicy(RecargaPolicy):
    """
    Política que agenda recargas automaticamente quando veiculo acaba as viagens e não tem mais viagens ativas.

    Veículos que ficam abaixo do limiar de autonomia são automaticamente
    direcionados para postos de abastecimento.
    """

    def nome_politica(self) -> str:
        return "RecargaAutomaticaPolicy"

    def permite_recarga(self) -> bool:
        return True

    def deve_agendar_recarga(self, veiculo, fim_viagem: bool = False) -> bool:
        """
        Verifica se o veículo precisa de recarga no fim de uma viageme não tem mais viagens ativas.
        """
        # Se nao for fim de viagem, não agenda recarga (pode ter sido chamado por alocador)
        if not fim_viagem:
            return False

        # Só agendar recarga se não tiver viagens ativas
        if veiculo.viagem_ativa:
            return False

        # Verificar se precisa reabastecer
        return veiculo.precisa_reabastecer()

    def encontrar_planos_recarga(
        self,
        veiculo,
        grafo,
        navegador,
        ambiente,
        rota_restante: Optional[List[str]] = None,
        tempo_simulacao: Optional[datetime] = None
    ) -> List[PlanoRecarga]:
        """
        Encontra o posto mais próximo acessível.

        Retorna lista com um único plano (posto mais próximo) ou lista vazia.
        """
        # Obter postos compatíveis
        tipo_posto = veiculo.tipo_posto_necessario()
        postos = ambiente.listar_postos_por_tipo(tipo_posto)

        if not postos:
            return []
        # Delegar para o helper genérico
        return self._encontrar_posto_mais_proximo(veiculo, grafo, navegador, ambiente, postos)


class SemRecargaPolicy(RecargaPolicy):
    """
    Política que não agenda recargas automáticas.

    Veículos devem ter autonomia suficiente para toda a simulação,
    ou ficam indisponíveis quando a autonomia acaba.
    """

    def nome_politica(self) -> str:
        return "SemRecargaPolicy"

    def permite_recarga(self) -> bool:
        return False

    def deve_agendar_recarga(self, veiculo, fim_viagem: bool = False) -> bool:
        """Nunca agenda recarga."""
        return False

    def encontrar_planos_recarga(
        self,
        veiculo,
        grafo,
        navegador,
        ambiente,
        rota_restante: Optional[List[str]] = None,
        tempo_simulacao: Optional[datetime] = None
    ) -> List[PlanoRecarga]:
        """Nunca retorna planos de recarga."""
        return []


class RecargaDuranteViagemPolicy(RecargaPolicy):
    """
    Política que permite agendar recargas durante a viagem.
    Apenas aceita postos que estejam na rota planejada (sem desvios).
    """

    def nome_politica(self) -> str:
        return "RecargaDuranteViagemPolicy"

    def permite_recarga(self) -> bool:
        return True

    def deve_agendar_recarga(self, veiculo, fim_viagem: bool = False) -> bool:
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

        # Se a autonomia atual não for suficiente para a distância remanescente,
        # então deve agendar a recarga.
        return not veiculo.autonomia_suficiente_para(distancia_remanescente)

    def encontrar_planos_recarga(
        self,
        veiculo,
        grafo,
        navegador,
        ambiente,
        rota_restante: Optional[List[str]] = None,
        tempo_simulacao: Optional[datetime] = None
    ) -> List[PlanoRecarga]:
        """
        Encontra postos que estejam na rota planeada (sem desvios).

        Retorna lista de postos que estão na rota restante, ordenados por distância.
        """
        tipo_posto = veiculo.tipo_posto_necessario()
        postos = ambiente.listar_postos_por_tipo(tipo_posto)

        if not postos:
            return []

        # Se não há rota restante, comportar como RecargaAutomaticaPolicy (posto mais próximo)
        if not rota_restante or len(rota_restante) <= 1:
            return super()._encontrar_posto_mais_proximo(veiculo, grafo, navegador, ambiente, postos)

        planos = []
        margem_seguranca = 5.0

        # Apenas considerar postos que estão na rota planejada
        for posto_nome in postos:
            # Verificar se posto está na rota
            if posto_nome not in rota_restante:
                continue

            # Calcular rota até o posto
            rota = navegador.calcular_rota(grafo, veiculo.localizacao_atual, posto_nome)

            if not rota or len(rota) < 2:
                continue

            distancia = grafo.calcular_distancia_rota(rota)
            if distancia is None:
                continue

            # Verificar autonomia para chegar
            if not veiculo.autonomia_suficiente_para(distancia, margem_seguranca=0):
                continue

            # Calcular tempos
            tempo_viagem_h = ambiente._calcular_tempo_rota(rota) if hasattr(
                ambiente, '_calcular_tempo_rota') else distancia / 50.0
            tempo_recarga_min = veiculo.tempoReabastecimento()

            # Calcular custo extra (sem penalização de desvio pois está na rota)
            custo_viagem = distancia * veiculo.custo_operacional_km
            custo_tempo = tempo_recarga_min * (veiculo.custo_operacional_km * 0.5)
            custo_extra = custo_viagem + custo_tempo

            plano = PlanoRecarga(
                posto=posto_nome,
                tipo_posto=tipo_posto,
                rota=rota,
                distancia_km=distancia,
                desvio_rota_km=0.0,  # Sem desvio - está na rota
                tempo_viagem_h=tempo_viagem_h,
                tempo_recarga_min=tempo_recarga_min,
                custo_extra_estimado=custo_extra,
                autonomia_necessaria_km=distancia + margem_seguranca,
                margem_seguranca_km=margem_seguranca,
                observacoes="Posto na rota planejada"
            )

            planos.append(plano)

        # Ordenar por distância (posto mais próximo primeiro)
        planos.sort(key=lambda p: p.distancia_km)

        return planos
