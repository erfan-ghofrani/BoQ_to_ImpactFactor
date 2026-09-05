# Data Availability and Redistribution Statement

This public repository is deliberately data-minimised to support
reproducibility while respecting project confidentiality and third-party
database licensing.

## Included in the repository

The files under `data/example/` are fully synthetic and were created solely to
demonstrate the computational workflow. They are not extracted, sampled, or
derived from the residential case study, BCCA, ecoinvent, or another
proprietary database.

The repository also contains empty input-schema templates under
`data/templates/`.

## Not included

The following research inputs are not redistributed:

- the original case-study BoQ and project documentation;
- BCCA database extracts where redistribution rights are not established;
- ecoinvent datasets, exports, environmental factors, or database records;
- the authors' original merged BCCA--ecoinvent database;
- project-specific result tables that may reproduce restricted source data.

## Reproducibility scope

The public package allows users to inspect and execute the complete public
case-study processing sequence using synthetic inputs.

Exact numerical reproduction of the published residential case-study result
requires authorised access to the same source documentation, database
versions, mappings, and conversion assumptions used in the research.

Users who possess authorised equivalent inputs can apply them through the
documented schemas without modifying the source code.

## Related methods

The BoQ extraction methodology is documented in:

Gachkar, S., Gachkar, D., Ghofrani, E., García Martínez, A., & Angulo Bahón, C.
(2025). *Text-based algorithms for automating life cycle inventory analysis in
building sector life cycle assessment studies*. Journal of Cleaner Production,
486, 144448. https://doi.org/10.1016/j.jclepro.2024.144448

The construction/environmental database-integration methodology is documented
in:

Gachkar, D., Gachkar, S., Ghofrani, E., García Martínez, A., & Angulo Bahón, C.
(2025). *Automating data integration for construction Life Cycle Assessment
using fuzzy matching and supervised learning*. Automation in Construction,
178, 106381. https://doi.org/10.1016/j.autcon.2025.106381
