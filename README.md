# Automated BoQ-to-LCA Workflow

Public reproducibility package for an automated building Life Cycle Assessment
workflow based on **Bill of Quantities (BoQ) text extraction, task matching,
material aggregation, and A1--A3 impact calculation**.

The repository is intentionally designed so that the implementation can be
inspected and executed without redistributing confidential project documents or
third-party licensed construction/environmental databases.

## Related publications

The implementation builds on the methods developed and validated in the
following two papers. If you use this repository, please cite both:

1. **Gachkar, S., Gachkar, D., Ghofrani, E., García Martínez, A., & Angulo Bahón, C. (2025).**
   *Text-based algorithms for automating life cycle inventory analysis in building sector life cycle assessment studies.*
   **Journal of Cleaner Production, 486, 144448.**
   DOI: https://doi.org/10.1016/j.jclepro.2024.144448  
   ScienceDirect: https://www.sciencedirect.com/science/article/abs/pii/S0959652624038976

2. **Gachkar, D., Gachkar, S., Ghofrani, E., García Martínez, A., & Angulo Bahón, C. (2025).**
   *Automating data integration for construction Life Cycle Assessment using fuzzy matching and supervised learning.*
   **Automation in Construction, 178, 106381.**
   DOI: https://doi.org/10.1016/j.autcon.2025.106381  
   ScienceDirect: https://www.sciencedirect.com/science/article/pii/S0926580525004212

BibTeX entries are provided in [`REFERENCES.bib`](REFERENCES.bib). A
machine-readable citation file is provided in [`CITATION.cff`](CITATION.cff).

## What this repository contains

```text
.
├── CITATION.cff
├── DATA_AVAILABILITY.md
├── LICENSE
├── README.md
├── REFERENCES.bib
├── requirements.txt
├── data
│   ├── example
│   │   ├── demo_boq.pdf
│   │   ├── impact_factors.csv
│   │   ├── reference_database.csv
│   │   └── spanish_stopwords.txt
│   └── templates
│       ├── impact_factors_template.csv
│       └── reference_database_template.csv
├── notebooks
│   └── 01_full_workflow_demo.ipynb
├── outputs
│   └── .gitkeep
├── src
│   ├── __init__.py
│   ├── extract_tasks.py
│   ├── sensitivity.py
│   └── workflow.py
└── tests
    └── test_demo.py
```

### `src/extract_tasks.py`

Extracts task-level information from a text-based BoQ PDF, including:

- task quantity;
- task description;
- task group/chapter; and
- task unit.

This module corresponds to the BoQ text-extraction methodology developed in
the Journal of Cleaner Production paper cited above.

### `src/workflow.py`

Implements the public case-study workflow:

1. extract BoQ tasks;
2. match BoQ task groups to the reference database;
3. restrict candidate reference tasks using task group and unit;
4. identify the closest task description using Bag-of-Words and cosine similarity;
5. recover the material decomposition of matched tasks;
6. aggregate material quantities;
7. merge the aggregated inventory with an authorised impact-factor table; and
8. calculate component-level and total A1--A3 impacts.

The environmental/reference database integration used in the research builds
on the fuzzy-matching and Random-Forest methodology described in the
Automation in Construction paper cited above. Because the underlying
third-party databases are not redistributed here, the public executable
example uses a synthetic impact-factor table with the same required schema.

### `src/sensitivity.py`

Contains the Monte Carlo material-matching perturbation analysis used as a
robustness/sensitivity test. The error rates are hypothetical stress-test
scenarios and are not empirical classifier error rates.

## Quick start

Run the following commands from the repository root.

### 1. Create a Python environment

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
```

Activate it:

**Windows**

```bash
.venv\Scripts\activate
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Verify the installation

```bash
python -m pytest -q
```

The repository includes tests for both the synthetic PDF extraction and the
end-to-end demonstration workflow.

### 4. Run the demonstration notebook

```bash
jupyter notebook notebooks/01_full_workflow_demo.ipynb
```

The notebook runs only on synthetic example data included in this repository.

## Using authorised research/project data

To apply the workflow to another project, supply:

1. a text-based BoQ PDF compatible with the extraction assumptions;
2. a reference construction table using the schema shown in
   `data/templates/reference_database_template.csv`; and
3. an impact-factor table using the schema shown in
   `data/templates/impact_factors_template.csv`.

The code does not require the original case-study files to be present in the
repository.

### Reference database schema

Required fields:

- `Task Code`
- `Task Title`
- `Task Unit`
- `Task Group`
- `Task Description`
- `Material Code`
- `Material Title`
- `Material Unit`
- `Material Quantity`

### Impact-factor schema

Required fields:

- `Component Code`
- `BCCA Impact Factor`

Additional metadata columns may be included and are preserved during the merge.

## Data and copyright

The repository contains **only synthetic demonstration inputs**. It does not
contain or redistribute:

- the original residential-project BoQ;
- confidential project documentation;
- BCCA database extracts;
- ecoinvent datasets or exports;
- the original merged BCCA--ecoinvent impact-factor database;
- private pickle/Excel source databases;
- credentials, API keys, usernames, local file paths, or personal contact data.

The synthetic example values were created solely to demonstrate the execution
of the code and are not copied from the case study or from BCCA/ecoinvent.

For details, see [`DATA_AVAILABILITY.md`](DATA_AVAILABILITY.md).

## Reproducing the exact paper result

This repository provides **computational reproducibility of the workflow**.
Exact numerical reproduction of the paper's residential case-study result
requires authorised access to the same project documentation, construction
database, environmental database/version, material correspondences, and
unit-conversion assumptions used by the authors.

This separation is intentional: making the authors' implementation public
does not confer redistribution rights for third-party databases.

## Software environment

The tested dependencies are listed in `requirements.txt`. Runtime values in the
paper should be interpreted as hardware- and input-dependent: execution time
varies with computer processing power, BoQ size, BoQ structure/complexity, and
the size of the reference/candidate search space.

## License

The source code in this repository is released under the
[MIT License](LICENSE).

The MIT License applies only to the authors' source code and synthetic example
files contained in this repository. It does **not** grant rights to any
third-party datasets or project documents that are not distributed here.
