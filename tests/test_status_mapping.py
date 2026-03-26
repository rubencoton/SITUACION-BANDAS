from __future__ import annotations

from src.data_model import normalize_phase, normalize_status, status_to_score


def test_status_mapping_basic():
    assert normalize_status("CRÍTICO") == "CRITICO"
    assert normalize_status("en proceso") == "EN PROCESO"
    assert normalize_status("OPTIMO") == "OPTIMO"
    assert status_to_score("CRITICO") == 0
    assert status_to_score("EN PROCESO") == 1
    assert status_to_score("OPTIMO") == 2


def test_status_mapping_unknown():
    assert normalize_status("BLOQUEADO") == "DESCONOCIDO"
    assert status_to_score("BLOQUEADO") == -1


def test_phase_normalization():
    assert normalize_phase("1. IMAGEN") == "IMAGEN"
    assert normalize_phase("3. PRODUCCIÓN") == "PRODUCCION"
