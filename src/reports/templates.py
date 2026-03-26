from __future__ import annotations

from dataclasses import dataclass

from reportlab.lib import colors


@dataclass(slots=True)
class BrandTheme:
    red: colors.Color
    yellow: colors.Color
    white: colors.Color
    dark: colors.Color


def build_brand_theme() -> BrandTheme:
    return BrandTheme(
        red=colors.HexColor("#C62828"),
        yellow=colors.HexColor("#FFCA28"),
        white=colors.HexColor("#FFFFFF"),
        dark=colors.HexColor("#1E1E1E"),
    )
