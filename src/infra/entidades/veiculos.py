from abc import ABC, abstractmethod
from enum import Enum

#NOTA: enum sus, depois vejam os estados melhor
class EstadoVeiculo(Enum):
    DISPONIVEL = 1
    EM_ANDAMENTO = 2
    INDISPONIVEL = 3 
    EM_REABASTECIMENTO = 4
    EM_MANUTENCAO = 5

class Veiculo(ABC):
    def __init__(self, id_veiculo: int, autonomia_maxima: int, autonomia_atual: int,
                 capacidade_passageiros: int, numero_passageiros: int, custo_operacional_km: float,
                 estado: EstadoVeiculo = EstadoVeiculo.DISPONIVEL, localizacao_atual = 0):
        # atributos protegidos (encapsulados) — aceder via propriedades
        self._id_veiculo = id_veiculo
        self._autonomia_maxima = autonomia_maxima
        self._autonomia_atual = autonomia_atual
        self._capacidade_passageiros = capacidade_passageiros
        self._numero_passageiros = numero_passageiros
        self._custo_operacional_km = custo_operacional_km
        self._estado = estado
        self._localizacao_atual = localizacao_atual  # ID ou nome do nó onde o veículo está
        
        #TODO: rever isto e ver se fazemos uma classe viagem
        # Informações da viagem em andamento
        self.viagem_ativa = False
        self.pedido_id = None
        self.rota = []
        self.distancia_total = 0.0
        self.distancia_percorrida = 0.0
        self.tempo_inicio = None
        self.segmentos = []
        self.indice_segmento_atual = 0
        self.distancia_no_segmento = 0.0

    @abstractmethod
    def reabastecer(self):
        """Método abstrato — implementado de forma diferente nos veículos a combustão e elétricos"""
        return

    @abstractmethod
    def tempoReabastecimento(self):
        return

    def adicionar_passageiros(self, numero: int):
        """Adiciona passageiros ao veículo, se houver capacidade."""
        if self._numero_passageiros + numero <= self._capacidade_passageiros:
            self._numero_passageiros += numero
            return True
        return False

    def reabastecer(self):
        self.autonomia_atual = self.autonomia_maxima
        self.estado = EstadoVeiculo.DISPONIVEL

    def atualizar_autonomia(self, km_percorridos: int):
        """Reduz a autonomia atual de acordo com a distância percorrida"""
        self.autonomia_atual = max(0, self.autonomia_atual - km_percorridos) # Evita autonomia negativa

    def __str__(self):
        return (f"{self.__class__.__name__} [{self.id_veiculo}] | "
                f"Autonomia: {self.autonomia_atual}/{self.autonomia_maxima} km | "
                f"Capacidade: {self.capacidade_passageiros} passageiros | "
                f"Custo/km: €{self.custo_operacional_km:.2f} | "
                f"Estado: {self.estado.value}")

    # -------------------- Propriedades (getters/setters) --------------------
    @property
    def id_veiculo(self) -> int:
        return self._id_veiculo

    @property
    def autonomia_maxima(self) -> int:
        return self._autonomia_maxima

    @property
    def autonomia_atual(self) -> int:
        return self._autonomia_atual
    
    @autonomia_atual.setter
    def autonomia_atual(self, value: int):
        self._autonomia_atual = max(0, value)

    @property
    def capacidade_passageiros(self) -> int:
        return self._capacidade_passageiros

    @property
    def custo_operacional_km(self) -> float:
        return self._custo_operacional_km

    @property
    def estado(self) -> EstadoVeiculo:
        return self._estado

    @estado.setter
    def estado(self, value: EstadoVeiculo):
        if not isinstance(value, EstadoVeiculo):
            raise ValueError("estado deve ser um EstadoVeiculo")
        self._estado = value

    @property
    def numero_passageiros(self) -> int:
        return self._numero_passageiros
    
    @property
    def localizacao_atual(self):
        """Retorna a localização atual (nome do nó ou ID)."""
        return self._localizacao_atual
    
    @localizacao_atual.setter
    def localizacao_atual(self, value):
        """Define a localização atual (pode ser nome do nó ou ID)."""
        self._localizacao_atual = value
    
    def iniciar_viagem(self, pedido_id: int, rota: list, distancia_total: float, tempo_inicio, grafo, velocidade_media: float = 50.0):
        """Inicia uma viagem no veículo."""
        from datetime import datetime
        
        self.viagem_ativa = True
        self.pedido_id = pedido_id
        self.rota = rota
        self.distancia_total = distancia_total
        self.distancia_percorrida = 0.0
        self.tempo_inicio = tempo_inicio
        self.indice_segmento_atual = 0
        self.distancia_no_segmento = 0.0
        
        # Pré-calcular informações dos segmentos
        self.segmentos = []
        for i in range(len(rota) - 1):
            origem = rota[i]
            destino = rota[i + 1]
            aresta = grafo.getEdge(origem, destino)
            
            if aresta:
                distancia = aresta.getQuilometro()
                velocidade = aresta.getVelocidadeMaxima()
                transito = aresta.getTransito()
                
                # Calcular tempo baseado na velocidade da aresta e trânsito
                tempo_base_horas = distancia / velocidade if velocidade > 0 else distancia / velocidade_media
                fator_transito = transito.value if transito.value is not None else 1.0
                tempo_horas = tempo_base_horas * fator_transito
                
                self.segmentos.append({
                    'origem': origem,
                    'destino': destino,
                    'distancia': distancia,
                    'velocidade': velocidade,
                    'tempo_horas': tempo_horas
                })
            else:
                # Fallback se não houver aresta
                distancia_fallback = 10.0
                self.segmentos.append({
                    'origem': origem,
                    'destino': destino,
                    'distancia': distancia_fallback,
                    'velocidade': velocidade_media,
                    'tempo_horas': distancia_fallback / velocidade_media
                })
    
    def atualizar_progresso_viagem(self, tempo_decorrido_horas: float) -> bool:
        """
        Atualiza o progresso da viagem baseado no tempo decorrido.
        Retorna True se a viagem foi concluída.
        """
        if not self.viagem_ativa or not self.segmentos:
            return False
        
        tempo_restante = tempo_decorrido_horas
        
        while tempo_restante > 0 and self.indice_segmento_atual < len(self.segmentos):
            segmento = self.segmentos[self.indice_segmento_atual]
            distancia_segmento = segmento['distancia']
            tempo_segmento = segmento['tempo_horas']
            
            # Calcular quanto falta percorrer neste segmento
            distancia_restante_segmento = distancia_segmento - self.distancia_no_segmento
            tempo_para_concluir_segmento = (distancia_restante_segmento / distancia_segmento) * tempo_segmento
            
            if tempo_restante >= tempo_para_concluir_segmento:
                # Concluir este segmento e avançar para o próximo
                self.distancia_percorrida += distancia_restante_segmento
                self.distancia_no_segmento = 0.0
                self.indice_segmento_atual += 1
                tempo_restante -= tempo_para_concluir_segmento
            else:
                # Avançar parcialmente neste segmento
                velocidade_efetiva = distancia_segmento / tempo_segmento if tempo_segmento > 0 else 0
                distancia_avancada = velocidade_efetiva * tempo_restante
                self.distancia_no_segmento += distancia_avancada
                self.distancia_percorrida += distancia_avancada
                tempo_restante = 0
        
        # Verificar se a viagem foi concluída
        if self.indice_segmento_atual >= len(self.segmentos):
            self.viagem_ativa = False
            return True
        
        return False
    
    def concluir_viagem(self):
        """Finaliza a viagem."""
        self.viagem_ativa = False
        self.pedido_id = None
        self.rota = []
        self.distancia_total = 0.0
        self.distancia_percorrida = 0.0
        self.tempo_inicio = None
        self.segmentos = []
        self.indice_segmento_atual = 0
        self.distancia_no_segmento = 0.0
    
    @property
    def progresso_percentual(self) -> float:
        """Retorna o progresso da viagem em percentual (0-100)."""
        if not self.viagem_ativa or self.distancia_total == 0:
            return 0.0
        return min(100.0, (self.distancia_percorrida / self.distancia_total) * 100.0)
    
    @property
    def destino(self) -> str:
        """Retorna o destino final da rota."""
        return self.rota[-1] if self.rota else None

# -------------------- Veículo a Combustão ---------------- #

class VeiculoCombustao(Veiculo):
    def __init__(self, id_veiculo, autonomia_maxima, autonomia_atual, capacidade_passageiros,
                 custo_operacional_km, numero_passageiros=0, localizacao_atual=0): #meter custo litro por kilometro se for preciso
        super().__init__(id_veiculo, autonomia_maxima, autonomia_atual, capacidade_passageiros,
                         numero_passageiros, custo_operacional_km, localizacao_atual=localizacao_atual)

    def tempoReabastecimento(self):
        return 5  # tempo fixo de reabastecimento em minutos, NOTA: pode ser ajustado conforme necessário


# -------------------- Veículo Elétrico ---------------- #

class VeiculoEletrico(Veiculo):
    def __init__(self, id_veiculo, autonomia_maxima, autonomia_atual, capacidade_passageiros,
                 custo_operacional_km, tempo_recarga_km: int, numero_passageiros=0, localizacao_atual=0):
        super().__init__(id_veiculo, autonomia_maxima, autonomia_atual, capacidade_passageiros,
                         numero_passageiros, custo_operacional_km, localizacao_atual=localizacao_atual)
        self.tempo_recarga_km = tempo_recarga_km  # tempo médio para carga de um km


    def tempoReabastecimento(self):
        tempo = self.tempo_recarga_km * (self.autonomia_maxima - self.autonomia_atual)
        return tempo


# -------------------- Propriedades (getters/setters) --------------------
@property
def tempo_recarga_km(self) -> int:
    return self._tempo_recarga_km




    

