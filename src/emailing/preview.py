from __future__ import annotations

import pandas as pd


def build_email_preview(bands_df: pd.DataFrame, subject: str) -> dict:
    recipients = (
        bands_df["correo_principal"]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda s: s != ""]
        .unique()
        .tolist()
        if not bands_df.empty and "correo_principal" in bands_df.columns
        else []
    )
    return {
        "subject": subject,
        "total_destinatarios": len(recipients),
        "destinatarios": recipients,
    }
