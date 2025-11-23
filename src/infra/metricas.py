"""
Sistema de recolha e análise de métricas da simulação.
"""
from typing import List, Dict
from datetime import datetime
import csv
import os

# TODO: rever e expandir com mais métricas conforme necessário


class Metricas:
    """
    Classe responsável por recolher e calcular métricas de desempenho
    da simulação.
    """

    # estão aqui as métricas globais que dizia no enunciado, mas depois podemos meter mais

    def __init__(self):
        self.pedidos_atendidos: int = 0
        self.pedidos_rejeitados: int = 0
        self.tempo_resposta_total: float = 0.0  # em minutos
        self.distancia_total: float = 0.0  # em km
        self.custo_total: float = 0.0  # em euros
        self.emissoes_totais: float = 0.0  # em kg CO2
        self.tempo_ocupacao_total: float = 0.0  # em minutos
        self.tempo_disponivel_total: float = 0.0  # em minutos

        # Histórico detalhado
        self.historico_pedidos: List[Dict] = []
        self.historico_veiculos: List[Dict] = []

    def registar_pedido_atendido(self, pedido_id: int, veiculo_id: int,
                                 tempo_resposta: float, distancia: float,
                                 custo: float, emissoes: float):
        """Regista um pedido que foi atendido com sucesso."""
        self.pedidos_atendidos += 1
        self.tempo_resposta_total += tempo_resposta
        self.distancia_total += distancia
        self.custo_total += custo
        self.emissoes_totais += emissoes

        self.historico_pedidos.append({
            'pedido_id': pedido_id,
            'veiculo_id': veiculo_id,
            'tempo_resposta': tempo_resposta,
            'distancia': distancia,
            'custo': custo,
            'emissoes': emissoes,
            'timestamp': datetime.now()
        })

    def registar_pedido_rejeitado(self, pedido_id: int, motivo: str):
        """Regista um pedido que não pôde ser atendido."""
        self.pedidos_rejeitados += 1
        self.historico_pedidos.append({
            'pedido_id': pedido_id,
            'rejeitado': True,
            'motivo': motivo,
            'timestamp': datetime.now()
        })

    # podemos mais tarde meter estatisticas para cada carro por isso é que recebe o veiculo id
    def registar_tempo_ocupacao(self, veiculo_id: int, minutos: float):
        """Regista tempo em que um veículo esteve ocupado."""
        self.tempo_ocupacao_total += minutos

    def registar_tempo_disponivel(self, veiculo_id: int, minutos: float):
        """Regista tempo em que um veículo esteve disponível."""
        self.tempo_disponivel_total += minutos

    # -------------------- Cálculos de métricas --------------------

    def tempo_resposta_medio(self) -> float:
        """Calcula o tempo médio de resposta aos pedidos."""
        if self.pedidos_atendidos == 0:
            return 0.0
        return self.tempo_resposta_total / self.pedidos_atendidos

    def taxa_atendimento(self) -> float:
        """Calcula a percentagem de pedidos atendidos."""
        total = self.pedidos_atendidos + self.pedidos_rejeitados
        if total == 0:
            return 0.0
        return (self.pedidos_atendidos / total) * 100

    def custo_medio_por_km(self) -> float:
        """Calcula o custo médio por quilómetro."""
        if self.distancia_total == 0:
            return 0.0
        return self.custo_total / self.distancia_total

    def emissoes_medias_por_km(self) -> float:
        """Calcula as emissões médias por quilómetro."""
        if self.distancia_total == 0:
            return 0.0
        return self.emissoes_totais / self.distancia_total

    def taxa_ocupacao(self) -> float:
        """Calcula a taxa de ocupação da frota (%)."""
        tempo_total = self.tempo_ocupacao_total + self.tempo_disponivel_total
        if tempo_total == 0:
            return 0.0
        return (self.tempo_ocupacao_total / tempo_total) * 100

    # -------------------- Relatórios e Exportação --------------------

    # NOTA: Aqui se calhar depois fazer de outra maneira para juntar com o display

    def gerar_relatorio(self) -> str:
        """Gera um relatório textual com todas as métricas."""
        relatorio = []
        relatorio.append("=" * 60)
        relatorio.append("RELATÓRIO DE MÉTRICAS DA SIMULAÇÃO")
        relatorio.append("=" * 60)
        relatorio.append("")
        relatorio.append(f"Pedidos atendidos: {self.pedidos_atendidos}")
        relatorio.append(f"Pedidos rejeitados: {self.pedidos_rejeitados}")
        relatorio.append(
            f"Taxa de atendimento: {self.taxa_atendimento():.2f}%")
        relatorio.append("")
        relatorio.append(
            f"Tempo médio de resposta: {self.tempo_resposta_medio():.2f} min")
        relatorio.append(
            f"Distância total percorrida: {self.distancia_total:.2f} km")
        relatorio.append(f"Custo total: €{self.custo_total:.2f}")
        relatorio.append(
            f"Custo médio por km: €{self.custo_medio_por_km():.3f}")
        relatorio.append("")
        relatorio.append(f"Emissões totais: {self.emissoes_totais:.2f} kg CO₂")
        relatorio.append(
            f"Emissões médias por km: {self.emissoes_medias_por_km():.3f} kg CO₂/km")
        relatorio.append("")
        relatorio.append(
            f"Taxa de ocupação da frota: {self.taxa_ocupacao():.2f}%")
        relatorio.append("=" * 60)

        return "\n".join(relatorio)

    def exportar_json(self) -> Dict:
        """Exporta as métricas em formato JSON."""
        return {
            'resumo': {
                'pedidos_atendidos': self.pedidos_atendidos,
                'pedidos_rejeitados': self.pedidos_rejeitados,
                'taxa_atendimento': self.taxa_atendimento(),
                'tempo_resposta_medio': self.tempo_resposta_medio(),
                'distancia_total': self.distancia_total,
                'custo_total': self.custo_total,
                'custo_medio_por_km': self.custo_medio_por_km(),
                'emissoes_totais': self.emissoes_totais,
                'emissoes_medias_por_km': self.emissoes_medias_por_km(),
                'taxa_ocupacao': self.taxa_ocupacao()
            },
            'historico_pedidos': self.historico_pedidos,
            'historico_veiculos': self.historico_veiculos
        }

    def exportar_csv(self, ficheiro_csv: str, config: Dict):
        """
        Exporta as métricas para CSV, fazendo append se o ficheiro já existir.

        Args:
            ficheiro_csv: Caminho para o ficheiro CSV de estatísticas
            config: Dicionário com configuração da run (algoritmo, velocidade, etc.)
        """
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(ficheiro_csv), exist_ok=True)

        # Verificar se ficheiro existe para decidir se escreve cabeçalho
        ficheiro_existe = os.path.exists(ficheiro_csv)

        # Preparar dados da linha
        dados = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'navegador': config.get('navegador', ''),
            'alocador': config.get('alocador', ''),
            'velocidade': config.get('velocidade', 1.0),
            'pedidos_atendidos': self.pedidos_atendidos,
            'pedidos_rejeitados': self.pedidos_rejeitados,
            'taxa_atendimento': round(self.taxa_atendimento(), 2),
            'tempo_resposta_medio': round(self.tempo_resposta_medio(), 2),
            'distancia_total': round(self.distancia_total, 2),
            'custo_total': round(self.custo_total, 2),
            'custo_medio_por_km': round(self.custo_medio_por_km(), 3),
            'emissoes_totais': round(self.emissoes_totais, 2),
            'emissoes_medias_por_km': round(self.emissoes_medias_por_km(), 3),
            'taxa_ocupacao': round(self.taxa_ocupacao(), 2)
        }

        # Escrever no CSV
        with open(ficheiro_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=dados.keys())

            # Escrever cabeçalho se ficheiro novo
            if not ficheiro_existe:
                writer.writeheader()

            writer.writerow(dados)
