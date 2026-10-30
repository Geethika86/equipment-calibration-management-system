import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output_final"
SQL_FILE = OUTPUT_DIR / "datasets.sql"
DB_FILE = OUTPUT_DIR / "fresh_final_test.db"

EXPECTED_COUNTS = {
    "suppliers": 9,
    "instrument_types": 5,
    "calibration_plans": 5,
    "assets": 2000,
    "calibration_events": 5000,
    "certificates": 4950,
    "work_orders": 371,
    "production_uses": 100000,
    "calibration_extensions": 50,
    "approved_exceptions": 50,
    "ground_truth": 54,
    "anomaly_findings": 54,
    "audit_records": 5425,
    "alerts": 58504,
}

if not SQL_FILE.exists():
    raise SystemExit(f"ERROR: SQL export not found: {SQL_FILE}")

if DB_FILE.exists():
    DB_FILE.unlink()

connection = sqlite3.connect(DB_FILE)

try:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SQL_FILE.read_text(encoding="utf-8-sig"))

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }

    errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    failed = False

    print("\n--- FINAL DATASET SQL VERIFICATION ---")
    print(f"SQL file: {SQL_FILE}")
    print(f"Fresh database: {DB_FILE}")
    print(f"Tables created: {len(tables)}")

    for table, expected in EXPECTED_COUNTS.items():
        if table not in tables:
            print(f"FAIL: Missing table {table}")
            failed = True
            continue

        actual = connection.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0]

        status = "PASS" if actual == expected else "FAIL"
        print(f"{status}: {table}: {actual} rows (expected {expected})")

        if actual != expected:
            failed = True

    if errors:
        print("\nFAIL: Foreign-key violations:")
        for error in errors[:10]:
            print(error)
        failed = True
    else:
        print("PASS: No declared foreign-key violations")

    if failed:
        raise SystemExit("\nVERIFICATION FAILED")

    print("\nSUCCESS: SQL import, row counts, and foreign keys verified.")

finally:
    connection.close()
