"""BoQ PDF task-extraction utilities.

This module implements the text-based BoQ extraction logic underlying the
authors' Life Cycle Inventory automation work. It extracts task quantity,
description, group/chapter, and unit from a text-based BoQ PDF.

Methodological reference
------------------------
S. Gachkar, D. Gachkar, E. Ghofrani, A. García Martínez, C. Angulo Bahón,
"Text-based algorithms for automating life cycle inventory analysis in
building sector life cycle assessment studies," Journal of Cleaner Production,
486 (2025) 144448. https://doi.org/10.1016/j.jclepro.2024.144448

No project data, licensed database content, credentials, or proprietary source
files are embedded in this module.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import math
import re

import pandas as pd
import pdfplumber

SUPPORTED_UNITS = ("u", "ud", "kg", "m", "m2", "m3", "l", "ml")


def alphabet_check(value) -> bool:
    """Return True when a string/list contains alphabetic or separator characters."""
    if isinstance(value, (list, str)):
        return (
            any(c.isalpha() for c in value)
            or any(c == "_" for c in value)
            or any(c == ":" for c in value)
            or any(c == "-" for c in value[1:])
        )
    return False


def string_to_num(value: str) -> float:
    """Convert the numeric tokens used in the source BoQ format to float."""
    value = str(value).replace(",", "").strip()
    value = re.sub(r"[~=]", "", value)
    value = re.sub(r"[^\d\./-]", "", value)
    try:
        if "/" in value:
            return float(Fraction(value))
        return float(value)
    except (ValueError, ZeroDivisionError):
        return 0.0


def remove_missings(words: list[str]) -> list[str]:
    """Remove blank tokens in place and return the list."""
    words[:] = (value for value in words if value not in ("", " "))
    return words


def multiplication_check(num1: float, num2: float, num3: float) -> bool:
    return math.floor(num1) == math.floor(num2 * num3)


def unit_check(words: list[str]) -> bool:
    return any(word in SUPPORTED_UNITS for word in words)


def unit_finder(words: list[str]) -> str:
    for word in words:
        if word in SUPPORTED_UNITS:
            return word
    return "0"


def text_clean(text: str) -> str:
    return re.sub(r"[^a-zA-ZñÑáéíóúÁÉÍÓÚ\s]", " ", text)


def line_4_clean(words: list[str]) -> bool:
    if len(words) == 3:
        return True
    if len(words) > 3:
        return not words[-4][-1].isnumeric()
    return False


def not_multiplication(line: list[str]) -> bool:
    if len(line) < 3:
        return True
    if alphabet_check(line[-1]) or alphabet_check(line[-2]) or alphabet_check(line[-3]):
        return True

    nums = [string_to_num(line[-1]), string_to_num(line[-2]), string_to_num(line[-3])]
    if not multiplication_check(nums[0], nums[1], nums[2]):
        return True
    return nums[0] == 0


def pages_next_lines_check(line: list[str]) -> bool:
    page_words = {"página", "página:", "pág", "page", "pagina"}
    return any(word in page_words for word in line)


def next_line_check(line_next: list[str]) -> bool:
    if len(line_next) < 2:
        return False

    cond1 = (
        (line_next[0][-1].isnumeric() or line_next[0][0].isnumeric())
        and alphabet_check(line_next[1])
    )
    cond2 = unit_check(line_next)
    cond3 = ("total" in line_next) or ("parcial" in line_next)
    return cond1 or cond2 or cond3


def _safe_page_text(pdf, page_index: int) -> str:
    text = pdf.pages[page_index].extract_text()
    return text or ""


def last_lines_check(i_page: int, total_pages: int, pdf) -> bool:
    """Inspect the start of the next page when a task boundary is near a page break."""
    if i_page + 1 >= total_pages:
        return False

    page_text = _safe_page_text(pdf, i_page + 1)
    page_text = (
        page_text.replace("€", "")
        .replace("$", "")
        .replace("m²", "m2 ")
        .replace("m³", "m3 ")
    )
    list_lines = page_text.split("\n")

    for j_line in range(min(6, len(list_lines))):
        line = remove_missings(list_lines[j_line].lower().split(" "))

        if j_line < len(list_lines) - 1:
            line_next = remove_missings(list_lines[j_line + 1].lower().split(" "))
        else:
            line_next = ["x", "x", "x"]
        if len(line_next) < 3:
            line_next += ["0", "x"]

        if j_line < len(list_lines) - 2:
            line_nextnext = remove_missings(list_lines[j_line + 2].lower().split(" "))
        else:
            line_nextnext = ["x", "x", "x"]
        if len(line_nextnext) < 3:
            line_nextnext += ["0", "x"]

        if any("(continuación...)" == word for word in line):
            return False
        if next_line_check(line):
            return True
        if quantity_line_finder(
            line, line_next, line_nextnext, j_line, i_page + 1, total_pages, pdf
        ):
            return False

    return False


def quantity_line_finder(
    line: list[str],
    line_next: list[str],
    line_nextnext: list[str],
    j_line: int,
    i_page: int,
    total_pages: int,
    pdf,
) -> bool:
    """Identify a quantity/total line that separates BoQ task descriptions."""
    page_lines_num = len(_safe_page_text(pdf, i_page).split("\n"))

    if len(line) < 3:
        return False

    if alphabet_check(line[-1]) or alphabet_check(line[-2]) or alphabet_check(line[-3]):
        return False

    last_1 = string_to_num(line[-1])
    last_2 = string_to_num(line[-2])
    last_3 = string_to_num(line[-3])

    if not multiplication_check(last_1, last_2, last_3):
        return False
    if not line_4_clean(line):
        return False

    # The original algorithm checks that the next lines look like descriptions/tasks
    # rather than additional numeric calculation rows.
    next_is_textual = any(
        alphabet_check(token)
        for token in line_next[-min(4, len(line_next)):]
    )
    nextnext_is_textual = any(
        alphabet_check(token)
        for token in line_nextnext[-min(4, len(line_nextnext)):]
    ) or (bool(line_nextnext) and alphabet_check(line_nextnext[0]))

    if not (next_is_textual and nextnext_is_textual):
        return False

    if not (
        not_multiplication(line_next)
        and (not_multiplication(line_nextnext) or next_line_check(line_next))
    ):
        return False

    near_page_end = (
        j_line >= page_lines_num - 3
        or pages_next_lines_check(line_next)
        or pages_next_lines_check(line_nextnext)
    )

    if near_page_end and i_page < total_pages - 1:
        return last_lines_check(i_page, total_pages, pdf)
    if near_page_end and i_page == total_pages - 1:
        return True

    return next_line_check(line_next) or next_line_check(line_nextnext)


def extract_tasks_main(file_name: str | Path) -> pd.DataFrame:
    """Extract task-level data from a BoQ-style PDF.

    Parameters
    ----------
    file_name:
        Path to a text-based PDF. Scanned PDFs require OCR before this function.

    Returns
    -------
    pandas.DataFrame
        Columns: Task Quantity, Task Description, Task Group, Task Unit.
    """
    file_name = Path(file_name)
    if not file_name.exists():
        raise FileNotFoundError(file_name)

    df = pd.DataFrame(columns=["Task Quantity", "Task Description"])

    with pdfplumber.open(file_name) as pdf:
        total_pages = len(pdf.pages)

        for i_page in range(total_pages):
            task_quantity = []
            task_description = []
            separator_line_flag = []

            page_text = _safe_page_text(pdf, i_page)
            page_text = (
                page_text.replace("€", "")
                .replace("$", "")
                .replace("m²", "m2 ")
                .replace("m³", "m3 ")
            )
            list_lines = page_text.split("\n")

            for j_line in range(2, len(list_lines)):
                line = remove_missings(list_lines[j_line].lower().split(" "))

                if j_line < len(list_lines) - 1:
                    line_next = remove_missings(list_lines[j_line + 1].lower().split(" "))
                else:
                    line_next = ["x", "x", "x"]
                if len(line_next) < 3:
                    line_next += ["0", "x"]

                if j_line < len(list_lines) - 2:
                    line_nextnext = remove_missings(list_lines[j_line + 2].lower().split(" "))
                else:
                    line_nextnext = ["x", "x", "x"]
                if len(line_nextnext) < 3:
                    line_nextnext += ["0", "x"]

                if quantity_line_finder(
                    line, line_next, line_nextnext, j_line, i_page, total_pages, pdf
                ):
                    task_quantity.append(line[-3])
                    separator_line_flag.append(j_line)

            if separator_line_flag:
                for f in range(len(separator_line_flag)):
                    if f == 0:
                        description = " \n ".join(list_lines[2:separator_line_flag[f]])
                    else:
                        description = " \n ".join(
                            list_lines[separator_line_flag[f - 1] + 1:separator_line_flag[f]]
                        )
                    task_description.append(description)

                if separator_line_flag[-1] < len(list_lines) - 1:
                    task_description.append(
                        " \n ".join(list_lines[separator_line_flag[-1] + 1:])
                    )

                for f in range(len(separator_line_flag)):
                    if df.empty:
                        df = pd.DataFrame(
                            {
                                "Task Quantity": [task_quantity[f]],
                                "Task Description": [task_description[f]],
                            }
                        )
                    elif f == 0 and df.iloc[-1]["Task Quantity"] == 0:
                        df.iloc[-1, df.columns.get_loc("Task Quantity")] = task_quantity[f]
                        df.iloc[-1, df.columns.get_loc("Task Description")] = (
                            str(df.iloc[-1]["Task Description"])
                            + " \n "
                            + task_description[f]
                        )
                    else:
                        df = pd.concat(
                            [
                                df,
                                pd.DataFrame(
                                    {
                                        "Task Quantity": [task_quantity[f]],
                                        "Task Description": [task_description[f]],
                                    }
                                ),
                            ],
                            ignore_index=True,
                        )

                if separator_line_flag[-1] < len(list_lines) - 1:
                    df = pd.concat(
                        [
                            df,
                            pd.DataFrame(
                                {
                                    "Task Quantity": [0],
                                    "Task Description": [task_description[-1]],
                                }
                            ),
                        ],
                        ignore_index=True,
                    )

    if df.empty:
        return pd.DataFrame(
            columns=["Task Quantity", "Task Description", "Task Group", "Task Unit"]
        )

    if df.iloc[-1]["Task Quantity"] == 0:
        df = df.iloc[:-1].copy()

    df_cleaned = df.copy()
    df_cleaned["Task Description"] = (
        df_cleaned["Task Description"].fillna("").astype(str)
    )

    # 1. Find task group / chapter and carry it forward.
    df_cleaned["Task Group"] = "0"
    for i in range(len(df_cleaned)):
        idx = df_cleaned.index[i]
        description = df_cleaned.loc[idx, "Task Description"]
        description_lower = description.lower()

        if ("capítulo" in description_lower) or ("cap." in description_lower):
            list_lines = description.split("\n")
            for j, line in enumerate(list_lines):
                line_lower = line.lower().strip()

                if (
                    "capítulo" in line_lower
                    and "subcapítulo" not in line_lower
                    and "total" not in line_lower
                ):
                    chapter_text = text_clean(
                        line_lower.replace("capítulo", "").strip()
                    )
                    df_cleaned.loc[df_cleaned.index[i:], "Task Group"] = chapter_text
                    df_cleaned.loc[idx, "Task Description"] = " \n ".join(
                        list_lines[j + 1:]
                    )
                    break

                if (
                    "cap." in line_lower
                    and "subcapítulo" not in line_lower
                    and "total" not in line_lower
                ):
                    words = remove_missings(line_lower.split())
                    if len(words) > 0 and len(words[0]) == 6:
                        chapter_text = text_clean(
                            line_lower.replace("cap.", "").strip()
                        )
                        df_cleaned.loc[df_cleaned.index[i:], "Task Group"] = chapter_text
                        df_cleaned.loc[idx, "Task Description"] = " \n ".join(
                            list_lines[j + 1:]
                        )
                        break

    # 2. Find task unit.
    df_cleaned["Task Unit"] = "0"
    for i in range(len(df_cleaned)):
        idx = df_cleaned.index[i]
        description = df_cleaned.loc[idx, "Task Description"]
        list_lines = description.split("\n")

        for j, line in enumerate(list_lines):
            line_lower = line.lower().strip()
            words = remove_missings(line_lower.split())

            if unit_check(words):
                task_unit = unit_finder(words)
                df_cleaned.loc[idx, "Task Unit"] = task_unit
                parts = line_lower.split(task_unit, 1)
                list_lines[j] = parts[1].strip() if len(parts) > 1 else line_lower
                df_cleaned.loc[idx, "Task Description"] = " \n ".join(
                    list_lines[j:]
                )
                break

    # 3. Remove trailing calculation lines.
    for i in range(len(df_cleaned)):
        idx = df_cleaned.index[i]
        description = df_cleaned.loc[idx, "Task Description"]
        cleaned_lines = []

        for line in description.split("\n"):
            words = remove_missings(line.lower().split())
            if len(words) <= 1:
                cleaned_lines.append(line)
                continue
            if not alphabet_check(words[-1]) and not alphabet_check(words[-2]):
                continue
            cleaned_lines.append(line)

        df_cleaned.loc[idx, "Task Description"] = " \n ".join(cleaned_lines)

    # 4. Normalise output.
    for column, default in [
        ("Task Description", ""),
        ("Task Group", "0"),
        ("Task Unit", "0"),
    ]:
        df_cleaned[column] = (
            df_cleaned[column].fillna(default).astype(str).str.lower().str.strip()
        )

    df_cleaned["Task Quantity"] = pd.to_numeric(
        df_cleaned["Task Quantity"], errors="coerce"
    )

    return df_cleaned.reset_index(drop=True)


# Compatibility alias with the authors' original notebook.
ExtractTasks_Main = extract_tasks_main
