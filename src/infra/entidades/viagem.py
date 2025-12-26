from typing import List, Optional
from infra.entidades.pedidos import Pedido


class ViagemBase:
    """Classe base para viagens, contém lógica comum de progresso e segmentos."""

    def __init__(self, rota: List[str], distancia_total: float, tempo_inicio,
                 grafo, velocidade_media: float = 50.0):
        self.rota = rota or []
        self.distancia_total = float(distancia_total)
        self.distancia_percorrida = 0.0
        self.tempo_inicio = tempo_inicio
        self.indice_segmento_atual = 0
        self.distancia_no_segmento = 0.0
        self._viagem_ativa = True
        self.segmentos = self._calcular_segmentos(rota, grafo, velocidade_media)

    def _calcular_segmentos(
            self,
            rota: List[str],
            grafo,
            velocidade_media: float = 50.0) -> List[dict]:
        """Calcula informações dos segmentos para uma rota."""
        segmentos = []
        for i in range(len(rota) - 1):
            origem = rota[i]
            destino = rota[i + 1]
            aresta = grafo.getEdge(origem, destino)

            if not aresta:
                raise ValueError(f"Rota inválida: não existe aresta entre {origem} -> {destino}")

            distancia = aresta.getQuilometro()
            velocidade = aresta.getVelocidadeMaxima()
            transito = aresta.getTransito()

            tempo_base = distancia / velocidade if velocidade > 0 else distancia / velocidade_media
            fator = transito.value if getattr(transito, 'value', None) is not None else 1.0

            segmentos.append({
                'origem': origem,
                'destino': destino,
                'distancia': distancia,
                'velocidade': velocidade,
                'tempo_horas': tempo_base * fator
            })
        return segmentos

    def atualizar_progresso(self, tempo_decorrido_horas: float) -> bool:
        """Atualiza o progresso da viagem. Retorna True se concluída."""
        if not self._viagem_ativa:
            return False

        if not self.segmentos or self.indice_segmento_atual >= len(self.segmentos):
            self._viagem_ativa = False
            return True

        tempo_restante = tempo_decorrido_horas

        while tempo_restante > 0 and self.indice_segmento_atual < len(self.segmentos):
            segmento = self.segmentos[self.indice_segmento_atual]
            distancia_segmento = segmento['distancia']
            tempo_segmento = segmento['tempo_horas']

            distancia_restante_segmento = distancia_segmento - self.distancia_no_segmento
            tempo_necessario_segmento = tempo_segmento * \
                (distancia_restante_segmento / distancia_segmento) if distancia_segmento > 0 else 0

            if tempo_restante >= tempo_necessario_segmento:
                self.distancia_percorrida += distancia_restante_segmento
                tempo_restante -= tempo_necessario_segmento
                self.indice_segmento_atual += 1
                self.distancia_no_segmento = 0.0
            else:
                proporcao = tempo_restante / tempo_necessario_segmento if tempo_necessario_segmento > 0 else 0
                distancia_avancada = distancia_restante_segmento * proporcao
                self.distancia_percorrida += distancia_avancada
                self.distancia_no_segmento += distancia_avancada
                tempo_restante = 0

        if self.indice_segmento_atual >= len(self.segmentos):
            self._viagem_ativa = False
            return True

        return False

    @property
    def viagem_ativa(self) -> bool:
        return self._viagem_ativa

    @property
    def progresso_percentual(self) -> float:
        if self.distancia_total == 0:
            return 100.0
        return min(100.0, (self.distancia_percorrida / self.distancia_total) * 100.0)


class ViagemRecarga(ViagemBase):
    """Viagem de um veículo até um posto de abastecimento/recarga."""

    def __init__(self, rota: List[str], destino_posto: str,
                 distancia_total: float, tempo_inicio, grafo,
                 velocidade_media: float = 50.0):
        super().__init__(rota, distancia_total, tempo_inicio, grafo, velocidade_media)
        self.destino_posto = destino_posto

    @property
    def localizacao_atual(self) -> Optional[str]:
        if self.indice_segmento_atual >= len(self.segmentos):
            return self.destino_posto
        return self.segmentos[self.indice_segmento_atual]['origem']

class ViagemReposicionamento(ViagemBase):
    """Viagem vazia usada para reposicionamento proativo (sem pedido)."""

    def __init__(self, rota: List[str], distancia_total: float, tempo_inicio, grafo,
                 velocidade_media: float = 50.0):

        super().__init__(rota, distancia_total, tempo_inicio, grafo, velocidade_media)
        self.pedido = None  # Reposicionamentos não têm pedido associado

    @property
    def destino(self):
        return self.rota[-1] if self.rota else None

    @property
    def localizacao_atual(self) -> Optional[str]:
        if self.indice_segmento_atual >= len(self.segmentos):
            return self.destino
        return self.segmentos[self.indice_segmento_atual]['origem']

    def aresta_na_rota_restante(self, nome_aresta: str, grafo) -> bool:
        """Verifica se uma aresta está na rota restante.
        
        Args:
            nome_aresta: Nome da aresta a verificar
            grafo: Grafo para obter informação das arestas
            
        Returns:
            True se a aresta está na rota restante, False caso contrário
        """
        if not self._viagem_ativa:
            return False
            
        # Calcular rota restante a partir do segmento atual
        rota_restante = self.rota[self.indice_segmento_atual:] if self.indice_segmento_atual < len(self.rota) else []
        
        if len(rota_restante) < 2:
            return False

        for i in range(len(rota_restante) - 1):
            aresta = grafo.getEdge(rota_restante[i], rota_restante[i + 1])
            if aresta and aresta.getNome() == nome_aresta:
                return True
        return False


class Viagem(ViagemBase):
    """Representa uma viagem em progresso.

    Encapsula rota, segmentos, progresso e timestamps.
    """

    def __init__(self, pedido: Pedido, rota_ate_cliente: List, rota_pedido: List,
                 distancia_ate_cliente: float, distancia_pedido: float,
                 tempo_inicio, grafo, velocidade_media: float = 50.0):

        self.pedido: Pedido = pedido
        self.rota_ate_cliente = rota_ate_cliente or []
        self.rota_pedido = rota_pedido or []

        # Rota completa = concatenação (sem repetir nó do cliente)
        if self.rota_ate_cliente:
            rota_completa = self.rota_ate_cliente + \
                (self.rota_pedido[1:] if self.rota_pedido else [])
        else:
            rota_completa = list(self.rota_pedido)

        self.distancia_ate_cliente = float(distancia_ate_cliente)
        self.distancia_pedido = float(distancia_pedido)
        distancia_total = self.distancia_ate_cliente + self.distancia_pedido

        # Inicializar classe base
        super().__init__(rota_completa, distancia_total, tempo_inicio, grafo, velocidade_media)

    def concluir(self):
        """Marcar viagem como concluída"""
        self._viagem_ativa = False

    @property
    def progresso_percentual(self) -> float:
        """Retorna o progresso da viagem em percentual (0-100)."""
        if not self._viagem_ativa or self.distancia_total == 0:
            return 0.0
        return min(100.0, (self.distancia_percorrida / self.distancia_total) * 100.0)

    @property
    def destino(self):
        return self.rota[-1] if self.rota else None

    @property
    def viagem_ativa(self) -> bool:
        """Propriedade controla acesso ao flag de atividade da viagem.

        Usa um atributo privado interno para evitar recursão quando for
        necessário definir ou consultar o estado a partir de outros módulos.
        """
        return bool(self._viagem_ativa)

    @viagem_ativa.setter
    def viagem_ativa(self, value: bool):
        self._viagem_ativa = bool(value)

    @property
    def pedido_id(self) -> Optional[int]:
        """Obter id do pedido quando existir."""
        return self.pedido.id if self.pedido else None

    def numero_passageiros(self) -> int:
        """Retorna o número de passageiros associados a esta viagem."""
        return self.pedido.numero_passageiros

    def passa_por(self, local: str) -> bool:
        """Indica se a rota restante desta viagem passa por `local`.

        Considera do segmento atual (`indice_segmento_atual`) até ao final da `rota`.
        `local` deve ser o nome de nó (string) presente na rota.
        """
        if not isinstance(local, str) or not local:
            return False
        restante = self.rota_restante()
        return local in restante

    def rota_restante(self) -> List[str]:
        """Retorna a rota restante (do segmento atual até ao fim)."""
        rota = self.rota
        if not rota:
            return []
        idx = self.indice_segmento_atual
        idx = max(0, min(idx, len(rota) - 1))
        return rota[idx:]

    def aresta_na_rota_restante(self, nome_aresta: str, grafo) -> bool:
        """Verifica se uma aresta específica está na rota restante da viagem.

        Args:
            nome_aresta: Nome da aresta a verificar
            grafo: Grafo para obter informação das arestas

        Returns:
            True se a aresta está na rota restante, False caso contrário
        """
        rota = self.rota_restante()
        if len(rota) < 2:
            return False

        for i in range(len(rota) - 1):
            aresta = grafo.getEdge(rota[i], rota[i + 1])
            if aresta and aresta.getNome() == nome_aresta:
                return True
        return False

    def posicao_atual(self) -> Optional[str]:
        """Retorna a posição atual do veículo na rota (nó atual ou mais recente)."""
        if not self.rota:
            return None
        idx = min(self.indice_segmento_atual, len(self.rota) - 1)
        return self.rota[idx]

    def aplicar_nova_rota(self, nova_rota: List[str], grafo) -> bool:
        """Aplica uma nova rota à viagem a partir da posição atual.

        Args:
            nova_rota: Nova rota calculada (da posição atual ao destino)
            grafo: Grafo do ambiente

        Returns:
            True se a rota foi aplicada com sucesso, False caso contrário
        """
        if not self._viagem_ativa or not nova_rota:
            return False

        try:
            novos_segmentos = self._calcular_segmentos(nova_rota, grafo)
        except ValueError:
            return False

        # Manter a parte já percorrida + nova rota
        rota_percorrida = self.rota[:self.indice_segmento_atual] if self.indice_segmento_atual > 0 else [
        ]
        self.rota = rota_percorrida + nova_rota

        # Atualizar segmentos
        self.segmentos = self.segmentos[:self.indice_segmento_atual] + novos_segmentos
        self.distancia_no_segmento = 0.0

        # Recalcular distâncias
        nova_distancia = sum(seg['distancia'] for seg in novos_segmentos)
        self.distancia_total = self.distancia_percorrida + nova_distancia

        return True

    def tempo_restante_horas(self) -> float:
        """Retorna o tempo estimado restante em horas."""
        return sum(seg['tempo_horas'] for seg in self.segmentos[self.indice_segmento_atual:])

    def distancia_restante_km(self) -> float:
        """Retorna a distância estimada restante em km."""
        return self.distancia_total - self.distancia_percorrida
