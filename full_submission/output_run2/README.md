# Equipment Calibration Management System — Synthetic Data Generator

## Purpose
This project generates a synthetic, traceable equipment-calibration lifecycle dataset. It models assets, instrument types, calibration plans and events, certificates, corrective work orders, production uses, emergency extensions, alerts, audit records, and separately stored evaluation ground truth.

## Requirements
- Python 3.10 or newer
- Python standard library only; no third-party packages are required

## Generate the full dataset
From the project directory, run:

```powershell
python generator_quality.py --profile full --seed 20261022 --output-base .\quality_lifecycle
```

## Generate the starter dataset
```powershell
python generator_quality.py --profile starter --seed 20261022 --output-base .\quality_lifecycle_starter
```

## Parameterize dataset size
```powershell
python generator_quality.py --assets 200 --calibrations 500 --uses 10000 --seed 20261022 --output-base .\quality_lifecycle_custom
```

The generator creates `output_run1` and `output_run2`, runs the same seed and parameters twice, and compares SHA-256 checksums. A successful run prints `SUCCESS: All generated files are reproducible.`

## Generated files
- CSV files for every entity/table.
- `datasets.json`: input/business datasets; excludes ground-truth labels.
- `ground_truth.csv` and `ground_truth.json`: separate evaluation labels for intentional anomalies.
- `datasets.sql`: SQLite-compatible table definitions and seed inserts with primary/foreign-key constraints.
- `schema.json`: machine-readable schema metadata.
- `data_dictionary.md`: field definitions, types, requiredness, values/units, uniqueness, validation rules, and relationship cardinalities.
- `validation_summary.txt`: row counts, decision metrics, validation outcomes, and documented edge cases.
- `manifest.json`: file sizes, CSV row counts, and SHA-256 checksums.

## Business rules
1. Calibration due date is derived from calibration event date plus the asset's plan interval.
2. The latest calibration at or before a production-use timestamp determines the applicable calibration.
3. A failed latest calibration blocks use; no preceding calibration requires review.
4. A passing calibration permits use through the plan's grace period. Only an approved emergency extension may extend that window.
5. Failed calibrations receive corrective work orders and impact assessments, except for the one deliberately labelled negative scenario.
6. Required anomalies are deliberately labelled in ground truth and are not silently treated as normal records.
7. Ground truth is excluded from `datasets.json` and must not be used as an input feature when evaluating decisions.

## Date and identifier convention
The synthetic event period is `2025-01-01` through `2025-12-31`. Identifier strings use the documented immutable entity prefixes and zero-padded counters. The `2026` segment in calibration/work-order identifiers is the configured identifier batch year in this generator; it is not the event timestamp year.

## Data provenance and licensing
All generated business records are synthetic and created locally by this generator. No external operational, personal, confidential, or restricted dataset is downloaded or redistributed. Public reference data is not required for generation.

## Validation and tests
Run the project tests with:

```powershell
python -m pytest -v
```

The generator itself also validates primary-key uniqueness, parent references, due-date calculations (excluding the labelled anomaly), certificate reconciliation, failed-calibration corrective actions, extension lifecycle details, use decisions, required edge-case coverage, and reproducibility.
