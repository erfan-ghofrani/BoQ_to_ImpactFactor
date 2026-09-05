"""Public BoQ-to-LCA workflow.

This module connects BoQ task extraction and task/reference matching with
material aggregation and building-level A1--A3 impact calculation while
keeping project-specific and licensed datasets outside the repository.

Methodological references
-------------------------
1. S. Gachkar, D. Gachkar, E. Ghofrani, A. García Martínez, C. Angulo Bahón,
   "Text-based algorithms for automating life cycle inventory analysis in
   building sector life cycle assessment studies," Journal of Cleaner
   Production, 486 (2025) 144448.
   https://doi.org/10.1016/j.jclepro.2024.144448

2. D. Gachkar, S. Gachkar, E. Ghofrani, A. García Martínez, C. Angulo Bahón,
   "Automating data integration for construction Life Cycle Assessment using
   fuzzy matching and supervised learning," Automation in Construction,
   178 (2025) 106381.
   https://doi.org/10.1016/j.autcon.2025.106381

The licensed/reference data used to create the research database are not
redistributed in this repository. The public example therefore uses synthetic
inputs with the same documented schemas.
"""

from __future__ import annotations

from pathlib import Path
import re
import time

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .extract_tasks import extract_tasks_main


def clean_data(data):
    regex = re.compile(r"[^a-zA-ZñÑáéíóúÁÉÍÓÚ\s]")
    if isinstance(data, str):
        return regex.sub(" ", data).lower().strip().replace("\n", " ")
    return [clean_data(value) for value in data]


def remove_space(data):
    if isinstance(data, str):
        return data.lower().strip().lstrip().replace("\n", "")
    return [remove_space(value) for value in data]


def parse_material_number(value) -> float:
    """Parse the number format used in the original reference-table quantities."""
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float, np.number)):
        return float(value)
    value = str(value).replace(".", "").replace(",", ".")
    return float(value)


def validate_columns(df: pd.DataFrame, required, name: str) -> None:
    missing = sorted(set(required).difference(df.columns))
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def load_stopwords(path: str | Path | None) -> list[str]:
    if path is None:
        return []
    path = Path(path)
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def prepare_inputs(reference_database: pd.DataFrame, extracted_tasks: pd.DataFrame):
    validate_columns(
        reference_database,
        [
            "Task Description", "Task Group", "Task Unit", "Task Code", "Task Title",
            "Material Code", "Material Title", "Material Unit", "Material Quantity",
        ],
        "reference_database",
    )
    validate_columns(
        extracted_tasks,
        ["Task Description", "Task Group", "Task Unit", "Task Quantity"],
        "extracted_tasks",
    )

    rd = reference_database.copy().rename(
        columns={
            "Task Description": "Task Description (RD)",
            "Task Group": "Task Group (RD)",
            "Task Unit": "Task Unit (RD)",
            "Task Code": "Task Code (RD)",
            "Task Title": "Task Title (RD)",
        }
    )

    mp = extracted_tasks.copy().rename(
        columns={
            "Task Description": "Task Description (MP)",
            "Task Group": "Task Group (MP)",
            "Task Unit": "Task Unit (MP)",
            "Task Quantity": "Task Quantity (MP)",
        }
    ).reset_index(names="Task ID (MP)")

    return rd, mp


def match_tasks_to_reference(
    reference_database: pd.DataFrame,
    extracted_tasks: pd.DataFrame,
    stop_words: list[str] | None = None,
):
    """Match extracted BoQ tasks to reference tasks using group + cosine similarity."""
    rd, mp = prepare_inputs(reference_database, extracted_tasks)

    vectorizer = CountVectorizer(
        token_pattern=r"(?u)\b\w\w+\b",
        lowercase=True,
        stop_words=stop_words or None,
        ngram_range=(1, 2),
        analyzer="word",
        max_features=None,
    )

    # Stage A: match task group.
    mp["Corresponding Task Group in RD"] = "0"
    rd_groups = clean_data(rd["Task Group (RD)"].astype(str).tolist())

    for t_mp in range(len(mp)):
        group_list = [clean_data(str(mp["Task Group (MP)"].iloc[t_mp]))] + rd_groups
        matrix = vectorizer.fit_transform(group_list)
        similarities = cosine_similarity(matrix[1:], matrix[0]).ravel()
        best_group_idx = int(np.argmax(similarities))
        mp.loc[mp.index[t_mp], "Corresponding Task Group in RD"] = rd_groups[best_group_idx]

    # Stage B: restrict candidate tasks by group and unit.
    rd_desc = remove_space(rd["Task Description (RD)"].astype(str).tolist())
    mp_desc = remove_space(mp["Task Description (MP)"].astype(str).tolist())

    candidate_indices = {}
    for t_mp in range(len(mp)):
        group = mp["Corresponding Task Group in RD"].iloc[t_mp]
        unit = mp["Task Unit (MP)"].iloc[t_mp]
        indices = [
            t_rd
            for t_rd in range(len(rd))
            if clean_data(str(rd["Task Group (RD)"].iloc[t_rd])) == group
            and rd["Task Unit (RD)"].iloc[t_rd] == unit
        ]
        candidate_indices[t_mp] = indices

    # Stage C: choose the closest task description.
    best_reference = []
    for t_mp in range(len(mp_desc)):
        indices = candidate_indices[t_mp]
        if not indices:
            best_reference.append(-1)
            continue

        docs = [mp_desc[t_mp]] + [rd_desc[idx] for idx in indices]
        matrix = vectorizer.fit_transform(docs)
        similarities = cosine_similarity(matrix[1:], matrix[0]).ravel()
        best_reference.append(indices[int(np.argmax(similarities))])

    return rd, mp, best_reference


def build_material_inventory(
    rd: pd.DataFrame,
    mp: pd.DataFrame,
    best_reference: list[int],
) -> pd.DataFrame:
    """Recover material decompositions for matched tasks and calculate quantities."""
    pieces = []

    for t_mp, ref_idx in enumerate(best_reference):
        if ref_idx == -1:
            continue

        task_code = rd["Task Code (RD)"].iloc[ref_idx]
        ref_rows = rd[rd["Task Code (RD)"] == task_code].reset_index(drop=True)
        mp_rows = pd.concat(
            [mp.iloc[[t_mp]].reset_index(drop=True)] * len(ref_rows),
            ignore_index=True,
        )

        merged = pd.concat([mp_rows, ref_rows], axis=1)
        merged = merged.drop(columns=["Corresponding Task Group in RD"])
        pieces.append(merged)

    if not pieces:
        raise RuntimeError("No BoQ tasks could be matched to the reference database.")

    inventory = pd.concat(pieces, ignore_index=True)
    inventory["Material Quantity Numeric"] = inventory["Material Quantity"].map(
        parse_material_number
    )
    inventory["Task Quantity Numeric"] = pd.to_numeric(
        inventory["Task Quantity (MP)"], errors="coerce"
    )
    inventory["Total Material"] = (
        inventory["Material Quantity Numeric"] * inventory["Task Quantity Numeric"]
    )
    return inventory


def calculate_impacts(
    inventory: pd.DataFrame,
    impact_factors: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate components and merge them with an authorised impact-factor table."""
    validate_columns(
        impact_factors,
        ["Component Code", "BCCA Impact Factor"],
        "impact_factors",
    )

    aggregated = (
        inventory[
            ["Material Code", "Material Title", "Material Unit", "Total Material"]
        ]
        .copy()
        .groupby("Material Code", as_index=False)
        .agg(
            {
                "Total Material": "sum",
                "Material Title": "first",
                "Material Unit": "first",
            }
        )
        .rename(
            columns={
                "Material Code": "Component Code",
                "Total Material": "Total Component Quantity",
                "Material Title": "Component Title",
                "Material Unit": "Component Unit",
            }
        )
    )

    aggregated["Component Code"] = (
        aggregated["Component Code"].astype(str).str.strip()
    )

    impact_factors = impact_factors.copy()
    impact_factors["Component Code"] = (
        impact_factors["Component Code"].astype(str).str.strip()
    )
    impact_factors["BCCA Impact Factor"] = pd.to_numeric(
        impact_factors["BCCA Impact Factor"], errors="coerce"
    )

    results = pd.merge(
        aggregated,
        impact_factors,
        on="Component Code",
        how="inner",
        validate="one_to_one",
    )

    results["Total Component Quantity"] = pd.to_numeric(
        results["Total Component Quantity"], errors="coerce"
    )
    results["Total Component Impact Factor"] = (
        results["BCCA Impact Factor"] * results["Total Component Quantity"]
    )
    return results


def run_from_pdf(
    boq_pdf: str | Path,
    reference_database: pd.DataFrame,
    impact_factors: pd.DataFrame,
    stop_words: list[str] | None = None,
):
    """Execute the public end-to-end case-study workflow from PDF to A1--A3 total."""
    start = time.perf_counter()

    tasks = extract_tasks_main(boq_pdf)
    rd, mp, best_reference = match_tasks_to_reference(
        reference_database=reference_database,
        extracted_tasks=tasks,
        stop_words=stop_words,
    )
    inventory = build_material_inventory(rd, mp, best_reference)
    results = calculate_impacts(inventory, impact_factors)

    total_impact = results["Total Component Impact Factor"].sum()
    runtime = time.perf_counter() - start

    return {
        "tasks": tasks,
        "inventory": inventory,
        "results": results,
        "total_impact": float(total_impact),
        "runtime_seconds": float(runtime),
    }
