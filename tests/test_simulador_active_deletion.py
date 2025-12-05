import pytest

from infra.simulador import Simulador


class FakeVeiculo:
    def __init__(self, vid, concluded_counts):
        # concluded_counts: list of integers indicating how many trips conclude per call
        self._id = vid
        self._concluded_counts = list(concluded_counts)
        self._active = True
        self.viagem_recarga = None  # Simular atributo para compatibilidade

    @property
    def id_veiculo(self):
        return self._id

    @property
    def viagem_ativa(self):
        return self._active

    def atualizar_progresso_viagem(self, tempo_decorrido_horas):
        # Return a list of fake concluded trips based on the next count
        if not self._concluded_counts:
            return []
        count = self._concluded_counts.pop(0)
        concluidas = [object() for _ in range(count)]
        # If count > 0, simulate that after processing, there are no more active trips
        # The Simulador will call _concluir_viagem, which should mark vehicle inactive;
        # here we simulate end-of-step: active only if further trips remain
        # We'll flip to inactive when we reach a special marker: -1
        return concluidas

    # Simulate called by simulador._concluir_viagem via veiculo.concluir_viagem(viagem)
    def concluir_viagem(self, viagem):
        # If no more concluded trips scheduled, mark inactive
        if not self._concluded_counts or self._concluded_counts[0] == 0:
            self._active = False


def test_no_deletion_when_still_active():
    s = Simulador(alocador=None, navegador=None, display=None)
    v = FakeVeiculo('V001', concluded_counts=[0])
    s.viagens_ativas = {'V001': v}

    s._atualizar_viagens_ativas(tempo_passo_horas=1.0)

    assert 'V001' in s.viagens_ativas, "Vehicle should remain active when no trips concluded"


def test_deletion_when_all_concluded_single_pass():
    s = Simulador(alocador=None, navegador=None, display=None)
    v = FakeVeiculo('V002', concluded_counts=[1])
    s.viagens_ativas = {'V002': v}

    # Monkeypatch _concluir_viagem to call vehicle.concluir_viagem
    def _concluir_viagem(veiculo, viagem):
        veiculo.concluir_viagem(viagem)
    s._concluir_viagem = _concluir_viagem

    s._atualizar_viagens_ativas(tempo_passo_horas=1.0)

    assert 'V002' not in s.viagens_ativas, "Vehicle should be removed when all trips concluded"


def test_multiple_conclusions_same_step_safe_deletion():
    s = Simulador(alocador=None, navegador=None, display=None)
    v = FakeVeiculo('V005', concluded_counts=[2])
    s.viagens_ativas = {'V005': v}

    # Monkeypatch _concluir_viagem to call vehicle.concluir_viagem for each concluded trip
    def _concluir_viagem(veiculo, viagem):
        veiculo.concluir_viagem(viagem)
    s._concluir_viagem = _concluir_viagem

    # Ensure no KeyError raised when multiple concluded trips processed
    s._atualizar_viagens_ativas(tempo_passo_horas=1.0)

    assert 'V005' not in s.viagens_ativas, "Vehicle should be removed once even if multiple trips conclude"
