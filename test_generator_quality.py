import tempfile
import unittest
import sqlite3
from pathlib import Path

from generator_quality import DataGenerator


class CalibrationQualityTests(unittest.TestCase):
    def make_generator(self):
        generator = DataGenerator(seed=20261022, num_assets=100, num_calibrations=250, num_uses=5000)
        generator.generate_all()
        return generator

    def test_required_dataset_volumes(self):
        generator = self.make_generator()
        self.assertEqual(len(generator.assets), 100)
        self.assertEqual(len(generator.calibration_events), 250)
        self.assertEqual(len(generator.production_uses), 5000)

    def test_required_anomaly_labels_are_present(self):
        generator = self.make_generator()
        issue_types = {row["issue_type"] for row in generator.ground_truth}
        self.assertTrue({
            "DUE_DATE_INCONSISTENT_WITH_PLAN",
            "EXPIRED_INSTRUMENT_USED_WITHOUT_EXCEPTION",
            "CERTIFICATE_ASSET_MISMATCH",
            "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT",
        }.issubset(issue_types))

    def test_approved_extension_path_is_exercised(self):
        generator = self.make_generator()
        self.assertTrue(any(row["approval_status"] == "APPROVED" for row in generator.calibration_extensions))
        self.assertTrue(any(row["use_decision"] == "ALLOWED_EXTENSION" and row["exception_applied"]
                            for row in generator.production_uses))

    def test_failed_calibrations_have_assessment_except_labelled_case(self):
        generator = self.make_generator()
        labelled = {row["entity_id"] for row in generator.ground_truth
                    if row["issue_type"] == "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT"}
        work_order_by_calibration = {row["calibration_id"]: row for row in generator.work_orders}
        for event in generator.calibration_events:
            if event["result"] != "FAIL":
                continue
            work_order = work_order_by_calibration.get(event["calibration_id"])
            self.assertIsNotNone(work_order, event["calibration_id"])
            self.assertTrue(work_order["corrective_action"])
            if event["calibration_id"] in labelled:
                self.assertFalse(work_order["impact_assessment"])
            else:
                self.assertTrue(work_order["impact_assessment"])

    def test_primary_keys_are_unique(self):
        generator = self.make_generator()
        pk_fields = {
            "suppliers": "supplier_id", "instrument_types": "type_id", "calibration_plans": "plan_id",
            "assets": "asset_id", "calibration_events": "calibration_id", "certificates": "certificate_id",
            "work_orders": "work_order_id", "production_uses": "use_id",
            "calibration_extensions": "extension_id", "alerts": "alert_id",
            "audit_records": "audit_id", "ground_truth": "ground_truth_id",
        }
        for table, pk in pk_fields.items():
            rows = generator._datasets()[table]
            values = [row[pk] for row in rows]
            self.assertEqual(len(values), len(set(values)), f"duplicate key in {table}.{pk}")

    def test_sql_export_and_validation_summary(self):
        generator = self.make_generator()
        with tempfile.TemporaryDirectory() as directory:
            generator.export_data(directory)
            output = Path(directory)
            self.assertTrue((output / "datasets.sql").is_file())
            self.assertTrue((output / "schema.json").is_file())
            self.assertTrue((output / "data_dictionary.md").is_file())
            summary = (output / "validation_summary.txt").read_text(encoding="utf-8")
            self.assertIn("Overall validation: PASS", summary)
            self.assertIn("ALLOWED_EXTENSION", summary)
            # Prove the SQL seed can be imported into a fresh database with no FK violations.
            connection = sqlite3.connect(":memory:")
            try:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.executescript((output / "datasets.sql").read_text(encoding="utf-8"))
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM assets").fetchone()[0], 100)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM production_uses").fetchone()[0], 5000)
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
