"""File exports: CSV tables and Excel workbooks (charts save via charts.save_html)."""

from __future__ import annotations

import pandas as pd


def export_csv(df: pd.DataFrame, path: str) -> str:
    df.to_csv(path, index=False)
    return path


def export_workbook(
    projection: pd.DataFrame,
    scenarios: dict[str, pd.DataFrame],
    percentiles: pd.DataFrame | None,
    path: str,
) -> str:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        projection.to_excel(writer, sheet_name="projection", index=False)
        for name, frame in scenarios.items():
            frame.to_excel(writer, sheet_name=f"scenario_{name}", index=False)
        if percentiles is not None:
            percentiles.to_excel(writer, sheet_name="montecarlo_pctl", index=False)
    return path
