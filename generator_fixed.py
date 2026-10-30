import os
import argparse
import csv
import json
import random
import hashlib
import sqlite3
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from bisect import bisect_right

# Fixed seed makes every generated file reproducible.
SEED = 20261022
DATE_FORMAT = "%Y-%m-%d"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


class DataGenerator:
    def __init__(self, seed=SEED, num_assets=2000, num_calibrations=5000, num_uses=100000):
        self.seed = seed
        self.num_assets = num_assets
        self.num_calibrations = num_calibrations
        self.num_uses = num_uses
        self.random = random.Random(seed)
        self.start_date = datetime(2025, 1, 1, 0, 0, 0)
        self.end_date = datetime(2025, 12, 31, 23, 59, 59)
        self.end_exclusive = datetime(2026, 1, 1, 0, 0, 0)

        self.suppliers = []
        self.instrument_types = []
        self.calibration_plans = []
        self.assets = []
        self.calibration_events = []
        self.certificates = []
        self.work_orders = []
        self.production_uses = []
        self.alerts = []
        self.audit_records = []
        self.ground_truth = []
        self.calibration_extensions = []
        self._ground_truth_keys = set()

    @staticmethod
    def _date(value):
        return value.strftime(DATE_FORMAT) if value else ""

    @staticmethod
    def _timestamp(value):
        return value.strftime(TIMESTAMP_FORMAT) if value else ""

    def _add_ground_truth(self, entity_type, entity_id, issue_type, details, expected_decision):
        key = (entity_type, entity_id, issue_type)
        if key in self._ground_truth_keys:
            return
        self._ground_truth_keys.add(key)
        self.ground_truth.append({
            "ground_truth_id": f"GT-{len(self.ground_truth) + 1:06d}",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "issue_type": issue_type,
            "details": details,
            "expected_decision": expected_decision
        })

    def generate_all(self):
        print("Generating master data...")
        self._generate_master_data()
        print(f"Generating assets ({self.num_assets})...")
        self._generate_assets()
        print(f"Generating calibration events ({self.num_calibrations})...")
        self._generate_calibrations()
        print("Generating emergency extensions...")
        self._generate_extensions()
        print(f"Generating production-use events ({self.num_uses})...")
        self._generate_production_uses()
        print("Injecting labelled edge cases...")
        self._inject_edge_cases()
        print("Generating audit history and alerts...")
        self._generate_audit_records()
        self._generate_alerts()
        self._refresh_asset_calibration_state()

    def _generate_master_data(self):
        for i in range(1, 10):
            self.suppliers.append({
                "supplier_id": f"SUP-{i:03d}",
                "name": f"Calibration Vendor {i} Ltd.",
                "iso_accredited": i % 2 == 0,
                "country": "IN"
            })

        types = [
            ("PRESSURE_GAUGE", 90, "PSI", 0.5),
            ("TEMP_SENSOR", 180, "Celsius", 0.8),
            ("TORQUE_WRENCH", 30, "Nm", 1.0),
            ("FLOW_METER", 365, "L/min", 0.7),
            ("SCALE_BALANCE", 120, "kg", 0.6)
        ]
        for idx, (name, interval, unit, tolerance) in enumerate(types, 1):
            self.instrument_types.append({
                "type_id": f"IT-{idx:03d}",
                "type_name": name,
                "measurement_unit": unit,
                "default_interval_days": interval,
                "tolerance_limit": tolerance
            })

        for instrument_type in self.instrument_types:
            self.calibration_plans.append({
                "plan_id": f"PLAN-{instrument_type['type_id']}",
                "type_id": instrument_type["type_id"],
                "interval_days": instrument_type["default_interval_days"],
                "grace_period_days": 7,
                "policy": "BLOCK_OVERDUE_USE"
            })

    def _generate_assets(self):
        statuses = ["ACTIVE", "ACTIVE", "ACTIVE", "MAINTENANCE", "RETIRED"]
        serials = set()
        for i in range(1, self.num_assets + 1):
            asset_id = f"AST-{i:06d}"
            instrument_type = self.random.choice(self.instrument_types)
            plan = next(p for p in self.calibration_plans if p["type_id"] == instrument_type["type_id"])
            serial_number = f"SN-{self.random.randint(100000, 999999)}"
            while serial_number in serials:
                serial_number = f"SN-{self.random.randint(100000, 999999)}"
            serials.add(serial_number)
            self.assets.append({
                "asset_id": asset_id,
                "type_id": instrument_type["type_id"],
                "plan_id": plan["plan_id"],
                "serial_number": serial_number,
                "status": self.random.choice(statuses),
                "commissioned_date": self._date(self.start_date - timedelta(days=self.random.randint(30, 1500))),
                "last_calibration_date": "",
                "next_due_date": ""
            })

    def _generate_calibrations(self):
        asset_by_id = {a["asset_id"]: a for a in self.assets}
        plan_by_id = {p["plan_id"]: p for p in self.calibration_plans}
        self._asset_calibrations = defaultdict(list)
        self._used_certificate_ids = set()

        for i in range(1, self.num_calibrations + 1):
            asset = self.random.choice(self.assets)
            plan = plan_by_id[asset["plan_id"]]
            supplier = self.random.choice(self.suppliers)
            # IDs follow the required immutable naming convention.
            calibration_id = f"CAL-{asset['asset_id']}-2026-{i:06d}"
            event_date = self.start_date + timedelta(seconds=self.random.randint(0, int((self.end_exclusive - self.start_date).total_seconds()) - 1))
            result = "PASS" if self.random.random() < 0.92 else "FAIL"
            due_date = event_date + timedelta(days=plan["interval_days"])
            measurement_value = round(self.random.uniform(0.0, 100.0), 3)
            measured_error = round(self.random.uniform(0.0, 1.5), 3)
            if result == "FAIL":
                measured_error = round(max(measured_error, plan_by_id[asset["plan_id"]]["interval_days"] / 100), 3)
            event = {
                "calibration_id": calibration_id,
                "asset_id": asset["asset_id"],
                "supplier_id": supplier["supplier_id"],
                "event_date": self._timestamp(event_date),
                "result": result,
                "measurement_value": measurement_value,
                "measurement_unit": next(t["measurement_unit"] for t in self.instrument_types if t["type_id"] == asset["type_id"]),
                "measured_error": measured_error,
                "due_date_calculated": self._date(due_date),
                "event_status": "COMPLETED"
            }
            self.calibration_events.append(event)
            self._asset_calibrations[asset["asset_id"]].append(event)

            # A small, explicitly labelled certificate gap is part of the baseline.
            if i % 100 != 0:
                certificate_id = f"CERT-{calibration_id}"
                self.certificates.append({
                    "certificate_id": certificate_id,
                    "calibration_id": calibration_id,
                    "asset_id": asset["asset_id"],
                    "issued_date": self._date(event_date),
                    "valid_from": self._date(event_date),
                    "valid_until": self._date(due_date),
                    "certificate_status": "VALID"
                })
                self._used_certificate_ids.add(calibration_id)
            else:
                self._add_ground_truth("CalibrationEvent", calibration_id, "CERTIFICATE_MISSING",
                                       "Calibration event has no certificate record.", "RAISE_CERTIFICATE_GAP_ALERT")

            # Every baseline failure gets a corrective work order and impact assessment.
            if result == "FAIL":
                self._create_work_order(event, i)

        # Sort event history so subsequent decisions use the most recent preceding event.
        for asset_id in self._asset_calibrations:
            self._asset_calibrations[asset_id].sort(key=lambda x: x["event_date"])

    def _create_work_order(self, calibration, sequence):
        wo_id = f"WO-2026-{len(self.work_orders) + 1:06d}"
        failed_at = datetime.strptime(calibration["event_date"], TIMESTAMP_FORMAT)
        downtime_start = failed_at + timedelta(hours=1)
        downtime_hours = self.random.randint(2, 24)
        downtime_end = downtime_start + timedelta(hours=downtime_hours)
        status = ["OPEN", "IN_PROGRESS", "COMPLETED"][len(self.work_orders) % 3]
        self.work_orders.append({
            "work_order_id": wo_id,
            "asset_id": calibration["asset_id"],
            "calibration_id": calibration["calibration_id"],
            "issue_description": "Failed tolerance verification",
            "corrective_action": "Inspect instrument, adjust calibration, and perform verification",
            "impact_assessment": "Review measurements produced since the last successful calibration",
            "opened_at": self._timestamp(failed_at),
            "downtime_start": self._timestamp(downtime_start),
            "downtime_end": self._timestamp(downtime_end),
            "downtime_hours": downtime_hours,
            "status": status
        })
        self.audit_records.append({
            "audit_id": f"AUD-{len(self.audit_records) + 1:06d}",
            "entity_type": "WorkOrder",
            "entity_id": wo_id,
            "action": "CREATED",
            "from_state": "",
            "to_state": status,
            "timestamp": self._timestamp(failed_at)
        })

    def _generate_extensions(self):
        # Approved emergency extensions are explicit records and never overwrite the original due date.
        candidates = [c for c in self.calibration_events if c["result"] == "PASS"]
        self.random.shuffle(candidates)
        for calibration in candidates[:min(50, len(candidates))]:
            original_due = datetime.strptime(calibration["due_date_calculated"], DATE_FORMAT)
            extension_days = self.random.choice([3, 7, 14])
            extension_id = f"EXT-{len(self.calibration_extensions) + 1:06d}"
            self.calibration_extensions.append({
                "extension_id": extension_id,
                "asset_id": calibration["asset_id"],
                "calibration_id": calibration["calibration_id"],
                "original_due_date": self._date(original_due),
                "extended_due_date": self._date(original_due + timedelta(days=extension_days)),
                "extension_days": extension_days,
                "reason": "Emergency production continuity extension",
                "approved_by": "QUALITY-MANAGER-001",
                "approval_status": "APPROVED",
                "approved_at": self._timestamp(original_due - timedelta(days=1))
            })

    def _refresh_asset_calibration_state(self):
        for asset in self.assets:
            events = self._asset_calibrations.get(asset["asset_id"], [])
            if not events:
                asset["last_calibration_date"] = ""
                asset["next_due_date"] = ""
                continue
            latest = events[-1]
            asset["last_calibration_date"] = latest["event_date"][:10]
            asset["next_due_date"] = latest["due_date_calculated"]

    def _effective_due_date(self, calibration_id, original_due):
        extensions = [e for e in self.calibration_extensions
                      if e["calibration_id"] == calibration_id and e["approval_status"] == "APPROVED"]
        if not extensions:
            return original_due, None
        selected = max(extensions, key=lambda e: datetime.strptime(e["extended_due_date"], DATE_FORMAT))
        extended = datetime.strptime(selected["extended_due_date"], DATE_FORMAT)
        return max(original_due, extended), selected["extension_id"]

    def _generate_production_uses(self):
        uses_seen = set()
        asset_ids = [a["asset_id"] for a in self.assets]
        for i in range(1, self.num_uses + 1):
            asset_id = self.random.choice(asset_ids)
            use_time = self.start_date + timedelta(seconds=self.random.randint(0, int((self.end_exclusive - self.start_date).total_seconds()) - 1))
            # Keep the required asset/timestamp naming convention while preventing duplicate IDs.
            use_id = f"USE-{asset_id}-{use_time.strftime('%Y%m%d%H%M%S')}"
            while use_id in uses_seen:
                use_time += timedelta(seconds=1)
                use_id = f"USE-{asset_id}-{use_time.strftime('%Y%m%d%H%M%S')}"
            uses_seen.add(use_id)

            events = self._asset_calibrations.get(asset_id, [])
            event_times = [e["event_date"] for e in events]
            event_index = bisect_right(event_times, self._timestamp(use_time)) - 1
            applicable = events[event_index] if event_index >= 0 else None
            exception_applied = False
            exception_id = ""
            applicable_calibration_id = applicable["calibration_id"] if applicable else ""
            effective_due = None
            if applicable is None:
                decision = "REVIEW_NO_CALIBRATION"
                flagged_overdue = True
            elif applicable["result"] == "FAIL":
                decision = "BLOCKED_FAILED_CALIBRATION"
                flagged_overdue = True
            else:
                due_date = datetime.strptime(applicable["due_date_calculated"], DATE_FORMAT)
                effective_due, matching_exception_id = self._effective_due_date(applicable["calibration_id"], due_date)
                exception_applied = bool(matching_exception_id and use_time.date() > due_date.date() and use_time.date() <= effective_due.date())
                exception_id = matching_exception_id if exception_applied else ""
                if use_time.date() <= effective_due.date():
                    decision = "ALLOWED_EXTENSION" if exception_applied else "ALLOWED_IN_CALIBRATION_WINDOW"
                    flagged_overdue = False
                else:
                    decision = "BLOCKED_OVERDUE"
                    flagged_overdue = True
            self.production_uses.append({
                "use_id": use_id,
                "asset_id": asset_id,
                "use_timestamp": self._timestamp(use_time),
                "applicable_calibration_id": applicable_calibration_id,
                "flagged_overdue": flagged_overdue,
                "use_decision": decision,
                "exception_applied": exception_applied,
                "exception_id": exception_id
            })

    def _inject_edge_cases(self):
        # Required case 1: due date inconsistent with the plan.
        inconsistent_calibration_id = ""
        if self.calibration_events:
            cal = self.calibration_events[0]
            inconsistent_calibration_id = cal["calibration_id"]
            cal["due_date_calculated"] = "2099-01-01"
            self._add_ground_truth("CalibrationEvent", cal["calibration_id"],
                                   "DUE_DATE_INCONSISTENT_WITH_PLAN",
                                   "Stored due date does not equal event date plus plan interval.",
                                   "FLAG_DUE_DATE_INCONSISTENCY")

        # Required case 2: expired instrument used without an exception.
        # Add an explicit use after the applicable calibration expiry, using an asset with a PASS event.
        pass_events = [
            c for c in self.calibration_events
            if c["result"] == "PASS" and c["calibration_id"] != inconsistent_calibration_id
            and datetime.strptime(c["due_date_calculated"], DATE_FORMAT) < datetime(2025, 12, 1)
        ]
        if not pass_events:
            pass_events = [c for c in self.calibration_events
                           if c["result"] == "PASS" and c["calibration_id"] != inconsistent_calibration_id]
        if pass_events:
            cal = pass_events[0]
            due = datetime.strptime(cal["due_date_calculated"], DATE_FORMAT)
            use_time = due + timedelta(days=30, hours=1)
            asset_id = cal["asset_id"]
            use_id = f"USE-{asset_id}-{use_time.strftime('%Y%m%d%H%M%S')}"
            # Replace one baseline use rather than adding a 100001st row; the required
            # production-use volume remains exactly num_uses.
            replacement_index = len(self.production_uses) - 1
            while any(u["use_id"] == use_id and index != replacement_index
                      for index, u in enumerate(self.production_uses)):
                use_time += timedelta(seconds=1)
                use_id = f"USE-{asset_id}-{use_time.strftime('%Y%m%d%H%M%S')}"
            self.production_uses[replacement_index] = {
                "use_id": use_id,
                "asset_id": asset_id,
                "use_timestamp": self._timestamp(use_time),
                "applicable_calibration_id": cal["calibration_id"],
                "flagged_overdue": True,
                "use_decision": "BLOCKED_OVERDUE",
                "exception_applied": False,
                "exception_id": ""
            }
            self._add_ground_truth("ProductionUse", use_id, "EXPIRED_INSTRUMENT_USED_WITHOUT_EXCEPTION",
                                   "Use event occurs after calibration expiry without an approved extension.",
                                   "BLOCK_USE_AND_RAISE_HIGH_ALERT")

        # Required case 3: certificate points to a different existing asset (FK remains valid).
        if len(self.certificates) > 1:
            cert = self.certificates[1]
            original_asset = cert["asset_id"]
            other_asset = next(a["asset_id"] for a in self.assets if a["asset_id"] != original_asset)
            cert["asset_id"] = other_asset
            self._add_ground_truth("Certificate", cert["certificate_id"], "CERTIFICATE_ASSET_MISMATCH",
                                   "Certificate asset differs from the asset on its calibration event.",
                                   "FLAG_CERTIFICATE_ASSET_MISMATCH")

        # Required case 4: failed calibration without work order/impact assessment.
        if len(self.calibration_events) > 2:
            cal = self.calibration_events[2]
            cal["result"] = "FAIL"
            # Re-evaluate uses against the injected final calibration result.
            for use in self.production_uses:
                if use.get("applicable_calibration_id") == cal["calibration_id"]:
                    use["flagged_overdue"] = True
                    use["use_decision"] = "BLOCKED_FAILED_CALIBRATION"
                    use["exception_applied"] = False
                    use["exception_id"] = ""
            # Deliberately remove any baseline work order for this calibration so the exception is unambiguous.
            self.work_orders = [w for w in self.work_orders if w["calibration_id"] != cal["calibration_id"]]
            self._add_ground_truth("CalibrationEvent", cal["calibration_id"],
                                   "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT",
                                   "Calibration failed but no corrective work order or impact assessment exists.",
                                   "CREATE_CORRECTIVE_WORK_ORDER_AND_IMPACT_ASSESSMENT")

    def _generate_audit_records(self):
        # Record calibration creation and state changes as separate audit events.
        for cal in self.calibration_events:
            self.audit_records.append({
                "audit_id": f"AUD-{len(self.audit_records) + 1:06d}",
                "entity_type": "CalibrationEvent",
                "entity_id": cal["calibration_id"],
                "action": "RECORD_CREATED",
                "from_state": "",
                "to_state": cal["event_status"],
                "timestamp": cal["event_date"]
            })
        for issue in self.ground_truth:
            self.audit_records.append({
                "audit_id": f"AUD-{len(self.audit_records) + 1:06d}",
                "entity_type": issue["entity_type"],
                "entity_id": issue["entity_id"],
                "action": "EDGE_CASE_INJECTED",
                "from_state": "BASELINE",
                "to_state": issue["issue_type"],
                "timestamp": self._timestamp(self.end_date)
            })

    def _generate_alerts(self):
        for cal in self.calibration_events:
            if cal["result"] == "FAIL":
                self.alerts.append({
                    "alert_id": f"ALT-{len(self.alerts) + 1:06d}",
                    "asset_id": cal["asset_id"],
                    "entity_type": "CalibrationEvent",
                    "entity_id": cal["calibration_id"],
                    "alert_type": "FAILED_CALIBRATION",
                    "severity": "HIGH",
                    "description": "Calibration failed; assess production impact and corrective action.",
                    "status": "OPEN",
                    "created_at": cal["event_date"]
                })
        for use in self.production_uses:
            if use["flagged_overdue"]:
                self.alerts.append({
                    "alert_id": f"ALT-{len(self.alerts) + 1:06d}",
                    "asset_id": use["asset_id"],
                    "entity_type": "ProductionUse",
                    "entity_id": use["use_id"],
                    "alert_type": use["use_decision"],
                    "severity": "HIGH" if use["use_decision"].startswith("BLOCKED") else "MEDIUM",
                    "description": "Production use is outside a valid calibration window or requires compliance review.",
                    "status": "OPEN",
                    "created_at": use["use_timestamp"]
                })
        for issue in self.ground_truth:
            self.alerts.append({
                "alert_id": f"ALT-{len(self.alerts) + 1:06d}",
                "asset_id": "",
                "entity_type": issue["entity_type"],
                "entity_id": issue["entity_id"],
                "alert_type": issue["issue_type"],
                "severity": "HIGH",
                "description": issue["details"],
                "status": "OPEN",
                "created_at": self._timestamp(self.end_date)
            })

    def _datasets(self):
        approved_exceptions = [{
            "exception_id": e["extension_id"],
            "asset_id": e["asset_id"],
            "calibration_id": e["calibration_id"],
            "original_due_date": e["original_due_date"],
            "extended_due_date": e["extended_due_date"],
            "extension_days": e["extension_days"],
            "reason": e["reason"],
            "approved_by": e["approved_by"],
            "approval_status": e["approval_status"],
            "approved_at": e["approved_at"]
        } for e in self.calibration_extensions]
        anomaly_findings = [{
            "finding_id": f"FND-{i:06d}",
            "ground_truth_id": issue["ground_truth_id"],
            "entity_type": issue["entity_type"],
            "entity_id": issue["entity_id"],
            "issue_type": issue["issue_type"],
            "details": issue["details"],
            "expected_decision": issue["expected_decision"],
            "finding_status": "KNOWN_ANOMALY"
        } for i, issue in enumerate(self.ground_truth, 1)]
        return {
            "suppliers": self.suppliers,
            "instrument_types": self.instrument_types,
            "calibration_plans": self.calibration_plans,
            "assets": self.assets,
            "calibration_events": self.calibration_events,
            "certificates": self.certificates,
            "work_orders": self.work_orders,
            "production_uses": self.production_uses,
            "calibration_extensions": self.calibration_extensions,
            "approved_exceptions": approved_exceptions,
            "alerts": self.alerts,
            "audit_records": self.audit_records,
            "ground_truth": self.ground_truth,
            "anomaly_findings": anomaly_findings
        }

    def export_data(self, output_dir="output"):
        os.makedirs(output_dir, exist_ok=True)
        datasets = self._datasets()

        # Remove stale generated exports so the manifest describes this run only.
        expected_names = {f"{name}.csv" for name in datasets} | {"datasets.json", "ground_truth.json", "datasets.sql", "schema.json", "data_dictionary.md", "validation_summary.txt", "manifest.json"}
        for filename in os.listdir(output_dir):
            path = os.path.join(output_dir, filename)
            if os.path.isfile(path) and (filename.endswith(".csv") or filename in expected_names):
                os.remove(path)

        for name, rows in datasets.items():
            if not rows:
                # Export header-only CSV when a dataset is empty, using schema fields below.
                fields = self._fieldnames(name)
            else:
                fields = list(rows[0].keys())
            with open(os.path.join(output_dir, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)

        # Ground truth is deliberately exported separately so it cannot accidentally
        # become part of the input feature bundle.
        input_datasets = {name: rows for name, rows in datasets.items() if name != "ground_truth"}
        with open(os.path.join(output_dir, "datasets.json"), "w", encoding="utf-8") as f:
            json.dump(input_datasets, f, indent=2, ensure_ascii=False)
            f.write("\n")
        with open(os.path.join(output_dir, "ground_truth.json"), "w", encoding="utf-8") as f:
            json.dump(self.ground_truth, f, indent=2, ensure_ascii=False)
            f.write("\n")

        self._export_sql(os.path.join(output_dir, "datasets.sql"), datasets)
        self._export_schema(os.path.join(output_dir, "schema.json"))
        self._export_data_dictionary(os.path.join(output_dir, "data_dictionary.md"))
        self._validate_and_write_summary(output_dir)
        self._write_manifest(output_dir)
        print(f"All files exported successfully to '{output_dir}/'.")

    def _fieldnames(self, name):
        known = {
            "suppliers": ["supplier_id", "name", "iso_accredited", "country"],
            "instrument_types": ["type_id", "type_name", "measurement_unit", "default_interval_days", "tolerance_limit"],
            "calibration_plans": ["plan_id", "type_id", "interval_days", "grace_period_days", "policy"],
            "assets": ["asset_id", "type_id", "plan_id", "serial_number", "status", "commissioned_date", "last_calibration_date", "next_due_date"],
            "calibration_events": ["calibration_id", "asset_id", "supplier_id", "event_date", "result", "measurement_value", "measurement_unit", "measured_error", "due_date_calculated", "event_status"],
            "certificates": ["certificate_id", "calibration_id", "asset_id", "issued_date", "valid_from", "valid_until", "certificate_status"],
            "work_orders": ["work_order_id", "asset_id", "calibration_id", "issue_description", "corrective_action", "impact_assessment", "opened_at", "downtime_start", "downtime_end", "downtime_hours", "status"],
            "production_uses": ["use_id", "asset_id", "use_timestamp", "applicable_calibration_id", "flagged_overdue", "use_decision", "exception_applied", "exception_id"],
            "calibration_extensions": ["extension_id", "asset_id", "calibration_id", "original_due_date", "extended_due_date", "extension_days", "reason", "approved_by", "approval_status", "approved_at"],
            "approved_exceptions": ["exception_id", "asset_id", "calibration_id", "original_due_date", "extended_due_date", "extension_days", "reason", "approved_by", "approval_status", "approved_at"],
            "anomaly_findings": ["finding_id", "ground_truth_id", "entity_type", "entity_id", "issue_type", "details", "expected_decision", "finding_status"],
            "alerts": ["alert_id", "asset_id", "entity_type", "entity_id", "alert_type", "severity", "description", "status", "created_at"],
            "audit_records": ["audit_id", "entity_type", "entity_id", "action", "from_state", "to_state", "timestamp"],
            "ground_truth": ["ground_truth_id", "entity_type", "entity_id", "issue_type", "details", "expected_decision"]
        }
        return known[name]

    def _export_sql(self, path, datasets):
        # SQLite-compatible SQL export with PK/FK constraints. The certificate asset FK
        # stays valid for the deliberate mismatch; validation checks the business join separately.
        connection = sqlite3.connect(":memory:")
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript("""
                CREATE TABLE suppliers (supplier_id TEXT PRIMARY KEY, name TEXT NOT NULL, iso_accredited INTEGER NOT NULL, country TEXT NOT NULL);
                CREATE TABLE instrument_types (type_id TEXT PRIMARY KEY, type_name TEXT NOT NULL UNIQUE, measurement_unit TEXT NOT NULL, default_interval_days INTEGER NOT NULL CHECK(default_interval_days > 0), tolerance_limit REAL NOT NULL);
                CREATE TABLE calibration_plans (plan_id TEXT PRIMARY KEY, type_id TEXT NOT NULL REFERENCES instrument_types(type_id), interval_days INTEGER NOT NULL CHECK(interval_days > 0), grace_period_days INTEGER NOT NULL CHECK(grace_period_days >= 0), policy TEXT NOT NULL);
                CREATE TABLE assets (asset_id TEXT PRIMARY KEY, type_id TEXT NOT NULL REFERENCES instrument_types(type_id), plan_id TEXT NOT NULL REFERENCES calibration_plans(plan_id), serial_number TEXT NOT NULL UNIQUE, status TEXT NOT NULL CHECK(status IN ('ACTIVE','MAINTENANCE','RETIRED')), commissioned_date TEXT NOT NULL, last_calibration_date TEXT, next_due_date TEXT);
                CREATE TABLE calibration_events (calibration_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(asset_id), supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id), event_date TEXT NOT NULL, result TEXT NOT NULL CHECK(result IN ('PASS','FAIL')), measurement_value REAL NOT NULL, measurement_unit TEXT NOT NULL, measured_error REAL NOT NULL, due_date_calculated TEXT NOT NULL, event_status TEXT NOT NULL CHECK(event_status IN ('COMPLETED')));
                CREATE TABLE certificates (certificate_id TEXT PRIMARY KEY, calibration_id TEXT NOT NULL UNIQUE REFERENCES calibration_events(calibration_id), asset_id TEXT NOT NULL REFERENCES assets(asset_id), issued_date TEXT NOT NULL, valid_from TEXT NOT NULL, valid_until TEXT NOT NULL, certificate_status TEXT NOT NULL);
                CREATE TABLE work_orders (work_order_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(asset_id), calibration_id TEXT NOT NULL REFERENCES calibration_events(calibration_id), issue_description TEXT NOT NULL, corrective_action TEXT NOT NULL, impact_assessment TEXT NOT NULL, opened_at TEXT NOT NULL, downtime_start TEXT NOT NULL, downtime_end TEXT NOT NULL, downtime_hours INTEGER NOT NULL CHECK(downtime_hours >= 0), status TEXT NOT NULL CHECK(status IN ('OPEN','IN_PROGRESS','COMPLETED')));
                CREATE TABLE calibration_extensions (extension_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(asset_id), calibration_id TEXT NOT NULL REFERENCES calibration_events(calibration_id), original_due_date TEXT NOT NULL, extended_due_date TEXT NOT NULL, extension_days INTEGER NOT NULL CHECK(extension_days > 0), reason TEXT NOT NULL, approved_by TEXT NOT NULL, approval_status TEXT NOT NULL CHECK(approval_status IN ('APPROVED','REJECTED','PENDING')), approved_at TEXT NOT NULL);
                CREATE TABLE approved_exceptions (exception_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(asset_id), calibration_id TEXT NOT NULL REFERENCES calibration_events(calibration_id), original_due_date TEXT NOT NULL, extended_due_date TEXT NOT NULL, extension_days INTEGER NOT NULL CHECK(extension_days > 0), reason TEXT NOT NULL, approved_by TEXT NOT NULL, approval_status TEXT NOT NULL CHECK(approval_status IN ('APPROVED','REJECTED','PENDING')), approved_at TEXT NOT NULL);
                CREATE TABLE production_uses (use_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(asset_id), use_timestamp TEXT NOT NULL, applicable_calibration_id TEXT REFERENCES calibration_events(calibration_id), flagged_overdue INTEGER NOT NULL CHECK(flagged_overdue IN (0,1)), use_decision TEXT NOT NULL, exception_applied INTEGER NOT NULL CHECK(exception_applied IN (0,1)), exception_id TEXT REFERENCES approved_exceptions(exception_id));
                CREATE TABLE alerts (alert_id TEXT PRIMARY KEY, asset_id TEXT REFERENCES assets(asset_id), entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, alert_type TEXT NOT NULL, severity TEXT NOT NULL CHECK(severity IN ('LOW','MEDIUM','HIGH')), description TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('OPEN','ACKNOWLEDGED','RESOLVED')), created_at TEXT NOT NULL);
                CREATE TABLE audit_records (audit_id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, action TEXT NOT NULL, from_state TEXT, to_state TEXT, timestamp TEXT NOT NULL);
                CREATE TABLE ground_truth (ground_truth_id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, issue_type TEXT NOT NULL, details TEXT NOT NULL, expected_decision TEXT NOT NULL);
                CREATE TABLE anomaly_findings (finding_id TEXT PRIMARY KEY, ground_truth_id TEXT NOT NULL REFERENCES ground_truth(ground_truth_id), entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, issue_type TEXT NOT NULL, details TEXT NOT NULL, expected_decision TEXT NOT NULL, finding_status TEXT NOT NULL);
            """)
            insert_order = ["suppliers", "instrument_types", "calibration_plans", "assets", "calibration_events", "certificates", "work_orders", "calibration_extensions", "approved_exceptions", "ground_truth", "anomaly_findings", "production_uses", "alerts", "audit_records"]
            for name in insert_order:
                rows = datasets[name]
                if not rows:
                    continue
                columns = list(rows[0].keys())
                placeholders = ",".join("?" for _ in columns)
                query = f"INSERT INTO {name} ({','.join(columns)}) VALUES ({placeholders})"
                calibration_id_set = {c["calibration_id"] for c in self.calibration_events}
                batch = []
                for row in rows:
                    values = []
                    for column in columns:
                        value = row.get(column)
                        if isinstance(value, bool):
                            value = int(value)
                        values.append(value if value != "" else None)
                    # Certificate gaps are expected; no row is inserted for them.
                    if name == "production_uses" and row.get("applicable_calibration_id") not in calibration_id_set:
                        values[columns.index("applicable_calibration_id")] = None
                    batch.append(values)
                connection.executemany(query, batch)
            with open(path, "w", encoding="utf-8") as f:
                f.write("-- SQLite-compatible seed export generated by generator.py\n")
                f.write("PRAGMA foreign_keys = ON;\nBEGIN TRANSACTION;\nPRAGMA defer_foreign_keys = ON;\n")
                dump_lines = list(connection.iterdump())
                create_lines = [line for line in dump_lines if line.startswith("CREATE TABLE")]
                insert_lines = [line for line in dump_lines if line.startswith("INSERT INTO")]
                other_lines = [line for line in dump_lines if line.startswith("CREATE INDEX")]
                for line in create_lines + other_lines + insert_lines:
                    f.write(line + "\n")
                f.write("COMMIT;\n")
        finally:
            connection.close()

    def _export_schema(self, path):
        schema = {
            "project": "Equipment Calibration Management System",
            "seed": self.seed,
            "date_range": {"start": self._date(self.start_date), "end": self._date(self.end_date)},
            "entities": {
                "Asset": {"table": "assets", "primary_key": "asset_id", "relationships": ["InstrumentType 1:N Asset", "CalibrationPlan 1:N Asset"]},
                "InstrumentType": {"table": "instrument_types", "primary_key": "type_id"},
                "CalibrationPlan": {"table": "calibration_plans", "primary_key": "plan_id", "foreign_keys": ["type_id -> instrument_types.type_id"]},
                "CalibrationEvent": {"table": "calibration_events", "primary_key": "calibration_id", "foreign_keys": ["asset_id -> assets.asset_id", "supplier_id -> suppliers.supplier_id"]},
                "Certificate": {"table": "certificates", "primary_key": "certificate_id", "foreign_keys": ["calibration_id -> calibration_events.calibration_id", "asset_id -> assets.asset_id"], "cardinality": "one certificate per certified calibration; certificate gaps are explicitly labelled"},
                "WorkOrder": {"table": "work_orders", "primary_key": "work_order_id", "foreign_keys": ["asset_id -> assets.asset_id", "calibration_id -> calibration_events.calibration_id"]},
                "ProductionUse": {"table": "production_uses", "primary_key": "use_id", "foreign_keys": ["asset_id -> assets.asset_id", "applicable_calibration_id -> calibration_events.calibration_id (optional)"]},
                "Supplier": {"table": "suppliers", "primary_key": "supplier_id"},
                "Alert": {"table": "alerts", "primary_key": "alert_id", "foreign_keys": ["entity_id is polymorphic and documented by entity_type"]},
                "AuditRecord": {"table": "audit_records", "primary_key": "audit_id", "foreign_keys": ["entity_id is polymorphic and documented by entity_type"]},
                "CalibrationExtension": {"table": "calibration_extensions", "primary_key": "extension_id", "foreign_keys": ["asset_id -> assets.asset_id", "calibration_id -> calibration_events.calibration_id"]},
                "ApprovedException": {"table": "approved_exceptions", "primary_key": "exception_id", "foreign_keys": ["asset_id -> assets.asset_id", "calibration_id -> calibration_events.calibration_id"]},
                "AnomalyFinding": {"table": "anomaly_findings", "primary_key": "finding_id", "foreign_keys": ["ground_truth_id -> ground_truth.ground_truth_id"]},
                "GroundTruth": {"table": "ground_truth", "primary_key": "ground_truth_id", "purpose": "evaluation labels only; exclude from input features"}
            },
            "lifecycle_states": {"asset": ["ACTIVE", "MAINTENANCE", "RETIRED"], "calibration_result": ["PASS", "FAIL"], "work_order": ["OPEN", "IN_PROGRESS", "COMPLETED"], "alert": ["OPEN", "ACKNOWLEDGED", "RESOLVED"]},
            "business_rules": [
                "due_date = calibration event date + plan interval_days",
                "a production use after effective due date is blocked unless an approved extension is in force",
                "a failed calibration requires corrective action and impact assessment",
                "certificate asset_id must match the asset_id on its calibration event",
                "ground_truth is kept separate from source event tables"
            ]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, sort_keys=True)
            f.write("\n")

    def _export_data_dictionary(self, path):
        descriptions = {
            "suppliers": "Supplier master records. supplier_id is unique; iso_accredited is boolean.",
            "instrument_types": "Instrument classes. default_interval_days is a positive number of days; measurement units are explicit.",
            "calibration_plans": "Calibration policy by instrument type. interval_days > 0; grace_period_days >= 0; policy is BLOCK_OVERDUE_USE.",
            "assets": "Instrument register. status is ACTIVE, MAINTENANCE, or RETIRED; type_id and plan_id must reference parent records.",
            "calibration_events": "Calibration event history. result is PASS or FAIL; due_date_calculated is event date plus plan interval except labelled anomaly.",
            "certificates": "Certificate evidence. calibration_id is unique; asset_id must match its calibration event except the labelled mismatch.",
            "work_orders": "Corrective action and downtime. failed baseline calibrations have corrective_action and impact_assessment; the labelled exception is intentionally missing.",
            "production_uses": "Use events within the 2025 one-year window, plus a labelled expired-use edge case. flagged_overdue is derived from event history and approved extensions.",
            "calibration_extensions": "Calibration extension source records; original due dates remain unchanged and extended_due_date is explicit.",
            "approved_exceptions": "Approved exception records referenced by production uses; only approved records may authorize use past original due date.",
            "anomaly_findings": "Finding records linked to ground_truth by ground_truth_id; every finding has a primary key.",
            "alerts": "Derived operational alerts; severity is LOW, MEDIUM, or HIGH; status is OPEN, ACKNOWLEDGED, or RESOLVED.",
            "audit_records": "Append-only record of creation and injected state changes; timestamps are ISO-like date/time strings.",
            "ground_truth": "Separate known-anomaly labels and expected decisions; never use as model input features."
        }
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Data Dictionary\n\n")
            f.write("All records are synthetic. Dates use `YYYY-MM-DD`; timestamps use `YYYY-MM-DD HH:MM:SS`. IDs are immutable strings. Empty optional foreign keys are exported as blank CSV values and NULL in SQL.\n\n")
            for name, description in descriptions.items():
                f.write(f"## `{name}`\n\n{description}\n\n")
                rows = self._datasets()[name]
                fields = list(rows[0].keys()) if rows else self._fieldnames(name)
                f.write("| Field | Type | Required | Validation / meaning |\n|---|---|---|---|\n")
                for field in fields:
                    value = next((row.get(field) for row in rows if row.get(field) not in (None, "")), None)
                    if field.endswith("_id") or field in {"type_id", "plan_id", "supplier_id", "asset_id", "calibration_id", "certificate_id", "work_order_id", "use_id", "extension_id", "alert_id", "audit_id", "ground_truth_id"}:
                        typ = "string ID"
                    elif isinstance(value, bool):
                        typ = "boolean"
                    elif isinstance(value, int):
                        typ = "integer"
                    elif isinstance(value, float):
                        typ = "number"
                    elif field.endswith("_date") or field in {"event_date", "use_timestamp", "issued_date", "valid_from", "valid_until", "created_at", "timestamp", "opened_at", "downtime_start", "downtime_end", "approved_at"}:
                        typ = "date/time string"
                    else:
                        typ = "string / enum"
                    optional = field in {"last_calibration_date", "next_due_date", "applicable_calibration_id", "from_state", "to_state"} or (name == "production_uses" and field == "applicable_calibration_id")
                    required = "Optional" if optional else "Required"
                    rule = "Unique primary key" if field in {"supplier_id", "type_id", "plan_id", "asset_id", "calibration_id", "certificate_id", "work_order_id", "use_id", "extension_id", "alert_id", "audit_id", "ground_truth_id"} else "See business rules and schema.json"
                    f.write(f"| `{field}` | {typ} | {required} | {rule} |\n")
                f.write("\n")
            f.write("## Relationships and cardinality\n\n")
            f.write("- InstrumentType 1:N Asset; InstrumentType 1:N CalibrationPlan.\n- CalibrationPlan 1:N Asset.\n- Asset 1:N CalibrationEvent and 1:N ProductionUse.\n- Supplier 1:N CalibrationEvent.\n- CalibrationEvent 0:1 Certificate (certificate gaps are labelled), 0:N WorkOrder, and 0:N CalibrationExtension/ApprovedException.\n- ProductionUse optionally references one ApprovedException.\n- AnomalyFinding N:1 GroundTruth through ground_truth_id.\n- Alert and AuditRecord use a polymorphic entity_type/entity_id pair; alert asset_id is an optional FK to Asset.\n- GroundTruth is a separate evaluation-label table, not an input feature.\n")

    def _validate_and_write_summary(self, output_dir):
        datasets = self._datasets()
        errors = []
        warnings = []
        expected_issues = {x["issue_type"] for x in self.ground_truth}

        pk_fields = {
            "suppliers": "supplier_id", "instrument_types": "type_id", "calibration_plans": "plan_id",
            "assets": "asset_id", "calibration_events": "calibration_id", "certificates": "certificate_id",
            "work_orders": "work_order_id", "production_uses": "use_id", "calibration_extensions": "extension_id",
            "alerts": "alert_id", "audit_records": "audit_id", "ground_truth": "ground_truth_id",
            "approved_exceptions": "exception_id", "anomaly_findings": "finding_id"
        }
        for name, field in pk_fields.items():
            values = [row[field] for row in datasets[name]]
            if len(values) != len(set(values)):
                errors.append(f"Duplicate primary keys in {name}.{field}")

        supplier_ids = {x["supplier_id"] for x in self.suppliers}
        type_ids = {x["type_id"] for x in self.instrument_types}
        plan_ids = {x["plan_id"] for x in self.calibration_plans}
        asset_ids = {x["asset_id"] for x in self.assets}
        calibration_ids = {x["calibration_id"] for x in self.calibration_events}
        certificate_ids = {x["certificate_id"] for x in self.certificates}
        for a in self.assets:
            if a["type_id"] not in type_ids or a["plan_id"] not in plan_ids:
                errors.append(f"Asset has invalid parent reference: {a['asset_id']}")
        for c in self.calibration_events:
            if c["asset_id"] not in asset_ids or c["supplier_id"] not in supplier_ids:
                errors.append(f"Calibration has invalid parent reference: {c['calibration_id']}")
        calibration_by_id = {c["calibration_id"]: c for c in self.calibration_events}
        asset_by_id = {a["asset_id"]: a for a in self.assets}
        # Validate certificate foreign keys and asset relationship. Only the
        # exact certificate intentionally labelled as anomalous may mismatch.
        labelled_mismatch_ids = {
            item["entity_id"]
            for item in self.ground_truth
            if item["issue_type"] == "CERTIFICATE_ASSET_MISMATCH"
        }
        for cert in self.certificates:
            if cert["calibration_id"] not in calibration_ids or cert["asset_id"] not in asset_ids:
                errors.append(f"Certificate has invalid FK: {cert['certificate_id']}")
            event = calibration_by_id.get(cert["calibration_id"])
            if (
                event
                and event["asset_id"] != cert["asset_id"]
                and cert["certificate_id"] not in labelled_mismatch_ids
            ):
                errors.append(f"Unexpected certificate asset mismatch: {cert['certificate_id']}")
        for use in self.production_uses:
            if use["asset_id"] not in asset_ids:
                errors.append(f"Production use has invalid asset FK: {use['use_id']}")
            if use["applicable_calibration_id"] and use["applicable_calibration_id"] not in calibration_ids:
                errors.append(f"Production use has invalid calibration FK: {use['use_id']}")
        for wo in self.work_orders:
            if wo["asset_id"] not in asset_ids or wo["calibration_id"] not in calibration_ids:
                errors.append(f"Work order has invalid FK: {wo['work_order_id']}")
        exception_ids = {e["extension_id"] for e in self.calibration_extensions}
        for extension in self.calibration_extensions:
            if extension["asset_id"] not in asset_ids or extension["calibration_id"] not in calibration_ids:
                errors.append(f"Calibration extension has invalid FK: {extension['extension_id']}")
        for use in self.production_uses:
            if use.get("exception_id") and use["exception_id"] not in exception_ids:
                errors.append(f"Production use has invalid exception FK: {use['use_id']}")
        ground_truth_ids = {x["ground_truth_id"] for x in self.ground_truth}
        for finding in datasets["anomaly_findings"]:
            if finding["ground_truth_id"] not in ground_truth_ids:
                errors.append(f"Anomaly finding has invalid ground-truth FK: {finding['finding_id']}")
        for alert in self.alerts:
            if alert.get("asset_id") and alert["asset_id"] not in asset_ids:
                errors.append(f"Alert has invalid asset FK: {alert['alert_id']}")

        # Verify due-date arithmetic, excluding the deliberately injected inconsistent date.
        for cal in self.calibration_events:
            if cal["calibration_id"] in {x["entity_id"] for x in self.ground_truth if x["issue_type"] == "DUE_DATE_INCONSISTENT_WITH_PLAN"}:
                continue
            asset = asset_by_id[cal["asset_id"]]
            plan = next(p for p in self.calibration_plans if p["plan_id"] == asset["plan_id"])
            event_date = datetime.strptime(cal["event_date"], TIMESTAMP_FORMAT)
            expected_due = self._date(event_date + timedelta(days=plan["interval_days"]))
            if cal["due_date_calculated"] != expected_due:
                errors.append(f"Incorrect due date: {cal['calibration_id']}")

        # Validate failed calibrations; only the one explicitly labelled exception may lack assessment.
        wo_by_cal = {w["calibration_id"]: w for w in self.work_orders}
        intentional_missing = {x["entity_id"] for x in self.ground_truth if x["issue_type"] == "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT"}
        for cal in self.calibration_events:
            if cal["result"] == "FAIL" and cal["calibration_id"] not in intentional_missing:
                wo = wo_by_cal.get(cal["calibration_id"])
                if not wo or not wo["corrective_action"] or not wo["impact_assessment"]:
                    errors.append(f"Failed calibration missing corrective action/impact assessment: {cal['calibration_id']}")

        required_edge_cases = {
            "DUE_DATE_INCONSISTENT_WITH_PLAN",
            "EXPIRED_INSTRUMENT_USED_WITHOUT_EXCEPTION",
            "CERTIFICATE_ASSET_MISMATCH",
            "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT"
        }
        missing_cases = required_edge_cases - expected_issues
        if missing_cases:
            errors.append("Missing required edge cases: " + ", ".join(sorted(missing_cases)))

        # Check that the injected expired-use record is flagged and blocked.
        for issue in self.ground_truth:
            if issue["issue_type"] == "EXPIRED_INSTRUMENT_USED_WITHOUT_EXCEPTION":
                use = next((u for u in self.production_uses if u["use_id"] == issue["entity_id"]), None)
                if not use or not use["flagged_overdue"] or use["exception_applied"] or use["use_decision"] != "BLOCKED_OVERDUE":
                    errors.append("Expired-use edge case is not correctly flagged/blocked")

        counts = {name: len(rows) for name, rows in datasets.items()}
        lines = [
            "EQUIPMENT CALIBRATION MANAGEMENT SYSTEM - VALIDATION SUMMARY",
            f"Seed: {self.seed}",
            f"Generation period: {self._date(self.start_date)} through {self._date(self.end_date)}",
            "",
            "ROW COUNTS"
        ]
        lines.extend(f"{name}: {count}" for name, count in counts.items())
        lines += ["", "VALIDATION CHECKS", f"Primary-key uniqueness: {'PASS' if not any('Duplicate primary keys' in e for e in errors) else 'FAIL'}",
                  f"Foreign-key integrity (except documented business mismatch): {'PASS' if not any('invalid' in e.lower() or 'invalid FK' in e for e in errors) else 'FAIL'}",
                  f"Due-date arithmetic (excluding labelled anomaly): {'PASS' if not any('Incorrect due date' in e for e in errors) else 'FAIL'}",
                  f"Failed-calibration corrective actions: {'PASS' if not any('Failed calibration missing' in e for e in errors) else 'FAIL'}",
                  f"Required edge-case coverage: {'PASS' if not missing_cases else 'FAIL'}",
                  f"Overall validation: {'PASS' if not errors else 'FAIL'}", "", "DOCUMENTED EDGE CASES"]
        lines.extend(f"{x['issue_type']}: {x['entity_id']} — {x['details']}" for x in self.ground_truth)
        if errors:
            lines += ["", "ERRORS"] + [f"- {error}" for error in errors]
        if warnings:
            lines += ["", "WARNINGS"] + [f"- {warning}" for warning in warnings]
        with open(os.path.join(output_dir, "validation_summary.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        if errors:
            raise ValueError("Validation failed. See validation_summary.txt: " + "; ".join(errors[:10]))

    def _write_manifest(self, output_dir):
        manifest = {
            "project": "Equipment Calibration Management System",
            "seed": self.seed,
            "date_range": {"start": self._date(self.start_date), "end": self._date(self.end_date)},
            "generator": "generator_fixed_corrected.py",
            "files": {}
        }
        for filename in sorted(os.listdir(output_dir)):
            path = os.path.join(output_dir, filename)
            if not os.path.isfile(path) or filename == "manifest.json":
                continue
            with open(path, "rb") as f:
                content = f.read()
            entry = {"size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
            if filename.endswith(".csv"):
                with open(path, newline="", encoding="utf-8") as f:
                    entry["row_count"] = sum(1 for _ in csv.DictReader(f))
            manifest[filename] = entry
            manifest["files"][filename] = entry
        with open(os.path.join(output_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
            f.write("\n")

    def compute_checksums(self, output_dir="output"):
        checksums = {}
        for filename in sorted(os.listdir(output_dir)):
            path = os.path.join(output_dir, filename)
            if os.path.isfile(path) and filename != "manifest.json":
                with open(path, "rb") as f:
                    checksums[filename] = hashlib.sha256(f.read()).hexdigest()
        return checksums


def main():
    parser = argparse.ArgumentParser(description="Generate deterministic calibration datasets.")
    parser.add_argument("--scale", choices=("starter", "full", "custom"), default="full",
                        help="starter uses smaller counts; full uses challenge baseline volumes")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--assets", type=int, default=None)
    parser.add_argument("--calibrations", type=int, default=None)
    parser.add_argument("--uses", type=int, default=None)
    parser.add_argument("--output", default=None, help="Output directory; by default writes output_run1 and output_run2")
    args = parser.parse_args()

    if args.scale == "starter":
        defaults = (100, 250, 5000)
    else:
        defaults = (2000, 5000, 100000)
    num_assets = args.assets if args.assets is not None else defaults[0]
    num_calibrations = args.calibrations if args.calibrations is not None else defaults[1]
    num_uses = args.uses if args.uses is not None else defaults[2]
    if min(num_assets, num_calibrations, num_uses) < 1:
        parser.error("assets, calibrations and uses must all be positive integers")

    if args.output:
        generator = DataGenerator(seed=args.seed, num_assets=num_assets,
                                  num_calibrations=num_calibrations, num_uses=num_uses)
        generator.generate_all()
        generator.export_data(args.output)
        print(f"Generated scale={args.scale}, assets={num_assets}, calibrations={num_calibrations}, uses={num_uses}")
        return

    print("--- FIRST GENERATION RUN ---")
    gen1 = DataGenerator(seed=args.seed, num_assets=num_assets,
                         num_calibrations=num_calibrations, num_uses=num_uses)
    gen1.generate_all()
    gen1.export_data("output_run1")
    checksums1 = gen1.compute_checksums("output_run1")

    print("\n--- SECOND GENERATION RUN (REPRODUCIBILITY CHECK) ---")
    gen2 = DataGenerator(seed=args.seed, num_assets=num_assets,
                         num_calibrations=num_calibrations, num_uses=num_uses)
    gen2.generate_all()
    gen2.export_data("output_run2")
    checksums2 = gen2.compute_checksums("output_run2")

    print("\n--- REPRODUCIBILITY VALIDATION ---")
    all_files = sorted(set(checksums1) | set(checksums2))
    match = True
    for filename in all_files:
        first = checksums1.get(filename)
        second = checksums2.get(filename)
        if first is not None and first == second:
            print(f"PASS {filename}: SHA-256 MATCH ({first})")
        else:
            print(f"FAIL {filename}: missing or different ({first} vs {second})")
            match = False
    if not match:
        raise SystemExit("Reproducibility validation failed.")
    print("\nSUCCESS: All generated files are reproducible.")


if __name__ == "__main__":
    main()