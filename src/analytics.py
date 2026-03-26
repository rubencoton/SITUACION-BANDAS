from __future__ import annotations

from dataclasses import dataclass
import math

import pandas as pd


@dataclass(slots=True)
class AnalyticsResult:
    kpis: dict
    state_distribution: pd.DataFrame
    phase_distribution: pd.DataFrame
    ranking_bands: pd.DataFrame
    ranking_phases_critical: pd.DataFrame
    heatmap_matrix: pd.DataFrame
    detail_table: pd.DataFrame


def semaforo_from_score(score: float) -> str:
    if math.isnan(score):
        return "SIN DATOS"
    if score < 0.8:
        return "CRITICO"
    if score < 1.6:
        return "EN PROCESO"
    return "OPTIMO"


def compute_analytics(bands_df: pd.DataFrame, phases_df: pd.DataFrame) -> AnalyticsResult:
    if bands_df.empty or phases_df.empty:
        empty = pd.DataFrame()
        return AnalyticsResult(
            kpis={
                "total_bandas": 0,
                "score_medio_global": 0.0,
                "pct_critico": 0.0,
                "pct_en_proceso": 0.0,
                "pct_optimo": 0.0,
                "bandas_mas_avanzadas": [],
                "bandas_mas_bloqueadas": [],
            },
            state_distribution=empty,
            phase_distribution=empty,
            ranking_bands=empty,
            ranking_phases_critical=empty,
            heatmap_matrix=empty,
            detail_table=empty,
        )

    phases_clean = phases_df.copy()
    phases_clean["estado"] = phases_clean["estado"].fillna("DESCONOCIDO")

    state_distribution = (
        phases_clean.groupby("estado", as_index=False)
        .size()
        .rename(columns={"size": "conteo"})
        .sort_values("conteo", ascending=False)
    )
    total_states = state_distribution["conteo"].sum()
    state_distribution["porcentaje"] = (
        (state_distribution["conteo"] / total_states) * 100
    ).round(2)

    phase_distribution = (
        phases_clean.groupby(["fase", "estado"], as_index=False)
        .size()
        .rename(columns={"size": "conteo"})
        .sort_values(["fase", "conteo"], ascending=[True, False])
    )

    ranking_bands = (
        phases_clean.groupby("banda", as_index=False)["score"]
        .mean(numeric_only=True)
        .rename(columns={"score": "score_global"})
        .sort_values("score_global", ascending=False)
    )
    ranking_bands["semaforo"] = ranking_bands["score_global"].apply(semaforo_from_score)

    critical_by_phase = phases_clean[phases_clean["estado"] == "CRITICO"]
    ranking_phases_critical = (
        critical_by_phase.groupby("fase", as_index=False)
        .size()
        .rename(columns={"size": "total_critico"})
        .sort_values("total_critico", ascending=False)
    )

    heatmap_matrix = phases_clean.pivot_table(
        index="banda",
        columns="fase",
        values="score",
        aggfunc="mean",
    ).reset_index()

    detail_table = (
        phases_clean.pivot_table(
            index="banda",
            columns="fase",
            values="estado",
            aggfunc="first",
        )
        .reset_index()
        .merge(
            bands_df[
                [
                    "banda",
                    "correo_principal",
                    "ultimo_envio",
                    "observaciones",
                    "score_global",
                ]
            ],
            on="banda",
            how="left",
        )
    )

    score_medio = float(ranking_bands["score_global"].mean()) if not ranking_bands.empty else 0.0

    def _pct(status: str) -> float:
        row = state_distribution[state_distribution["estado"] == status]
        if row.empty:
            return 0.0
        return float(row["porcentaje"].iloc[0])

    kpis = {
        "total_bandas": int(bands_df["banda"].nunique()),
        "score_medio_global": round(score_medio, 3),
        "pct_critico": round(_pct("CRITICO"), 2),
        "pct_en_proceso": round(_pct("EN PROCESO"), 2),
        "pct_optimo": round(_pct("OPTIMO"), 2),
        "bandas_mas_avanzadas": ranking_bands.head(5).to_dict(orient="records"),
        "bandas_mas_bloqueadas": ranking_bands.tail(5).to_dict(orient="records"),
    }

    return AnalyticsResult(
        kpis=kpis,
        state_distribution=state_distribution,
        phase_distribution=phase_distribution,
        ranking_bands=ranking_bands,
        ranking_phases_critical=ranking_phases_critical,
        heatmap_matrix=heatmap_matrix,
        detail_table=detail_table,
    )
