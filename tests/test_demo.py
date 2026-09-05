from pathlib import Path
import pandas as pd

from src.extract_tasks import extract_tasks_main
from src.workflow import load_stopwords, run_from_pdf


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "example"


def test_demo_extraction():
    tasks = extract_tasks_main(DATA / "demo_boq.pdf")
    assert len(tasks) == 2
    assert tasks.loc[0, "Task Group"] == "demo masonry"
    assert tasks.loc[0, "Task Unit"] == "m2"
    assert tasks.loc[1, "Task Group"] == "demo structure"
    assert tasks.loc[1, "Task Unit"] == "m3"


def test_demo_end_to_end():
    reference_db = pd.read_csv(DATA / "reference_database.csv")
    impact_factors = pd.read_csv(DATA / "impact_factors.csv")
    stop_words = load_stopwords(DATA / "spanish_stopwords.txt")

    run = run_from_pdf(
        DATA / "demo_boq.pdf",
        reference_db,
        impact_factors,
        stop_words,
    )

    assert len(run["results"]) == 4
    assert run["total_impact"] > 0
