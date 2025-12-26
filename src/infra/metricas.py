"""
Sistema de recolha e análise de métricas da simulação.
"""
from typing import List, Dict
from datetime import datetime
import csv
import os

# TODO: rever e expandir com mais métricas conforme necessário
#TODO rever alguns calculos

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
        self.custo_penalizacoes: float = 0.0  # em euros
        self.emissoes_totais: float = 0.0  # em kg CO2
        self.tempo_ocupacao_total: float = 0.0  # em minutos
        self.tempo_disponivel_total: float = 0.0  # em minutos

        # Métricas de recálculo de rotas
        self.recalculos_totais: int = 0  # Total de rotas recalculadas
        self.tempo_ganho_recalculo: float = 0.0  # Tempo economizado (minutos)
        self.tempo_perdido_recalculo: float = 0.0  # Tempo perdido (minutos)
        self.eventos_recalculo: int = 0  # Número de eventos que causaram recálculo
        self.viagens_afetadas_total: int = 0  # Total de viagens afetadas
        self.recalculos_por_transito: int = 0  # Recálculos devido a trânsito
        self.recalculos_por_outros: int = 0  # Recálculos por outros motivos
        
        # Métricas de recarga/abastecimento
        self.recargas_totais: int = 0  # Total de recargas realizadas
        self.tempo_recarga_total: float = 0.0  # Tempo total em recarga (minutos)
        self.autonomia_recarregada_total: float = 0.0  # Autonomia total recarregada (km)
        self.recargas_por_veiculo: Dict[int, int] = {}  # Contagem de recargas por veículo
        self.veiculos_sem_autonomia: int = 0  # Veículos que ficaram sem autonomia
        
        # Métricas de alocação com recarga
        self.pedidos_rejeitados_sem_recarga: int = 0  # Pedidos rejeitados por falta de autonomia sem plano viável
        self.veiculos_alocados_com_recarga_planejada: int = 0  # Veículos alocados que precisarão recarregar

        # Histórico detalhado
        self.historico_pedidos: List[Dict] = []
        self.historico_veiculos: List[Dict] = []
        self.historico_recalculos: List[Dict] = []  # Histórico de recálculos
        self.historico_recargas: List[Dict] = []  # Histórico de recargas

    def registar_pedido_atendido(self, pedido_id: int, veiculo_id: int,
                                 tempo_resposta: float, distancia: float,
                                 custo: float, emissoes: float, plano_recarga=None):
        """Regista um pedido que foi atendido com sucesso.
        
        Args:
            pedido_id: ID do pedido
            veiculo_id: ID do veículo alocado
            tempo_resposta: Tempo de resposta em minutos
            distancia: Distância percorrida em km
            custo: Custo em euros
            emissoes: Emissões em kg CO2
            plano_recarga: PlanoRecarga se veículo necessitará recarga (opcional)
        """
        self.pedidos_atendidos += 1
        self.tempo_resposta_total += tempo_resposta
        self.distancia_total += distancia
        self.custo_total += custo
        self.emissoes_totais += emissoes
        
        # Registar se foi alocado com plano de recarga
        if plano_recarga and plano_recarga.viavel:
            self.veiculos_alocados_com_recarga_planejada += 1

        historico_entry = {
            'pedido_id': pedido_id,
            'veiculo_id': veiculo_id,
            'tempo_resposta': tempo_resposta,
            'distancia': distancia,
            'custo': custo,
            'emissoes': emissoes,
            'timestamp': datetime.now()
        }
        
        # Adicionar informação do plano de recarga se existir
        if plano_recarga and plano_recarga.viavel:
            historico_entry['plano_recarga'] = {
                'posto': plano_recarga.posto,
                'distancia_km': plano_recarga.distancia_km,
                'tempo_recarga_min': plano_recarga.tempo_recarga_min,
                'custo_extra': plano_recarga.custo_extra_estimado,
                'desvio_km': plano_recarga.desvio_rota_km
            }
        
        self.historico_pedidos.append(historico_entry)

    def registar_pedido_rejeitado(self, pedido_id: int, motivo: str, penalidade: float = 0.0):
        """Regista um pedido que não pôde ser atendido e aplica penalidade opcional.

        Args:
            pedido_id: ID do pedido
            motivo: Motivo da rejeição
            penalidade: Valor a acrescentar ao custo total como penalização
        """
        self.pedidos_rejeitados += 1
        # Aplicar penalidade ao custo total e ao contador de penalizações
        if penalidade and penalidade > 0.0:
            self.custo_total += penalidade
            self.custo_penalizacoes += penalidade

        self.historico_pedidos.append({
            'pedido_id': pedido_id,
            'rejeitado': True,
            'motivo': motivo,
            'penalidade': penalidade,
            'timestamp': datetime.now()
        })

    # podemos mais tarde meter estatisticas para cada carro por isso é que recebe o veiculo id
    def registar_tempo_ocupacao(self, veiculo_id: int, minutos: float):
        """Regista tempo em que um veículo esteve ocupado."""
        self.tempo_ocupacao_total += minutos

    def registar_tempo_disponivel(self, veiculo_id: int, minutos: float):
        """Regista tempo em que um veículo esteve disponível."""
        self.tempo_disponivel_total += minutos

    def registar_recalculo_rota(self, pedido_id: int, veiculo_id: int, 
                                diferenca_tempo: float, motivo: str = "transito",
                                distancia_anterior: float = 0.0, 
                                distancia_nova: float = 0.0):
        """Regista um recálculo de rota.
        
        Args:
            pedido_id: ID do pedido/viagem recalculado
            veiculo_id: ID do veículo
            diferenca_tempo: Diferença de tempo em minutos (positivo = mais demorado, negativo = mais rápido)
            motivo: Motivo do recálculo ('transito', 'outro')
            distancia_anterior: Distância da rota anterior em km
            distancia_nova: Distância da nova rota em km
        """
        self.recalculos_totais += 1
        
        if diferenca_tempo > 0:
            self.tempo_perdido_recalculo += diferenca_tempo
        else:
            self.tempo_ganho_recalculo += abs(diferenca_tempo)
        
        if motivo == "transito":
            self.recalculos_por_transito += 1
        else:
            self.recalculos_por_outros += 1
        
        self.historico_recalculos.append({
            'pedido_id': pedido_id,
            'veiculo_id': veiculo_id,
            'diferenca_tempo_min': diferenca_tempo,
            'motivo': motivo,
            'distancia_anterior_km': distancia_anterior,
            'distancia_nova_km': distancia_nova,
            'diferenca_distancia_km': distancia_nova - distancia_anterior,
            'timestamp': datetime.now()
        })

    def registar_evento_recalculo(self, num_viagens_afetadas: int):
        """Regista um evento que causou recálculo de rotas.
        
        Args:
            num_viagens_afetadas: Número de viagens afetadas pelo evento
        """
        self.eventos_recalculo += 1
        self.viagens_afetadas_total += num_viagens_afetadas
    
    def registar_recarga(self, veiculo_id: int, tempo_recarga: float, 
                        autonomia_recarregada: float, localizacao: str = None):
        """Regista uma recarga/abastecimento de veículo.
        
        Args:
            veiculo_id: ID do veículo recarregado
            tempo_recarga: Tempo gasto em recarga (minutos)
            autonomia_recarregada: Autonomia recarregada (km)
            localizacao: Localização onde ocorreu a recarga
        """
        self.recargas_totais += 1
        self.tempo_recarga_total += tempo_recarga
        self.autonomia_recarregada_total += autonomia_recarregada
        
        # Incrementar contador por veículo
        if veiculo_id not in self.recargas_por_veiculo:
            self.recargas_por_veiculo[veiculo_id] = 0
        self.recargas_por_veiculo[veiculo_id] += 1
        
        self.historico_recargas.append({
            'veiculo_id': veiculo_id,
            'tempo_recarga_min': tempo_recarga,
            'autonomia_recarregada_km': autonomia_recarregada,
            'localizacao': localizacao,
            'timestamp': datetime.now()
        })
    
    def registar_veiculo_sem_autonomia(self, veiculo_id: int):
        """Regista um veículo que ficou sem autonomia.
        
        Args:
            veiculo_id: ID do veículo sem autonomia
        """
        self.veiculos_sem_autonomia += 1

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

    def tempo_medio_por_recalculo(self) -> float:
        """Calcula o impacto médio de tempo por recálculo."""
        if self.recalculos_totais == 0:
            return 0.0
        return (self.tempo_perdido_recalculo - self.tempo_ganho_recalculo) / self.recalculos_totais

    def saldo_tempo_recalculo(self) -> float:
        """Calcula o saldo total de tempo (ganho - perdido) em minutos."""
        return self.tempo_ganho_recalculo - self.tempo_perdido_recalculo

    def taxa_recalculo_por_pedido(self) -> float:
        """Calcula a taxa de recálculos por pedido atendido."""
        if self.pedidos_atendidos == 0:
            return 0.0
        return self.recalculos_totais / self.pedidos_atendidos

    def media_viagens_afetadas_por_evento(self) -> float:
        """Calcula a média de viagens afetadas por evento de recálculo."""
        if self.eventos_recalculo == 0:
            return 0.0
        return self.viagens_afetadas_total / self.eventos_recalculo
    
    def tempo_medio_recarga(self) -> float:
        """Calcula o tempo médio de recarga por veículo."""
        if self.recargas_totais == 0:
            return 0.0
        return self.tempo_recarga_total / self.recargas_totais
    
    def recargas_por_pedido(self) -> float:
        """Calcula a taxa de recargas por pedido atendido."""
        if self.pedidos_atendidos == 0:
            return 0.0
        return self.recargas_totais / self.pedidos_atendidos
    
    def percentual_tempo_em_recarga(self) -> float:
        """Calcula o percentual de tempo gasto em recarga."""
        tempo_total = self.tempo_ocupacao_total + self.tempo_disponivel_total + self.tempo_recarga_total
        if tempo_total == 0:
            return 0.0
        return (self.tempo_recarga_total / tempo_total) * 100

    # -------------------- Relatórios e Exportação --------------------

    # NOTA: Aqui se calhar depois fazer de outra maneira para juntar com o display
    #TODO: juntar com o logger de alguma forma?

    def gerar_relatorio(self) -> str:
        """Gera um relatório textual com todas as métricas."""
        relatorio = []
        relatorio.append("=" * 60)
        relatorio.append("RELATÓRIO DE MÉTRICAS DA SIMULAÇÃO")
        relatorio.append("=" * 60)
        relatorio.append("")
        relatorio.append(f"Pedidos atendidos: {self.pedidos_atendidos}")
        relatorio.append(f"Pedidos rejeitados: {self.pedidos_rejeitados}")
        relatorio.append(f"Penalizações por rejeição: €{self.custo_penalizacoes:.2f}")
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
        relatorio.append("")
        relatorio.append("--- MÉTRICAS DE RECÁLCULO DE ROTAS ---")
        relatorio.append(f"Total de recálculos: {self.recalculos_totais}")
        relatorio.append(f"Eventos que causaram recálculo: {self.eventos_recalculo}")
        relatorio.append(f"Viagens afetadas no total: {self.viagens_afetadas_total}")
        relatorio.append(f"Média de viagens/evento: {self.media_viagens_afetadas_por_evento():.2f}")
        relatorio.append(f"Recálculos por trânsito: {self.recalculos_por_transito}")
        relatorio.append(f"Recálculos por outros motivos: {self.recalculos_por_outros}")
        relatorio.append("")
        relatorio.append(f"Tempo economizado: {self.tempo_ganho_recalculo:.2f} min")
        relatorio.append(f"Tempo perdido: {self.tempo_perdido_recalculo:.2f} min")
        saldo = self.saldo_tempo_recalculo()
        sinal = "+" if saldo >= 0 else ""
        relatorio.append(f"Saldo líquido: {sinal}{saldo:.2f} min")
        relatorio.append(f"Impacto médio/recálculo: {self.tempo_medio_por_recalculo():+.2f} min")
        relatorio.append(f"Taxa recálculos/pedido: {self.taxa_recalculo_por_pedido():.2f}")
        relatorio.append("")
        relatorio.append("--- MÉTRICAS DE RECARGA/ABASTECIMENTO ---")
        relatorio.append(f"Total de recargas: {self.recargas_totais}")
        relatorio.append(f"Tempo total em recarga: {self.tempo_recarga_total:.2f} min")
        relatorio.append(f"Tempo médio por recarga: {self.tempo_medio_recarga():.2f} min")
        relatorio.append(f"Autonomia total recarregada: {self.autonomia_recarregada_total:.2f} km")
        relatorio.append(f"Recargas por pedido: {self.recargas_por_pedido():.2f}")
        relatorio.append(f"% tempo em recarga: {self.percentual_tempo_em_recarga():.2f}%")
        if self.recargas_por_veiculo:
            relatorio.append(f"Veículos que recarregaram: {len(self.recargas_por_veiculo)}")
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
                'penalizacoes_total': self.custo_penalizacoes,
                'custo_medio_por_km': self.custo_medio_por_km(),
                'emissoes_totais': self.emissoes_totais,
                'emissoes_medias_por_km': self.emissoes_medias_por_km(),
                'taxa_ocupacao': self.taxa_ocupacao()
            },
            'recalculos': {
                'total_recalculos': self.recalculos_totais,
                'eventos_recalculo': self.eventos_recalculo,
                'viagens_afetadas': self.viagens_afetadas_total,
                'media_viagens_por_evento': self.media_viagens_afetadas_por_evento(),
                'recalculos_transito': self.recalculos_por_transito,
                'recalculos_outros': self.recalculos_por_outros,
                'tempo_ganho_min': self.tempo_ganho_recalculo,
                'tempo_perdido_min': self.tempo_perdido_recalculo,
                'saldo_tempo_min': self.saldo_tempo_recalculo(),
                'impacto_medio_min': self.tempo_medio_por_recalculo(),
                'taxa_recalculos_pedido': self.taxa_recalculo_por_pedido()
            },
            'recargas': {
                'total_recargas': self.recargas_totais,
                'tempo_total_min': self.tempo_recarga_total,
                'tempo_medio_min': self.tempo_medio_recarga(),
                'autonomia_total_km': self.autonomia_recarregada_total,
                'recargas_por_pedido': self.recargas_por_pedido(),
                'percentual_tempo_recarga': self.percentual_tempo_em_recarga(),
                'veiculos_recarregados': len(self.recargas_por_veiculo),
                'recargas_por_veiculo': self.recargas_por_veiculo
            },
            'historico_pedidos': self.historico_pedidos,
            'historico_veiculos': self.historico_veiculos,
            'historico_recalculos': self.historico_recalculos,
            'historico_recargas': self.historico_recargas
        }

    def exportar_csv(self, ficheiro_csv: str = None, config: Dict = None) -> str:
        """
        Exporta as métricas para CSV, fazendo append se o ficheiro já existir.

        Args:
            ficheiro_csv: Caminho para o ficheiro CSV de estatísticas. Se None,
                usa o caminho por omissão em 'runs/stats/statistics.csv'.
            config: Dicionário com configuração da run (algoritmo, velocidade, etc.)

        Returns:
            O caminho absoluto para o ficheiro CSV utilizado.
        """
        # Determinar ficheiro por omissão se não for fornecido
        if ficheiro_csv is None:
            project_root = os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))
            ficheiro_csv = os.path.join(project_root, 'runs', 'stats', 'statistics.csv')

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
            # Políticas
            'recarga_policy': config.get('recarga_policy', ''),
            'recarga_permitida': config.get('recarga_permitida', False),
            'ridesharing_policy': config.get('ridesharing_policy', ''),
            'ridesharing_permitida': config.get('ridesharing_permitida', False),
            'pedidos_atendidos': self.pedidos_atendidos,
            'pedidos_rejeitados': self.pedidos_rejeitados,
            'taxa_atendimento': round(self.taxa_atendimento(), 2),
            'tempo_resposta_medio': round(self.tempo_resposta_medio(), 2),
            'distancia_total': round(self.distancia_total, 2),
            'custo_total': round(self.custo_total, 2),
            'penalizacoes_total': round(self.custo_penalizacoes, 2),
            'custo_medio_por_km': round(self.custo_medio_por_km(), 3),
            'emissoes_totais': round(self.emissoes_totais, 2),
            'emissoes_medias_por_km': round(self.emissoes_medias_por_km(), 3),
            'taxa_ocupacao': round(self.taxa_ocupacao(), 2),
            'recalculos_totais': self.recalculos_totais,
            'eventos_recalculo': self.eventos_recalculo,
            'viagens_afetadas': self.viagens_afetadas_total,
            'recalculos_transito': self.recalculos_por_transito,
            'tempo_ganho_min': round(self.tempo_ganho_recalculo, 2),
            'tempo_perdido_min': round(self.tempo_perdido_recalculo, 2),
            'saldo_tempo_min': round(self.saldo_tempo_recalculo(), 2),
            'impacto_medio_recalculo_min': round(self.tempo_medio_por_recalculo(), 2),
            'taxa_recalculos_pedido': round(self.taxa_recalculo_por_pedido(), 2),
            'recargas_totais': self.recargas_totais,
            'tempo_recarga_total_min': round(self.tempo_recarga_total, 2),
            'tempo_medio_recarga_min': round(self.tempo_medio_recarga(), 2),
            'autonomia_recarregada_km': round(self.autonomia_recarregada_total, 2),
            'recargas_por_pedido': round(self.recargas_por_pedido(), 2),
            'percentual_tempo_recarga': round(self.percentual_tempo_em_recarga(), 2),
            'veiculos_recarregados': len(self.recargas_por_veiculo),
            'pedidos_rejeitados_sem_recarga': self.pedidos_rejeitados_sem_recarga,
            'veiculos_alocados_com_recarga_planejada': self.veiculos_alocados_com_recarga_planejada,
            'veiculos_sem_autonomia': self.veiculos_sem_autonomia
        }

        # Escrever no CSV
        with open(ficheiro_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=dados.keys())

            # Escrever cabeçalho se ficheiro novo
            if not ficheiro_existe:
                writer.writeheader()

            writer.writerow(dados)

        return os.path.abspath(ficheiro_csv)
