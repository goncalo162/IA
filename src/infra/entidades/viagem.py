from typing import List


class Viagem:
    """Representa uma viagem em progresso.

    Encapsula rota, segmentos, progresso e timestamps. Foi extraída de Veiculo
    para separar responsabilidades (single responsibility).
    """

    def __init__(self, pedido_id: int, rota_ate_cliente: List, rota_pedido: List,
                 distancia_ate_cliente: float, distancia_pedido: float,
                 tempo_inicio, grafo, velocidade_media: float = 50.0):
        self.pedido_id = pedido_id

        # Rota separada em dois segmentos: veículo->cliente e cliente->destino
        self.rota_ate_cliente = rota_ate_cliente or []
        self.rota_pedido = rota_pedido or []

        # Rota completa = concatenação (sem repetir nó do cliente)
        if self.rota_ate_cliente:
            self.rota = self.rota_ate_cliente + (self.rota_pedido[1:] if self.rota_pedido else [])
        else:
            self.rota = list(self.rota_pedido)

        self.distancia_ate_cliente = float(distancia_ate_cliente)
        self.distancia_pedido = float(distancia_pedido)
        self.distancia_total = self.distancia_ate_cliente + self.distancia_pedido
        self.distancia_percorrida = 0.0
        self.tempo_inicio = tempo_inicio
        self.indice_segmento_atual = 0
        self.distancia_no_segmento = 0.0
        self.segmentos = []
        # Flag interna que indica se a viagem está ativa
        self._viagem_ativa = True

        # Pré-calcular informações dos segmentos ao longo da rota completa
        for i in range(len(self.rota) - 1):
            origem = self.rota[i]
            destino = self.rota[i + 1]
            aresta = grafo.getEdge(origem, destino)

            if aresta:
                distancia = aresta.getQuilometro()
                velocidade = aresta.getVelocidadeMaxima()
                transito = aresta.getTransito()

                tempo_base_horas = distancia / velocidade if velocidade > 0 else distancia / velocidade_media
                fator_transito = transito.value if getattr(transito, 'value', None) is not None else 1.0
                tempo_horas = tempo_base_horas * fator_transito

                self.segmentos.append({
                    'origem': origem,
                    'destino': destino,
                    'distancia': distancia,
                    'velocidade': velocidade,
                    'tempo_horas': tempo_horas
                })
            else:
                distancia_fallback = 10.0
                self.segmentos.append({
                    'origem': origem,
                    'destino': destino,
                    'distancia': distancia_fallback,
                    'velocidade': velocidade_media,
                    'tempo_horas': distancia_fallback / velocidade_media
                })

    def atualizar_progresso(self, tempo_decorrido_horas: float) -> bool:
        """
        Atualiza as físicas do progresso da viagem baseado no tempo decorrido.
        Retorna True se a viagem foi concluída.
        """
        if not self._viagem_ativa or not self.segmentos:
            return False
        

        tempo_restante = tempo_decorrido_horas

        while tempo_restante > 0 and self.indice_segmento_atual < len(self.segmentos):
            segmento = self.segmentos[self.indice_segmento_atual]
            distancia_segmento = segmento['distancia']
            tempo_segmento = segmento['tempo_horas']

            distancia_restante_segmento = distancia_segmento - self.distancia_no_segmento
            tempo_para_concluir_segmento = (distancia_restante_segmento / distancia_segmento) * tempo_segmento

            if tempo_restante >= tempo_para_concluir_segmento:
                self.distancia_percorrida += distancia_restante_segmento
                self.distancia_no_segmento = 0.0
                self.indice_segmento_atual += 1
                tempo_restante -= tempo_para_concluir_segmento
            else:
                velocidade_efetiva = distancia_segmento / tempo_segmento if tempo_segmento > 0 else 0
                distancia_avancada = velocidade_efetiva * tempo_restante
                self.distancia_no_segmento += distancia_avancada
                self.distancia_percorrida += distancia_avancada
                tempo_restante = 0

        if self.indice_segmento_atual >= len(self.segmentos):
            # marcar internamente como concluída
            self._viagem_ativa = False
            return True

        return False

    def concluir(self):
        """Marcar viagem como concluída / limpar dados."""
    # marcar internamente como concluída e limpar dados
        self._viagem_ativa = False
        self.rota = []
        self.rota_ate_cliente = []
        self.rota_pedido = []
        self.distancia_total = 0.0
        self.distancia_ate_cliente = 0.0
        self.distancia_pedido = 0.0
        self.distancia_percorrida = 0.0
        self.tempo_inicio = None
        self.segmentos = []
        self.indice_segmento_atual = 0
        self.distancia_no_segmento = 0.0

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
