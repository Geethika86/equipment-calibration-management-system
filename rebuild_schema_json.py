import json
import sqlite3
from pathlib import Path

db_path = Path("calibration_validation.db")
output_path = Path("schema.json")

if not db_path.exists():
    raise SystemExit("ERROR: calibration_validation.db was not found.")

connection = sqlite3.connect(db_path)

try:
    tables = connection.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """).fetchall()

    schema = {}

    for (table_name,) in tables:
        columns = connection.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()

        foreign_keys = connection.execute(
            f'PRAGMA foreign_key_list("{table_name}")'
        ).fetchall()

        schema[table_name] = {
            "columns": [
                {
                    "name": column[1],
                    "type": column[2],
                    "required": bool(column[3]),
                    "primary_key_position": column[5]
                }
                for column in columns
            ],
            "foreign_keys": [
                {
                    "column": fk[3],
                    "references_table": fk[2],
                    "references_column": fk[4]
                }
                for fk in foreign_keys
            ]
        }

    output_path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    print("Schema JSON rebuilt from SQLite metadata.")
    print("Tables documented:", len(schema))
    print("Saved:", output_path)

    with output_path.open(encoding="utf-8") as file:
        check = json.load(file)

    print("JSON parse check: PASS")
    print("Documented tables:")
    for name in check:
        print("-", name)

finally:
    connection.close()
