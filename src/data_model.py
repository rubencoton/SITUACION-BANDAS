from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
import unicodedata

import pandas as pd


STATUS_SCORE_MAP = {
    "CRITICO": 0,
    "EN PROCESO": 1,
    "OPTIMO": 2,
}

PHASE_ORDER = [
    "IMAGEN",
    "REDES SOCIALES",
    "PRODUCCION",
    "LANZAMIENTO",
    "BOOKING",
]


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def normalize_status(value: str | None) -> str:
    if not value:
        return "DESCONOCIDO"
    normalized = strip_accents(value).upper().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    if normalized in STATUS_SCORE_MAP:
        return normalized
    return "DESCONOCIDO"


def status_to_score(value: str | None) -> int:
    normalized = normalize_status(value)
    return STATUS_SCORE_MAP.get(normalized, -1)


def normalize_phase(value: str | None) -> str:
    if not value:
        return "DESCONOCIDA"
    normalized = strip_accents(value).upper().strip()
    normalized = re.sub(r"^\d+\.\s*", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


@dataclass(slots=True)
class BandRecord:
    banda: str
    correo_principal: str
    asunto: str
    mensaje_personalizado: str
    ultimo_envio: str
    observaciones: str
    nombre_hoja: str
    fecha_extraccion: str


@dataclass(slots=True)
class PhaseStateRecord:
    banda: str
    fase: str
    estado: str
    score: int
    fecha_extraccion: str
    nombre_hoja: str


@dataclass(slots=True)
class NormalizedDataset:
    bands_df: pd.DataFrame
    phases_df: pd.DataFrame
    extraction_ts: datetime
    sheet_id: str
    source_mode: str
