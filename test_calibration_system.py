import csv
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "output_completed"

REQUIRED_ANOMALIES = {
    "DUE_DATE_INCONSISTENT_WITH_PLAN",
    "EXPIRED_INSTRUMENT_USED_WITHOUT_EXCEPTION",
    "CERTIFICATE_ASSET_MISMATCH",
    "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT",
}


def load_csv(filename):
    path = DATA / filename
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


class CalibrationSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = load_csv("assets.csv")
        cls.plans = load_csv("calibration_plans.csv")
        cls.types = load_csv("instrument_types.csv")
        cls.events = load_csv("calibration_events.csv")
        cls.certificates = load_csv("certificates.csv")
        cls.work_orders = load_csv("work_orders.csv")
        cls.uses = load_csv("production_uses.csv")
        cls.flags = load_csv("compliance_flags.csv")
        cls.exceptions = load_csv("approved_exceptions.csv")
        cls.findings = load_csv("anomaly_findings.csv")
        cls.truth = load_csv("ground_truth.csv")

        cls.asset_map = {r["asset_id"]: r for r in cls.assets}
        cls.plan_map = {r["plan_id"]: r for r in cls.plans}
        cls.event_map = {r["calibration_id"]: r for r in cls.events}
        cls.flag_map = {r["use_id"]: r for r in cls.flags}

    def truth_record(self, issue_type):
        matches = [
            r for r in self.truth
            if r["issue_type"] == issue_type
        ]
        self.assertEqual(
            len(matches), 1,
            f"Expected exactly one ground-truth record for {issue_type}"
        )
        return matches[0]

    def test_required_dataset_volumes(self):
        self.assertEqual(len(self.assets), 2000)
        self.assertEqual(len(self.events), 5000)
        self.assertEqual(len(self.uses), 100000)
        self.assertEqual(len(self.certificates), 5000)

    def test_primary_ids_are_unique(self):
        checks = [
            (self.assets, "asset_id"),
            (self.plans, "plan_id"),
            (self.types, "type_id"),
            (self.events, "calibration_id"),
            (self.certificates, "certificate_id"),
            (self.work_orders, "work_order_id"),
            (self.uses, "use_id"),
            (self.flags, "use_id"),
        ]
        for rows, field in checks:
            values = [r[field] for r in rows]
            with self.subTest(field=field):
                self.assertTrue(all(values), f"Empty {field}")
                self.assertEqual(len(values), len(set(values)))

    def test_every_use_has_one_compliance_flag(self):
        use_ids = [r["use_id"] for r in self.uses]
        flag_ids = [r["use_id"] for r in self.flags]
        self.assertEqual(len(flag_ids), len(set(flag_ids)))
        self.assertEqual(set(use_ids), set(flag_ids))

    def test_all_required_anomalies_have_findings(self):
        labels = {r["issue_type"] for r in self.truth}
        findings = {
            (r["entity_id"], r["issue_type"])
            for r in self.findings
        }
        self.assertTrue(REQUIRED_ANOMALIES.issubset(labels))
        for record in self.truth:
            self.assertIn(
                (record["entity_id"], record["issue_type"]),
                findings
            )

    def test_due_date_anomaly_violates_plan_interval(self):
        record = self.truth_record(
            "DUE_DATE_INCONSISTENT_WITH_PLAN"
        )
        event = self.event_map[record["entity_id"]]
        asset = self.asset_map[event["asset_id"]]
        plan = self.plan_map[asset["plan_id"]]

        expected = (
            date.fromisoformat(event["event_date"])
            + timedelta(days=int(plan["interval_days"]))
        )
        actual = date.fromisoformat(event["due_date_calculated"])
        self.assertNotEqual(actual, expected)

    def test_certificate_asset_mismatch_is_real(self):
        record = self.truth_record("CERTIFICATE_ASSET_MISMATCH")
        matches = [
            c for c in self.certificates
            if c["certificate_id"] == record["entity_id"]
        ]
        self.assertEqual(len(matches), 1)

        certificate = matches[0]
        event = self.event_map[certificate["calibration_id"]]

        self.assertTrue(
            certificate["asset_id"] != event["asset_id"]
            or certificate["asset_id"] not in self.asset_map
        )

    def test_failed_calibration_has_no_impact_assessment(self):
        record = self.truth_record(
            "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT"
        )
        event = self.event_map[record["entity_id"]]
        self.assertEqual(event["result"], "FAIL")

        linked_orders = [
            order for order in self.work_orders
            if order["calibration_id"] == event["calibration_id"]
        ]
        assessed_orders = [
            order for order in linked_orders
            if order.get("impact_assessment", "").strip()
        ]
        self.assertEqual(
            assessed_orders, [],
            "Found a linked work order with an impact assessment."
        )

    def test_expired_use_is_noncompliant_without_exception(self):
        record = self.truth_record(
            "EXPIRED_INSTRUMENT_USED_WITHOUT_EXCEPTION"
        )
        use_id = record["entity_id"]

        use_matches = [
            u for u in self.uses if u["use_id"] == use_id
        ]
        self.assertEqual(len(use_matches), 1)

        flag = self.flag_map[use_id]
        self.assertEqual(flag["compliance_status"], "NON_COMPLIANT")
        self.assertEqual(
            flag["exception_approved"].strip().lower(), "false"
        )

        approved = [
            e for e in self.exceptions if e["use_id"] == use_id
        ]
        self.assertEqual(approved, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
