"""Sensitivity utilities used to stress-test material matching.

The error rates are hypothetical perturbation scenarios, not measured model
error rates.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def simulate_matching_errors(
    results: pd.DataFrame,
    error_rate: float,
    n_simulations: int = 1000,
    seed: int = 42,
    unit_column: str = "Component Unit",
) -> dict:
    """Monte Carlo perturbation of a proportion of material matches.

    Selected components are assigned an alternative impact factor drawn from
    another component with the same unit. This is a controlled stress test.
    """
    required = {
        "BCCA Impact Factor",
        "Total Component Quantity",
        unit_column,
    }
    missing = required.difference(results.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    df = results.copy()
    baseline = (
        pd.to_numeric(df["BCCA Impact Factor"], errors="coerce")
        * pd.to_numeric(df["Total Component Quantity"], errors="coerce")
    ).sum()

    rng = np.random.default_rng(seed)
    totals = []
    n_components = len(df)
    n_errors = max(1, round(n_components * error_rate))

    for _ in range(n_simulations):
        temp = df.copy()
        selected = rng.choice(temp.index, size=min(n_errors, n_components), replace=False)

        for idx in selected:
            current_unit = temp.loc[idx, unit_column]
            alternatives = temp[
                (temp[unit_column] == current_unit)
                & (temp.index != idx)
                & (temp["BCCA Impact Factor"].notna())
            ]

            if not alternatives.empty:
                alt_idx = rng.choice(alternatives.index)
                temp.loc[idx, "BCCA Impact Factor"] = temp.loc[
                    alt_idx, "BCCA Impact Factor"
                ]

        total = (
            pd.to_numeric(temp["BCCA Impact Factor"], errors="coerce")
            * pd.to_numeric(temp["Total Component Quantity"], errors="coerce")
        ).sum()
        totals.append(total)

    totals = np.asarray(totals, dtype=float)

    return {
        "Assumed matching error (%)": 100 * error_rate,
        "Mean impact": float(totals.mean()),
        "Mean change (%)": float((totals.mean() - baseline) / baseline * 100),
        "5th percentile": float(np.percentile(totals, 5)),
        "95th percentile": float(np.percentile(totals, 95)),
    }


def run_matching_sensitivity(
    results: pd.DataFrame,
    error_rates=(0.05, 0.10, 0.20),
    n_simulations: int = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    rows = [
        simulate_matching_errors(
            results,
            error_rate=rate,
            n_simulations=n_simulations,
            seed=seed,
        )
        for rate in error_rates
    ]
    return pd.DataFrame(rows)
