from __future__ import annotations

from datetime import date


def build_executive_insights(
    kpis: dict,
    ranking_phases_critical,
    previous_snapshot: dict | None,
) -> list[str]:
    insights: list[str] = []

    insights.append(
        f"Se monitorizan {kpis.get('total_bandas', 0)} bandas activas en el periodo."
    )
    insights.append(
        "Distribucion global de estados: "
        f"CRITICO {kpis.get('pct_critico', 0):.2f}% | "
        f"EN PROCESO {kpis.get('pct_en_proceso', 0):.2f}% | "
        f"OPTIMO {kpis.get('pct_optimo', 0):.2f}%."
    )

    top_blocked = kpis.get("bandas_mas_bloqueadas", [])
    if top_blocked:
        blocked_names = ", ".join(item["banda"] for item in top_blocked[:3])
        insights.append(f"Bandas con mayor bloqueo relativo: {blocked_names}.")

    if ranking_phases_critical is not None and not ranking_phases_critical.empty:
        phase = ranking_phases_critical.iloc[0]["fase"]
        total = int(ranking_phases_critical.iloc[0]["total_critico"])
        insights.append(
            f"La fase con mayor concentracion de riesgo es {phase} con {total} casos criticos."
        )

    if previous_snapshot is None:
        insights.append(
            "No existe historial previo equivalente; la comparativa interperiodo se activara en el siguiente informe."
        )
        return insights

    prev_kpis = previous_snapshot.get("kpis", {})
    prev_score = float(prev_kpis.get("score_medio_global", 0.0))
    curr_score = float(kpis.get("score_medio_global", 0.0))
    delta = round(curr_score - prev_score, 3)
    direction = "mejora" if delta >= 0 else "deterioro"
    insights.append(
        f"Comparado con el informe equivalente anterior, el score medio muestra {direction} de {delta:+.3f} puntos."
    )

    prev_crit = float(prev_kpis.get("pct_critico", 0.0))
    curr_crit = float(kpis.get("pct_critico", 0.0))
    delta_crit = round(curr_crit - prev_crit, 2)
    insights.append(
        f"El porcentaje de estados CRITICO cambio {delta_crit:+.2f} puntos porcentuales."
    )

    generated_at = previous_snapshot.get("generated_at")
    if generated_at:
        insights.append(f"Base comparativa tomada del snapshot anterior ({generated_at}).")
    else:
        insights.append(
            f"Base comparativa tomada del snapshot anterior disponible ({date.today().isoformat()})."
        )

    return insights
