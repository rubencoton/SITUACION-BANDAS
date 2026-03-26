from __future__ import annotations

from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def build_report_charts(
    output_dir: Path,
    state_distribution: pd.DataFrame,
    ranking_bands: pd.DataFrame,
    ranking_phases_critical: pd.DataFrame,
    heatmap_matrix: pd.DataFrame,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    paths["state_distribution"] = output_dir / "state_distribution.png"
    _plot_state_distribution(state_distribution, paths["state_distribution"])

    paths["ranking_bands"] = output_dir / "ranking_bands.png"
    _plot_ranking_bands(ranking_bands, paths["ranking_bands"])

    paths["ranking_phases_critical"] = output_dir / "ranking_phases_critical.png"
    _plot_phase_criticality(ranking_phases_critical, paths["ranking_phases_critical"])

    paths["heatmap"] = output_dir / "heatmap.png"
    _plot_heatmap(heatmap_matrix, paths["heatmap"])

    return paths


def _plot_state_distribution(df: pd.DataFrame, path: Path) -> None:
    plt.figure(figsize=(8, 4.5))
    if df.empty:
        plt.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        plt.axis("off")
    else:
        plt.bar(df["estado"], df["conteo"], color=["#C62828", "#FFCA28", "#2E7D32", "#9E9E9E"][: len(df)])
        plt.title("Distribucion global por estado")
        plt.xlabel("Estado")
        plt.ylabel("Total")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def _plot_ranking_bands(df: pd.DataFrame, path: Path) -> None:
    plt.figure(figsize=(8, 5))
    if df.empty:
        plt.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        plt.axis("off")
    else:
        top = df.head(10).sort_values("score_global", ascending=True)
        plt.barh(top["banda"], top["score_global"], color="#C62828")
        plt.title("Ranking de bandas (score global)")
        plt.xlabel("Score")
        plt.ylabel("Banda")
        plt.xlim(0, 2)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def _plot_phase_criticality(df: pd.DataFrame, path: Path) -> None:
    plt.figure(figsize=(8, 4.5))
    if df.empty:
        plt.text(0.5, 0.5, "Sin estados criticos", ha="center", va="center")
        plt.axis("off")
    else:
        plt.bar(df["fase"], df["total_critico"], color="#C62828")
        plt.title("Fases mas criticas")
        plt.xlabel("Fase")
        plt.ylabel("Casos criticos")
        plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def _plot_heatmap(df: pd.DataFrame, path: Path) -> None:
    plt.figure(figsize=(9, 6))
    if df.empty or len(df.columns) <= 1:
        plt.text(0.5, 0.5, "Sin datos para heatmap", ha="center", va="center")
        plt.axis("off")
    else:
        data = df.set_index("banda")
        matrix = data.values.astype(float)
        im = plt.imshow(matrix, cmap="RdYlGn", aspect="auto", vmin=0, vmax=2)
        plt.colorbar(im, fraction=0.03, pad=0.04, label="Score fase")
        plt.xticks(range(len(data.columns)), data.columns, rotation=30, ha="right")
        plt.yticks(range(len(data.index)), data.index)
        plt.title("Matriz banda x fase")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
