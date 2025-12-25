import pytest

from infra.simulador import Simulador


class FakeViagem:
    """Viagem fake para testes."""
    def __init__(self, pedido_id):
        self.pedido_id = pedido_id


class FakeVeiculo:
    def __init__(self, vid, concluded_counts):
        # concluded_counts: list of integers indicating how many trips conclude per call
        self._id = vid
        self._concluded_counts = list(concluded_counts)
        self._active = True
        self.viagem_recarga = None  # Simular atributo para compatibilidade
        self.localizacao_atual = "FakeLocation"  # Simular localização

    @property
    def id_veiculo(self):
        return self._id

    @property
    def viagem_ativa(self):
        return self._active

    def atualizar_progresso_viagem(self, tempo_decorrido_horas):
        # Return a tuple (list of fake concluded trips, chegou_posto) based on the next count
        if not self._concluded_counts:
            return [], False
        count = self._concluded_counts.pop(0)
        # Criar viagens fake com pedido_id
        concluidas = [FakeViagem(pedido_id=i) for i in range(count)]
        # If count > 0, simulate that after processing, there are no more active trips
        if count > 0 and not self._concluded_counts:
            self._active = False
        return concluidas, False  # Retornar tupla (viagens_concluidas, chegou_posto)

    def concluir_viagem(self, viagem):
        # If no more concluded trips scheduled, mark inactive
        if not self._concluded_counts or self._concluded_counts[0] == 0:
            self._active = False


class FakeAmbiente:
    """Ambiente fake para testes."""
    def concluir_pedido(self, pedido_id, viagem):
        pass
    
    def atualizar_viagens_ativas(self, viagens_ativas, tempo_passo_horas):
        # Simular comportamento do ambiente
        viagens_concluidas = []
        veiculos_chegaram_posto = []
        
        for veiculo_id, veiculo in list(viagens_ativas.items()):
            concluidas, chegou_posto = veiculo.atualizar_progresso_viagem(tempo_passo_horas)
            for viagem in concluidas:
                viagens_concluidas.append((veiculo_id, veiculo, viagem))
        
        return viagens_concluidas, veiculos_chegaram_posto


def test_no_deletion_when_still_active():
    s = Simulador(alocador=None, navegador=None, display=None)
    v = FakeVeiculo('V001', concluded_counts=[0])
    s.gestor_viagens.viagens_ativas = {'V001': v}
    
    # Substituir ambiente por fake
    s.ambiente = FakeAmbiente()
    s.gestor_viagens.ambiente = FakeAmbiente()

    # Usar gestor de viagens diretamente
    s.gestor_viagens.atualizar_viagens_ativas(
        1.0, s.tempo_simulacao
    )

    assert 'V001' in s.gestor_viagens.viagens_ativas, "Vehicle should remain active when no trips concluded"


def test_deletion_when_all_concluded_single_pass():
    s = Simulador(alocador=None, navegador=None, display=None)
    v = FakeVeiculo('V002', concluded_counts=[1])
    s.gestor_viagens.viagens_ativas = {'V002': v}
    
    # Substituir ambiente por fake
    s.ambiente = FakeAmbiente()
    s.gestor_viagens.ambiente = FakeAmbiente()

    # Usar gestor de viagens diretamente
    s.gestor_viagens.atualizar_viagens_ativas(
        1.0, s.tempo_simulacao
    )

    assert 'V002' not in s.gestor_viagens.viagens_ativas, "Vehicle should be removed when all trips concluded"


def test_multiple_conclusions_same_step_safe_deletion():
    s = Simulador(alocador=None, navegador=None, display=None)
    v = FakeVeiculo('V005', concluded_counts=[2])
    s.gestor_viagens.viagens_ativas = {'V005': v}
    
    # Substituir ambiente por fake
    s.ambiente = FakeAmbiente()
    s.gestor_viagens.ambiente = FakeAmbiente()

    # Ensure no KeyError raised when multiple concluded trips processed
    s.gestor_viagens.atualizar_viagens_ativas(
        1.0, s.tempo_simulacao
    )

    assert 'V005' not in s.gestor_viagens.viagens_ativas, (
        "Vehicle should be removed safely even when multiple trips conclude in same step"
    )
