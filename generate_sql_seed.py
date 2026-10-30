import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "output_completed"
SCHEMA_FILE = ROOT / "schema.sql"
SEED_FILE = ROOT / "seed.sql"
DB_FILE = ROOT / "calibration_validation.db"

TABLES = [
    ("instrument_types", "instrument_types.csv"),
    ("calibration_plans", "calibration_plans.csv"),
    ("suppliers", "suppliers.csv"),
    ("assets", "assets.csv"),
    ("calibration_events", "calibration_events.csv"),
    ("certificates", "certificates.csv"),
    ("work_orders", "work_orders.csv"),
    ("production_uses", "production_uses.csv"),
    ("approved_exceptions", "approved_exceptions.csv"),
    ("compliance_flags", "compliance_flags.csv"),
    ("anomaly_findings", "anomaly_findings.csv"),
    ("ground_truth", "ground_truth.csv"),
    ("audit_records", "audit_records.csv"),
]


def quote_identifier(value):
    return '"' + value.replace('"', '""') + '"'


def sql_value(value):
    if value is None or value == "":
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def main():
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Missing schema: {SCHEMA_FILE}")

    for _, filename in TABLES:
        if not (DATA_DIR / filename).exists():
            raise FileNotFoundError(f"Missing CSV: {DATA_DIR / filename}")

    # Recreate only the validation database, not the original CSV files.
    if DB_FILE.exists():
        DB_FILE.unlink()

    connection = sqlite3.connect(DB_FILE)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        connection.executescript(SCHEMA_FILE.read_text(encoding="utf-8-sig"))

        with SEED_FILE.open("w", encoding="utf-8", newline="\n") as output:
            output.write("-- Equipment Calibration System SQL seed\n")
            output.write("-- Generated from output_completed CSV files.\n")
            output.write("PRAGMA foreign_keys = ON;\n")
            output.write("BEGIN TRANSACTION;\n\n")

            total_rows = 0

            for table, filename in TABLES:
                csv_path = DATA_DIR / filename

                with csv_path.open(
                    "r", encoding="utf-8-sig", newline=""
                ) as csv_file:
                    reader = csv.DictReader(csv_file)
                    columns = reader.fieldnames

                    if not columns:
                        raise ValueError(f"No header found in {filename}")

                    quoted_columns = ", ".join(
                        quote_identifier(column) for column in columns
                    )

                    insert_sql = (
                        f"INSERT INTO {quote_identifier(table)} "
                        f"({quoted_columns}) VALUES "
                        f"({', '.join('?' for _ in columns)})"
                    )

                    table_count = 0

                    for row in reader:
                        values = [row[column] for column in columns]

                        # Execute the insert to validate the database schema
                        # and foreign-key constraints.
                        connection.execute(insert_sql, values)

                        literal_values = ", ".join(
                            sql_value(value) for value in values
                        )
                        output.write(
                            f"INSERT INTO {quote_identifier(table)} "
                            f"({quoted_columns}) VALUES "
                            f"({literal_values});\n"
                        )

                        table_count += 1
                        total_rows += 1

                output.write("\n")
                print(f"Loaded {table}: {table_count} rows")

            output.write("COMMIT;\n")
            connection.commit()

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if foreign_key_errors:
            print("WARNING: Foreign-key violations found:")
            for error in foreign_key_errors[:20]:
                print(error)
            raise RuntimeError(
                "Database foreign-key checks failed. Review the errors above."
            )

        print(f"\nSUCCESS: SQL seed created: {SEED_FILE}")
        print(f"Total rows exported: {total_rows}")
        print(f"Validation database: {DB_FILE}")
        print("Foreign-key checks: PASS")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
