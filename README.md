# Equipment Calibration Management System

## 1. Overview

This project generates deterministic synthetic data for equipment calibration scheduling, certificate management, production-use compliance, emergency extensions, approved exceptions, anomaly detection, and audit traceability.

All records are synthetic. They are for demonstration and testing, not real operational decisions.

## 2. Technology

- Python 3.10 or newer
- Python standard library
- CSV and JSON exports
- SQLite-compatible SQL export
- Python unittest
- SHA-256 checksums for reproducibility

## 3. Generate the datasets

Activate the virtual environment if needed:

```powershell
.\venv\Scripts\Activate.ps1
```

Generate a starter dataset:

```powershell
python .\generator_quality.py --profile starter --output-base starter_submission
```

Generate the full dataset:

```powershell
python .\generator_quality.py --profile full --output-base full_submission
```

To see all available options:

```powershell
python .\generator_quality.py --help
```

The generator uses a fixed random seed of `20261022`.

The generated period is 2025-01-01 through 2025-12-31.

## 4. Full dataset counts

The validated full run produced:

| Dataset | Rows |
|---|---:|
| Suppliers | 9 |
| Instrument types | 5 |
| Calibration plans | 5 |
| Assets | 2,000 |
| Calibration events | 5,000 |
| Certificates | 4,950 |
| Work orders | 371 |
| Production uses | 100,000 |
| Calibration extensions | 50 |
| Approved exceptions | 50 |
| Alerts | 58,504 |
| Audit records | 5,425 |
| Ground-truth labels | 54 |
| Anomaly findings | 54 |

The certificate count is lower than the calibration-event count because missing-certificate scenarios are intentionally included.

## 5. Required anomaly scenarios

The generated data includes labelled scenarios for:

1. `CERTIFICATE_MISSING`
2. `DUE_DATE_INCONSISTENT_WITH_PLAN`
3. `EXPIRED_INSTRUMENT_USED_WITHOUT_EXCEPTION`
4. `CERTIFICATE_ASSET_MISMATCH`
5. `FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT`

The generator writes evaluation labels to `ground_truth.csv` and `ground_truth.json`, separate from the source event datasets.

Do not use these evaluation labels as model input features when evaluating anomaly detection.

## 6. Output files

The output directory includes CSV files for assets, instrument types, calibration plans, calibration events, certificates, suppliers, work orders, production uses, extensions, approved exceptions, alerts, audit records, ground truth, and anomaly findings.

It also includes:

- `datasets.json` — combined JSON export
- `datasets.sql` — SQLite-compatible schema and seed data
- `schema.json` — schema and business-rule metadata
- `data_dictionary.md` — descriptions of datasets and fields
- `validation_summary.txt` — generation counts, validation results, and labelled edge cases
- `manifest.json` — output file metadata, row counts, and checksums

## 7. Validation and tests

Run both automated test suites:

```powershell
python -m unittest -v test_calibration_system.py
python -m unittest -v test_generator_quality.py
```

**Verified test results:**

- `test_calibration_system.py` — 8 tests passed.
- `test_generator_quality.py` — 6 tests passed.
- Total — 14 tests passed.

The tests cover:

- Dataset volumes
- Primary-key uniqueness
- Compliance flags
- Required anomaly scenarios
- Approved extension workflow
- Failed-calibration assessment checks
- SQL export and validation summary

The full run reported these checks as passing:

- Primary-key uniqueness
- Foreign-key integrity, except for the documented business mismatch
- Due-date arithmetic, excluding the labelled anomaly
- Failed-calibration corrective-action checks
- Required edge-case coverage

The tests and validation checks cover selected requirements; they do not prove every possible lifecycle transition or business rule.

## 8. Reproducibility

The generator creates two output runs and compares corresponding generated files using SHA-256 hashes.

Matching hashes demonstrate byte-for-byte reproducibility for the files compared.

The manifest is excluded from some comparison scripts and should be checked separately if it contains output-specific metadata.

The validated starter and full generation runs completed successfully, with all 19 compared generated files passing the reproducibility checks.

## 9. Data integrity and intentional anomalies

The certificate-to-calibration asset mismatch is intentionally included as a labelled business anomaly. It must remain detectable rather than being silently corrected during generation.

The extension and approved-exception records are linked by their generated identifiers. The dataset includes approved exceptions that can be referenced by production-use records.

Polymorphic entity references in alerts and audit records require application-level validation because they do not point to one fixed parent table.

## 10. Limitations

- All records are synthetic.
- Compliance decisions reflect the rules implemented by the generator.
- Passing automated tests does not prove complete regulatory compliance.
- Lifecycle transition enforcement, effective-date handling, and every possible relationship constraint require separate verification.
- Evaluation labels must remain separate from input features to avoid label leakage.

## 11. Submission checklist

- [ ] Generate starter and full datasets.
- [ ] Confirm the output counts.
- [ ] Run all automated tests.
- [ ] Compare two full runs using SHA-256.
- [ ] Review schema and data dictionary.
- [ ] Verify the SQL export in a fresh SQLite database.
- [ ] Review each required anomaly scenario.
- [ ] Include AI-use disclosure and relevant prompt history required by the challenge.
- [ ] Check for secrets and unintended files before publishing the repository.