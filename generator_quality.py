
import os
import csv
import json
import random
import hashlib
import sqlite3
import argparse
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
        failed_at = datetime.strptime(
            calibration["event_date"], TIMESTAMP_FORMAT
        )
        downtime_start = failed_at + timedelta(hours=1)
        downtime_hours = self.random.randint(2, 24)
        downtime_end = downtime_start + timedelta(hours=downtime_hours)

        # Determine the final lifecycle state.
        status = ["OPEN", "IN_PROGRESS", "COMPLETED"][
            len(self.work_orders) % 3
        ]
        self.work_orders.append({
            "work_order_id": wo_id,
            "asset_id": calibration["asset_id"],
            "calibration_id": calibration["calibration_id"],
            "issue_description": "Failed tolerance verification",
            "corrective_action": (
                "Inspect instrument, adjust calibration, and perform verification"
            ),
            "impact_assessment": (
                "Review measurements produced since the last successful calibration"
            ),
            "opened_at": self._timestamp(failed_at),
            "downtime_start": self._timestamp(downtime_start),
            "downtime_end": self._timestamp(downtime_end),
            "downtime_hours": downtime_hours,
            "status": status
        })
        # Record creation in the OPEN state.
        transitions = [
            ("CREATED", "", "OPEN", failed_at)
        ] 
        # Record subsequent lifecycle transitions.
        if status in ("IN_PROGRESS", "COMPLETED"):
            transitions.append((
                "STARTED",
                "OPEN",
                "IN_PROGRESS",
                failed_at + timedelta(minutes=5)
            ))
        if status == "COMPLETED":
            transitions.append((
                "COMPLETED",
                "IN_PROGRESS",
                "COMPLETED",
                failed_at + timedelta(minutes=10)
            ))

        for action, from_state, to_state, transition_time in transitions:
            self.audit_records.append({
                "audit_id": f"AUD-{len(self.audit_records) + 1:06d}",
                "entity_type": "WorkOrder",
                "entity_id": wo_id,
                "action": action,
                "from_state": from_state,
                "to_state": to_state,
                "timestamp": self._timestamp(transition_time)
            })


    def _generate_extensions(self):
        plan_by_id = {
            p["plan_id"]: p for p in self.calibration_plans
        }
        candidates = []
        for calibration in self.calibration_events:
            if calibration["result"] != "PASS":
                continue
            asset = next(
                a for a in self.assets
                if a["asset_id"] == calibration["asset_id"]
            )
            plan = plan_by_id[asset["plan_id"]]
            grace_days = int(plan["grace_period_days"])
            original_due = datetime.strptime(
                calibration["due_date_calculated"],
                DATE_FORMAT
            )
            # Ensure the extension-use date falls within 2025.
            extension_use_date = original_due + timedelta(
                days=grace_days + 1
            )
            if extension_use_date <= self.end_date:
                candidates.append((calibration, original_due))
        self.random.shuffle(candidates)
        selected = candidates[:min(50, len(candidates))]
        for index, (calibration, original_due) in enumerate(selected):
            extension_days = self.random.choice([3, 7, 14])
            if index == 0:
                status = "APPROVED"
            elif index % 3 == 1:
                status = "PENDING"
            else:
                status = "REJECTED"
            extension = {
                "extension_id": f"EXT-{index + 1:06d}",
                "asset_id": calibration["asset_id"],
                "calibration_id": calibration["calibration_id"],
                "original_due_date": self._date(original_due),
                "extended_due_date": self._date(
                    original_due + timedelta(days=extension_days)
                ),
                "extension_days": extension_days,
                "reason": "Emergency production continuity extension",
                "requested_by": "ENGINEER-001",
                "requested_at": self._timestamp(
                    original_due - timedelta(days=3)
                ),
                "approval_status": status,
                "decided_by": "",
                "decision_reason": "",
                "decided_at": ""
            }
            if status == "APPROVED":
                extension["decided_by"] = "QUALITY-MANAGER-001"
                extension["decision_reason"] = (
                    "Emergency extension approved"
                )
                extension["decided_at"] = self._timestamp(
                    original_due - timedelta(days=1)
                )
            elif status == "REJECTED":
                extension["decided_by"] = "QUALITY-MANAGER-002"
                extension["decision_reason"] = (
                    "Extension rejected after review"
                )
                extension["decided_at"] = self._timestamp(
                    original_due - timedelta(days=1)
                )
            self.calibration_extensions.append(extension)

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
            return original_due, False
        extended = max(datetime.strptime(e["extended_due_date"], DATE_FORMAT) for e in extensions)
        return max(original_due, extended), True

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
                asset = next(a for a in self.assets if a["asset_id"] == asset_id)
                plan = next(p for p in self.calibration_plans if p["plan_id"] == asset["plan_id"])
                grace_days = int(plan["grace_period_days"])
                effective_due, extension_exists = self._effective_due_date(applicable["calibration_id"], due_date)
                normal_deadline = due_date + timedelta(days=grace_days)
                effective_deadline = effective_due + timedelta(days=grace_days)
                if use_time.date() <= normal_deadline.date():
                    decision = "ALLOWED_IN_CALIBRATION_WINDOW"
                    flagged_overdue = False
                elif extension_exists and use_time.date() <= effective_deadline.date():
                    decision = "ALLOWED_EXTENSION"
                    exception_applied = True
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
                "exception_applied": exception_applied
            })

    def _inject_edge_cases(self):
        # Ensure the approved-exception path is exercised by at least one use event.
        # Select an extension whose extension-only window falls inside the one-year use period.
        if len(self.production_uses) >= 2:
            plan_by_id = {p["plan_id"]: p for p in self.calibration_plans}
            extension_choice = None
            for ext in self.calibration_extensions:
                if ext["approval_status"] != "APPROVED":
                    continue
                asset = next((a for a in self.assets if a["asset_id"] == ext["asset_id"]), None)
                if not asset:
                    continue
                grace = int(plan_by_id[asset["plan_id"]]["grace_period_days"])
                original_due = datetime.strptime(ext["original_due_date"], DATE_FORMAT)
                extended_due = datetime.strptime(ext["extended_due_date"], DATE_FORMAT)
                use_date = original_due + timedelta(days=grace + 1)
                if use_date <= self.end_date and use_date <= extended_due + timedelta(days=grace):
                    extension_choice = (ext, use_date)
                    break
            if extension_choice:
                ext, use_date = extension_choice
                use_id = f"USE-{ext['asset_id']}-{use_date.strftime('%Y%m%d')}120000"
                while any(u["use_id"] == use_id for u in self.production_uses[:-1]):
                    use_date += timedelta(seconds=1)
                    use_id = f"USE-{ext['asset_id']}-{use_date.strftime('%Y%m%d%H%M%S')}"
                self.production_uses[-2] = {
                    "use_id": use_id, "asset_id": ext["asset_id"],
                    "use_timestamp": self._timestamp(use_date.replace(hour=12, minute=0, second=0)),
                    "applicable_calibration_id": ext["calibration_id"],
                    "flagged_overdue": False, "use_decision": "ALLOWED_EXTENSION",
                    "exception_applied": True
                }

        # Required case 1: due date inconsistent with the plan.
        if self.calibration_events:
            cal = self.calibration_events[0]
            cal["due_date_calculated"] = "2099-01-01"
            self._add_ground_truth("CalibrationEvent", cal["calibration_id"],
                                   "DUE_DATE_INCONSISTENT_WITH_PLAN",
                                   "Stored due date does not equal event date plus plan interval.",
                                   "FLAG_DUE_DATE_INCONSISTENCY")

        # Required case 2: expired instrument used without an exception.
        # Add an explicit use after the applicable calibration expiry, using an asset with a PASS event.
        pass_events = [c for c in self.calibration_events if c["result"] == "PASS"]
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
                "exception_applied": False
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

        # Required case 4: failed calibration with a traceable corrective work order but no impact assessment.
        if len(self.calibration_events) > 2:
            cal = self.calibration_events[2]
            cal["result"] = "FAIL"
            matching_orders = [w for w in self.work_orders if w["calibration_id"] == cal["calibration_id"]]
            if not matching_orders:
                self._create_work_order(cal, 3)
                matching_orders = [w for w in self.work_orders if w["calibration_id"] == cal["calibration_id"]]
            # Preserve the work-order and audit history; only the assessment is deliberately absent.
            for wo in matching_orders:
                wo["impact_assessment"] = ""

                previous_status = wo["status"]

                # Record the deliberate reopening in the audit history.
                if previous_status != "OPEN":
                    reopened_at = (
                        datetime.strptime(wo["opened_at"], TIMESTAMP_FORMAT)
                        + timedelta(minutes=15)
                    )

                    self.audit_records.append({
                        "audit_id": f"AUD-{len(self.audit_records) + 1:06d}",
                        "entity_type": "WorkOrder",
                        "entity_id": wo["work_order_id"],
                        "action": "REOPENED",
                        "from_state": previous_status,
                        "to_state": "OPEN",
                        "timestamp": self._timestamp(reopened_at)
                    })

                wo["status"] = "OPEN"
            self._add_ground_truth("CalibrationEvent", cal["calibration_id"],
                                   "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT",
                                   "Calibration failed and a corrective work order exists, but impact_assessment is missing.",
                                   "COMPLETE_IMPACT_ASSESSMENT_AND_REVIEW_AFFECTED_PRODUCTION")

    def _generate_audit_records(self):
        """Create one audit trail for calibrations, extensions and labelled anomalies."""
        # Calibration creation records.
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

        # Extension request and decision records: each extension is processed once.
        for extension in self.calibration_extensions:
            self.audit_records.append({
                "audit_id": f"AUD-{len(self.audit_records) + 1:06d}",
                "entity_type": "CalibrationExtension",
                "entity_id": extension["extension_id"],
                "action": "EXTENSION_REQUESTED",
                "from_state": "",
                "to_state": "PENDING",
                "timestamp": extension["requested_at"]
            })
            if extension["approval_status"] in {"APPROVED", "REJECTED"}:
                self.audit_records.append({
                    "audit_id": f"AUD-{len(self.audit_records) + 1:06d}",
                    "entity_type": "CalibrationExtension",
                    "entity_id": extension["extension_id"],
                    "action": (
                        "EXTENSION_APPROVED"
                        if extension["approval_status"] == "APPROVED"
                        else "EXTENSION_REJECTED"
                    ),
                    "from_state": "PENDING",
                    "to_state": extension["approval_status"],
                    "timestamp": extension["decided_at"]
                })

        # Record each deliberate edge case once.
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
            "alerts": self.alerts,
            "audit_records": self.audit_records,
            "ground_truth": self.ground_truth
        }

    def export_data(self, output_dir="output"):
        os.makedirs(output_dir, exist_ok=True)
        datasets = self._datasets()

        # Remove stale generated exports so the manifest describes this run only.
        expected_names = {f"{name}.csv" for name in datasets} | {"datasets.json", "ground_truth.json", "datasets.sql", "schema.json", "data_dictionary.md", "README.md", "validation_summary.txt", "manifest.json"}
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
        self._write_readme(os.path.join(output_dir, "README.md"))
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
            "production_uses": ["use_id", "asset_id", "use_timestamp", "applicable_calibration_id", "flagged_overdue", "use_decision", "exception_applied"],
            "calibration_extensions": [
                "extension_id", "asset_id", "calibration_id",
                "original_due_date", "extended_due_date", "extension_days",
                "reason", "requested_by", "requested_at",
                "approval_status", "decided_by", "decision_reason", "decided_at"
            ],
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
                CREATE TABLE work_orders (work_order_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(asset_id), calibration_id TEXT NOT NULL REFERENCES calibration_events(calibration_id), issue_description TEXT NOT NULL, corrective_action TEXT NOT NULL, impact_assessment TEXT, opened_at TEXT NOT NULL, downtime_start TEXT NOT NULL, downtime_end TEXT NOT NULL, downtime_hours INTEGER NOT NULL CHECK(downtime_hours >= 0), status TEXT NOT NULL CHECK(status IN ('OPEN','IN_PROGRESS','COMPLETED')));
                CREATE TABLE calibration_extensions (
                    extension_id TEXT PRIMARY KEY,
                    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
                    calibration_id TEXT NOT NULL REFERENCES calibration_events(calibration_id),
                    original_due_date TEXT NOT NULL,
                    extended_due_date TEXT NOT NULL,
                    extension_days INTEGER NOT NULL CHECK(extension_days > 0),
                    reason TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    approval_status TEXT NOT NULL
                        CHECK(approval_status IN ('APPROVED', 'REJECTED', 'PENDING')),
                    decided_by TEXT,
                    decision_reason TEXT,
                    decided_at TEXT
                );
                CREATE TABLE production_uses (use_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(asset_id), use_timestamp TEXT NOT NULL, applicable_calibration_id TEXT REFERENCES calibration_events(calibration_id), flagged_overdue INTEGER NOT NULL, use_decision TEXT NOT NULL, exception_applied INTEGER NOT NULL);
                CREATE TABLE alerts (alert_id TEXT PRIMARY KEY, asset_id TEXT, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, alert_type TEXT NOT NULL, severity TEXT NOT NULL CHECK(severity IN ('LOW','MEDIUM','HIGH')), description TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('OPEN','ACKNOWLEDGED','RESOLVED')), created_at TEXT NOT NULL);
                CREATE TABLE audit_records (audit_id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, action TEXT NOT NULL, from_state TEXT, to_state TEXT, timestamp TEXT NOT NULL);
                CREATE TABLE ground_truth (ground_truth_id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, issue_type TEXT NOT NULL, details TEXT NOT NULL, expected_decision TEXT NOT NULL);
            """)
            insert_order = ["suppliers", "instrument_types", "calibration_plans", "assets", "calibration_events", "certificates", "work_orders", "calibration_extensions", "production_uses", "alerts", "audit_records", "ground_truth"]
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
                f.write("-- SQLite-compatible seed export generated by generator_quality.py\n")
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
                "CalibrationExtension": {
                    "table": "calibration_extensions",
                    "primary_key": "extension_id",
                    "foreign_keys": ["asset_id -> assets.asset_id", "calibration_id -> calibration_events.calibration_id"],
                    "lifecycle": {
                        "states": ["PENDING", "APPROVED", "REJECTED"],
                        "request_fields": ["requested_by", "requested_at"],
                        "decision_fields": ["decided_by", "decision_reason", "decided_at"],
                        "rule": "Only APPROVED extensions affect production-use decisions"
                    }
                },
                "GroundTruth": {"table": "ground_truth", "primary_key": "ground_truth_id", "purpose": "evaluation labels only; exclude from input features"}
            },
            "lifecycle_states": {"asset": ["ACTIVE", "MAINTENANCE", "RETIRED"], "calibration_result": ["PASS", "FAIL"], "work_order": ["OPEN", "IN_PROGRESS", "COMPLETED"], "extension": ["PENDING", "APPROVED", "REJECTED"], "alert": ["OPEN", "ACKNOWLEDGED", "RESOLVED"]},
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
            "suppliers": "Supplier master records.",
            "instrument_types": "Instrument classes and measurement units.",
            "calibration_plans": "Calibration interval, grace period, and overdue-use policy by instrument type.",
            "assets": "Registered instruments; current calibration dates are derived from event history.",
            "calibration_events": "Immutable calibration history with measured result and plan-derived due date.",
            "certificates": "Calibration evidence; certificate gaps and asset mismatches are explicitly labelled.",
            "work_orders": "Corrective actions, impact assessment, lifecycle state, and downtime for failed calibrations.",
            "production_uses": "Production-use decisions derived from calibration history, grace periods, and approved extensions.",
            "calibration_extensions": "Emergency extension requests with request metadata, PENDING/APPROVED/REJECTED decisions, decision metadata, and immutable original due dates.",
            "alerts": "Operational alerts derived from failed calibrations, blocked uses, and labelled anomalies.",
            "audit_records": "Append-only history of record creation and deliberate edge-case injection.",
            "ground_truth": "Separate evaluation labels; exclude this dataset from model input features."
        }
        enum_rules = {
            ("assets", "status"): "ACTIVE | MAINTENANCE | RETIRED",
            ("calibration_events", "result"): "PASS | FAIL",
            ("calibration_events", "event_status"): "COMPLETED",
            ("calibration_plans", "policy"): "BLOCK_OVERDUE_USE",
            ("certificates", "certificate_status"): "VALID",
            ("work_orders", "status"): "OPEN | IN_PROGRESS | COMPLETED",
            ("calibration_extensions", "approval_status"): "APPROVED | REJECTED | PENDING",
            ("production_uses", "use_decision"): "ALLOWED_IN_CALIBRATION_WINDOW | ALLOWED_EXTENSION | BLOCKED_OVERDUE | BLOCKED_FAILED_CALIBRATION | REVIEW_NO_CALIBRATION",
            ("alerts", "severity"): "LOW | MEDIUM | HIGH",
            ("alerts", "status"): "OPEN | ACKNOWLEDGED | RESOLVED"
        }
        optional_fields = {
            ("assets", "last_calibration_date"), ("assets", "next_due_date"),
            ("production_uses", "applicable_calibration_id"),
            ("audit_records", "from_state"), ("audit_records", "to_state"),
            ("alerts", "asset_id")
        }
        unique_fields = {
            ("suppliers", "supplier_id"), ("instrument_types", "type_id"),
            ("calibration_plans", "plan_id"), ("assets", "asset_id"),
            ("assets", "serial_number"), ("calibration_events", "calibration_id"),
            ("certificates", "certificate_id"), ("certificates", "calibration_id"),
            ("work_orders", "work_order_id"), ("production_uses", "use_id"),
            ("calibration_extensions", "extension_id"), ("alerts", "alert_id"),
            ("audit_records", "audit_id"), ("ground_truth", "ground_truth_id")
        }
        positive_fields = {"interval_days", "default_interval_days", "extension_days", "downtime_hours"}
        nonnegative_fields = {"grace_period_days", "measurement_value", "measured_error", "tolerance_limit"}
        date_fields = {"commissioned_date", "last_calibration_date", "next_due_date", "issued_date", "valid_from", "valid_until", "original_due_date", "extended_due_date"}
        timestamp_fields = {"event_date", "use_timestamp", "requested_at", "decided_at", "opened_at", "downtime_start", "downtime_end", "created_at", "timestamp"}
        pk_fields = {
            "suppliers": "supplier_id", "instrument_types": "type_id", "calibration_plans": "plan_id",
            "assets": "asset_id", "calibration_events": "calibration_id", "certificates": "certificate_id",
            "work_orders": "work_order_id", "production_uses": "use_id", "calibration_extensions": "extension_id",
            "alerts": "alert_id", "audit_records": "audit_id", "ground_truth": "ground_truth_id"
        }
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Data Dictionary\n\n")
            f.write("All records are synthetic. Date fields use `YYYY-MM-DD`; timestamp fields use `YYYY-MM-DD HH:MM:SS`. IDs are immutable strings. Blank optional CSV references represent SQL NULL.\n\n")
            for name, description in descriptions.items():
                f.write(f"## `{name}`\n\n{description}\n\n")
                rows = self._datasets()[name]
                fields = list(rows[0].keys()) if rows else self._fieldnames(name)
                f.write("| Field | Type | Required | Allowed values / units | Uniqueness | Validation rule |\n")
                f.write("|---|---|---|---|---|---|\n")
                for field in fields:
                    value = next((row.get(field) for row in rows if row.get(field) not in (None, "")), None)
                    if field in date_fields:
                        typ = "date string"
                    elif field in timestamp_fields:
                        typ = "timestamp string"
                    elif isinstance(value, bool) or field in {"iso_accredited", "flagged_overdue", "exception_applied"}:
                        typ = "boolean (0/1 in SQL)"
                    elif isinstance(value, int) or field.endswith("_days") or field in {"downtime_hours", "default_interval_days", "interval_days", "grace_period_days"}:
                        typ = "integer"
                    elif isinstance(value, float) or field in {"measurement_value", "measured_error", "tolerance_limit"}:
                        typ = "decimal number"
                    else:
                        typ = "string"
                    required = "Optional" if (name, field) in optional_fields else "Required"
                    allowed = enum_rules.get((name, field), "Free text / identifier")
                    if field in {"measurement_value", "measured_error", "tolerance_limit"}:
                        allowed = "Numeric; measurement_value uses the instrument's measurement_unit; measured_error/tolerance_limit use the same unit"
                    elif field == "measurement_unit":
                        allowed = "PSI | Celsius | Nm | L/min | kg (from InstrumentType)"
                    elif field in {"interval_days", "default_interval_days", "extension_days"}:
                        allowed = "Positive whole days"
                    elif field == "grace_period_days":
                        allowed = "Zero or positive whole days"
                    elif field == "downtime_hours":
                        allowed = "Zero or positive whole hours; reconciles with downtime_start/end"
                    elif field in date_fields:
                        allowed = "YYYY-MM-DD"
                    elif field in timestamp_fields:
                        allowed = "YYYY-MM-DD HH:MM:SS"
                    elif field in {"iso_accredited", "flagged_overdue", "exception_applied"}:
                        allowed = "true/false (0/1 in SQL)"
                    uniqueness = "Primary key" if pk_fields.get(name) == field else ("Unique" if (name, field) in unique_fields else "Not unique")
                    rule = "Must be non-empty" if required == "Required" else "May be blank/NULL"
                    if field.endswith("_id") and field not in {"entity_id"}:
                        rule += "; referenced IDs must exist in the parent table where a declared FK applies"
                    if (name, field) in unique_fields:
                        rule += "; duplicates rejected"
                    if field in positive_fields:
                        rule += "; value > 0" if field != "downtime_hours" else "; value >= 0"
                    if field in nonnegative_fields:
                        rule += "; value >= 0"
                    if field == "due_date_calculated":
                        rule += "; equals event date + plan interval except the labelled due-date anomaly"
                    if field == "valid_until":
                        rule += "; must be on/after valid_from and issued_date; reconcile with derived plan due date"
                    if field == "approval_status":
                        rule += "; only APPROVED extensions affect use decisions"
                    if field == "ground_truth_id":
                        rule += "; evaluation-only, never an input feature"
                    f.write(f"| `{field}` | {typ} | {required} | {allowed} | {uniqueness} | {rule} |\n")
                f.write("\n")
            f.write("## Relationships and cardinality\n\n")
            f.write("- InstrumentType 1:N Asset; InstrumentType 1:N CalibrationPlan.\n")
            f.write("- CalibrationPlan 1:N Asset; each asset references one type and one plan.\n")
            f.write("- Asset 1:N CalibrationEvent and 1:N ProductionUse.\n")
            f.write("- Supplier 1:N CalibrationEvent.\n")
            f.write("- CalibrationEvent 0:1 Certificate (certificate gaps are intentionally labelled), 0:N WorkOrder, and 0:N CalibrationExtension.\n")
            f.write("- CalibrationExtension N:1 Asset and N:1 CalibrationEvent; only APPROVED records affect decisions.\n")
            f.write("- Alert and AuditRecord use entity_type/entity_id polymorphic references; their IDs are validated against the documented entity map.\n")
            f.write("- GroundTruth is kept in separate CSV/JSON exports and is not included in `datasets.json` input data.\n\n")
            f.write("## Business rules and derived values\n\n")
            f.write("1. `due_date_calculated = event_date + calibration_plans.interval_days`; one explicitly labelled edge case intentionally violates this.\n")
            f.write("2. Use decisions select the latest calibration event at or before use time. A failed latest calibration blocks use; no prior calibration requires review.\n")
            f.write("3. For a passing calibration, use is allowed through due date plus plan grace days. An approved extension may extend that deadline; use during the extension-only window is labelled `ALLOWED_EXTENSION`.\n")
            f.write("4. Failed calibrations require a corrective work order and impact assessment except for the one explicitly labelled negative scenario.\n")
            f.write("5. Certificate asset must match its calibration event; issue/validity dates must be chronologically consistent.\n")
            f.write("6. Downtime hours must equal the duration between downtime_start and downtime_end. Ground-truth labels describe deliberate exceptions and must not be silently repaired.\n")

    def _validate_and_write_summary(self, output_dir):
        datasets = self._datasets()
        errors = []
        warnings = []
        expected_issues = {x["issue_type"] for x in self.ground_truth}

        pk_fields = {
            "suppliers": "supplier_id", "instrument_types": "type_id", "calibration_plans": "plan_id",
            "assets": "asset_id", "calibration_events": "calibration_id", "certificates": "certificate_id",
            "work_orders": "work_order_id", "production_uses": "use_id", "calibration_extensions": "extension_id",
            "alerts": "alert_id", "audit_records": "audit_id", "ground_truth": "ground_truth_id"
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
        for cert in self.certificates:
            if cert["calibration_id"] not in calibration_ids or cert["asset_id"] not in asset_ids:
                errors.append(f"Certificate has invalid FK: {cert['certificate_id']}")
            event = calibration_by_id.get(cert["calibration_id"])
            if event and event["asset_id"] != cert["asset_id"] and "CERTIFICATE_ASSET_MISMATCH" not in expected_issues:
                errors.append(f"Unexpected certificate asset mismatch: {cert['certificate_id']}")
        for use in self.production_uses:
            if use["asset_id"] not in asset_ids:
                errors.append(f"Production use has invalid asset FK: {use['use_id']}")
            if use["applicable_calibration_id"] and use["applicable_calibration_id"] not in calibration_ids:
                errors.append(f"Production use has invalid calibration FK: {use['use_id']}")
        for wo in self.work_orders:
            if wo["asset_id"] not in asset_ids or wo["calibration_id"] not in calibration_ids:
                errors.append(f"Work order has invalid FK: {wo['work_order_id']}")

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
            if cal["result"] != "FAIL":
                continue
            wo = wo_by_cal.get(cal["calibration_id"])
            if cal["calibration_id"] in intentional_missing:
                if not wo or not wo["corrective_action"] or wo["impact_assessment"]:
                    errors.append(f"Labelled impact-assessment anomaly is not isolated correctly: {cal['calibration_id']}")
            elif not wo or not wo["corrective_action"] or not wo["impact_assessment"]:
                errors.append(f"Failed calibration missing corrective action/impact assessment: {cal['calibration_id']}")

        # Validate extension relationships, approval details, dates, and business limits.
        extension_ids = {e["extension_id"] for e in self.calibration_extensions}
        extension_by_cal = defaultdict(list)
        for ext in self.calibration_extensions:
            if ext["asset_id"] not in asset_ids or ext["calibration_id"] not in calibration_ids:
                errors.append(f"Extension has invalid parent reference: {ext['extension_id']}")
                continue

            cal = calibration_by_id[ext["calibration_id"]]
            if cal["asset_id"] != ext["asset_id"]:
                errors.append(f"Extension asset/calibration mismatch: {ext['extension_id']}")

            status = ext["approval_status"]
            if status not in {"APPROVED", "REJECTED", "PENDING"}:
                errors.append(f"Invalid extension approval status: {ext['extension_id']}")

            try:
                extension_days = int(ext["extension_days"])
                original = datetime.strptime(ext["original_due_date"], DATE_FORMAT)
                extended = datetime.strptime(ext["extended_due_date"], DATE_FORMAT)
                if extension_days <= 0:
                    errors.append(f"Invalid extension length: {ext['extension_id']}")
                if extended <= original or (extended - original).days != extension_days:
                    errors.append(f"Extension date arithmetic mismatch: {ext['extension_id']}")
            except (ValueError, TypeError):
                errors.append(f"Invalid extension date/length: {ext['extension_id']}")

            if not ext["reason"].strip():
                errors.append(f"Extension {ext['extension_id']} has no reason.")
            if not ext["requested_by"].strip():
                errors.append(f"Extension {ext['extension_id']} has no requestor.")

            try:
                requested_at = datetime.strptime(ext["requested_at"], TIMESTAMP_FORMAT)
            except (ValueError, TypeError):
                errors.append(f"Extension {ext['extension_id']} has invalid request timestamp.")
                requested_at = None

            if status == "PENDING":
                if ext["decided_by"] or ext["decision_reason"] or ext["decided_at"]:
                    errors.append(
                        f"Pending extension {ext['extension_id']} must not contain decision details."
                    )
            elif status in {"APPROVED", "REJECTED"}:
                if (
                    not ext["decided_by"].strip()
                    or not ext["decision_reason"].strip()
                    or not ext["decided_at"].strip()
                ):
                    errors.append(
                        f"Extension {ext['extension_id']} is missing decision details."
                    )
                else:
                    try:
                        decided_at = datetime.strptime(ext["decided_at"], TIMESTAMP_FORMAT)
                        if requested_at is not None and decided_at < requested_at:
                            errors.append(
                                f"Extension {ext['extension_id']} decision predates its request."
                            )
                        if status == "APPROVED" and decided_at.date() > original.date():
                            warnings.append(
                                f"Extension approved after original due date: {ext['extension_id']}"
                            )
                    except (ValueError, TypeError):
                        errors.append(
                            f"Extension {ext['extension_id']} has invalid decision timestamp."
                        )

            extension_by_cal[ext["calibration_id"]].append(ext)

        # Verify that all three lifecycle states are represented.
        extension_states = {ext["approval_status"] for ext in self.calibration_extensions}
        if self.calibration_extensions and extension_states != {"PENDING", "APPROVED", "REJECTED"}:
            errors.append(
                "Emergency extensions must demonstrate PENDING, APPROVED and REJECTED states."
            )

        # Validate certificate lifecycle/date ordering and event-to-certificate reconciliation.
        for cert in self.certificates:
            try:
                issued = datetime.strptime(cert["issued_date"], DATE_FORMAT)
                valid_from = datetime.strptime(cert["valid_from"], DATE_FORMAT)
                valid_until = datetime.strptime(cert["valid_until"], DATE_FORMAT)
                if valid_from > valid_until or issued > valid_until:
                    errors.append(f"Invalid certificate date ordering: {cert['certificate_id']}")
                event = calibration_by_id.get(cert["calibration_id"])
                if event and issued.date() < datetime.strptime(event["event_date"], TIMESTAMP_FORMAT).date():
                    errors.append(f"Certificate issued before calibration event: {cert['certificate_id']}")
                if event:
                    asset_for_cert = asset_by_id.get(event["asset_id"])
                    if asset_for_cert:
                        plan_for_cert = next(p for p in self.calibration_plans if p["plan_id"] == asset_for_cert["plan_id"])
                        derived_due = (datetime.strptime(event["event_date"], TIMESTAMP_FORMAT) + timedelta(days=int(plan_for_cert["interval_days"]))).date()
                        if valid_until.date() != derived_due:
                            errors.append(f"Certificate validity does not reconcile to plan due date: {cert['certificate_id']}")
            except (ValueError, TypeError):
                errors.append(f"Invalid certificate date format: {cert['certificate_id']}")

        # Validate work-order lifecycle, downtime arithmetic, and corrective-action traceability.
        allowed_wo_states = {"OPEN", "IN_PROGRESS", "COMPLETED"}
        for wo in self.work_orders:
            if wo["status"] not in allowed_wo_states:
                errors.append(f"Invalid work-order lifecycle state: {wo['work_order_id']}")
            try:
                opened = datetime.strptime(wo["opened_at"], TIMESTAMP_FORMAT)
                start = datetime.strptime(wo["downtime_start"], TIMESTAMP_FORMAT)
                end = datetime.strptime(wo["downtime_end"], TIMESTAMP_FORMAT)
                if start < opened or end < start:
                    errors.append(f"Invalid work-order date ordering: {wo['work_order_id']}")
                if (end - start).total_seconds() != int(wo["downtime_hours"]) * 3600:
                    errors.append(f"Downtime arithmetic mismatch: {wo['work_order_id']}")
            except (ValueError, TypeError):
                errors.append(f"Invalid work-order timestamp: {wo['work_order_id']}")

        # Validate alert lifecycle and polymorphic references against the entity's actual table.
        entity_ids = {
            "Asset": asset_ids, "CalibrationEvent": calibration_ids,
            "Certificate": certificate_ids, "WorkOrder": {w["work_order_id"] for w in self.work_orders},
            "ProductionUse": {u["use_id"] for u in self.production_uses},
            "CalibrationExtension": extension_ids, "Supplier": supplier_ids,
            "InstrumentType": type_ids, "CalibrationPlan": plan_ids
        }
        for alert in self.alerts:
            if alert["status"] not in {"OPEN", "ACKNOWLEDGED", "RESOLVED"}:
                errors.append(f"Invalid alert lifecycle state: {alert['alert_id']}")
            known = entity_ids.get(alert["entity_type"])
            if known is None:
                errors.append(f"Alert has unknown entity type: {alert['alert_id']}")
            elif alert["entity_id"] not in known:
                # A deliberately injected ground-truth alert can reference a certificate mismatch
                # and therefore still points to a real entity in the certificate table.
                errors.append(f"Alert points to missing entity: {alert['alert_id']}")
            if alert["asset_id"] and alert["asset_id"] not in asset_ids:
                errors.append(f"Alert has invalid asset reference: {alert['alert_id']}")

        # Audit IDs and lifecycle records must refer to an entity and use known actions.
        audit_entity_ids = {**entity_ids, "Supplier": supplier_ids, "InstrumentType": type_ids, "CalibrationPlan": plan_ids}
        for audit in self.audit_records:
            known = audit_entity_ids.get(audit["entity_type"])
            if known is None:
                errors.append(f"Audit record has unknown entity type: {audit['audit_id']}")
            elif audit["entity_id"] not in known:
                errors.append(f"Audit record points to missing entity: {audit['audit_id']}")
            if not audit["action"] or not audit["timestamp"]:
                errors.append(f"Audit record missing action/timestamp: {audit['audit_id']}")

        # Reconcile use decisions with the event history and exception policy. Skip only uses
        # whose linked calibration is one of the intentionally mutated edge-case records.
        special_cal_ids = {x["entity_id"] for x in self.ground_truth if x["entity_type"] == "CalibrationEvent"}
        plan_by_id = {p["plan_id"]: p for p in self.calibration_plans}
        extensions_by_cal = defaultdict(list)
        for ext in self.calibration_extensions:
            if ext["approval_status"] == "APPROVED":
                extensions_by_cal[ext["calibration_id"]].append(ext)
        for use in self.production_uses:
            cal_id = use["applicable_calibration_id"]
            if not cal_id or cal_id in special_cal_ids:
                continue
            cal = calibration_by_id.get(cal_id)
            if not cal:
                continue
            if cal["asset_id"] != use["asset_id"]:
                errors.append(f"Use/calibration asset mismatch: {use['use_id']}")
                continue
            if cal["result"] == "FAIL":
                expected_decision = "BLOCKED_FAILED_CALIBRATION"
            else:
                asset = asset_by_id[use["asset_id"]]
                plan = plan_by_id[asset["plan_id"]]
                original_due = datetime.strptime(cal["due_date_calculated"], DATE_FORMAT)
                use_date = datetime.strptime(use["use_timestamp"], TIMESTAMP_FORMAT).date()
                normal_deadline = (original_due + timedelta(days=int(plan["grace_period_days"]))).date()
                approved = extensions_by_cal.get(cal_id, [])
                extended_due = max((datetime.strptime(e["extended_due_date"], DATE_FORMAT) for e in approved), default=original_due)
                extended_deadline = (extended_due + timedelta(days=int(plan["grace_period_days"]))).date()
                if use_date <= normal_deadline:
                    expected_decision = "ALLOWED_IN_CALIBRATION_WINDOW"
                elif approved and use_date <= extended_deadline:
                    expected_decision = "ALLOWED_EXTENSION"
                else:
                    expected_decision = "BLOCKED_OVERDUE"
            if use["use_decision"] != expected_decision:
                errors.append(f"Use decision does not reconcile with policy: {use['use_id']}")
            expected_blocked = expected_decision.startswith("BLOCKED") or expected_decision == "REVIEW_NO_CALIBRATION"
            if bool(use["flagged_overdue"]) != expected_blocked:
                errors.append(f"Use overdue flag does not reconcile with decision: {use['use_id']}")
            if bool(use["exception_applied"]) != (expected_decision == "ALLOWED_EXTENSION"):
                errors.append(f"Use exception flag does not reconcile with decision: {use['use_id']}")

        required_edge_cases = {
            "DUE_DATE_INCONSISTENT_WITH_PLAN",
            "EXPIRED_INSTRUMENT_USED_WITHOUT_EXCEPTION",
            "CERTIFICATE_ASSET_MISMATCH",
            "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT"
        }
        missing_cases = required_edge_cases - expected_issues
        if missing_cases:
            errors.append("Missing required edge cases: " + ", ".join(sorted(missing_cases)))

        # Verify the exception workflow is not merely present in a table: at least one use must exercise it.
        if not any(u["use_decision"] == "ALLOWED_EXTENSION" and bool(u["exception_applied"]) for u in self.production_uses):
            errors.append("No production use exercises an approved emergency extension")

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
        decision_counts = Counter(use["use_decision"] for use in self.production_uses)
        lines += ["", "PRODUCTION-USE DECISION METRICS"]
        lines.extend(f"{decision}: {decision_counts.get(decision, 0)}" for decision in [
            "ALLOWED_IN_CALIBRATION_WINDOW", "ALLOWED_EXTENSION", "BLOCKED_OVERDUE",
            "BLOCKED_FAILED_CALIBRATION", "REVIEW_NO_CALIBRATION"
        ])
        lines.append(f"Approved-extension usage rate: {decision_counts.get('ALLOWED_EXTENSION', 0) / max(1, len(self.production_uses)):.4%}")
        lines.append(f"Blocked/review use rate: {(decision_counts.get('BLOCKED_OVERDUE', 0) + decision_counts.get('BLOCKED_FAILED_CALIBRATION', 0) + decision_counts.get('REVIEW_NO_CALIBRATION', 0)) / max(1, len(self.production_uses)):.4%}")
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

    def _write_readme(self, path):
        """Write reproducible setup, generation, export, and provenance instructions."""
        content = f"""# Equipment Calibration Management System — Synthetic Data Generator

## Purpose
This project generates a synthetic, traceable equipment-calibration lifecycle dataset. It models assets, instrument types, calibration plans and events, certificates, corrective work orders, production uses, emergency extensions, alerts, audit records, and separately stored evaluation ground truth.

## Requirements
- Python 3.10 or newer
- Python standard library only; no third-party packages are required

## Generate the full dataset
From the project directory, run:

```powershell
python generator_quality.py --profile full --seed {self.seed} --output-base .\quality_lifecycle
```

## Generate the starter dataset
```powershell
python generator_quality.py --profile starter --seed {self.seed} --output-base .\quality_lifecycle_starter
```

## Parameterize dataset size
```powershell
python generator_quality.py --assets 200 --calibrations 500 --uses 10000 --seed {self.seed} --output-base .\quality_lifecycle_custom
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
The synthetic event period is `{self._date(self.start_date)}` through `{self._date(self.end_date)}`. Identifier strings use the documented immutable entity prefixes and zero-padded counters. The `2026` segment in calibration/work-order identifiers is the configured identifier batch year in this generator; it is not the event timestamp year.

## Data provenance and licensing
All generated business records are synthetic and created locally by this generator. No external operational, personal, confidential, or restricted dataset is downloaded or redistributed. Public reference data is not required for generation.

## Validation and tests
Run the project tests with:

```powershell
python -m pytest -v
```

The generator itself also validates primary-key uniqueness, parent references, due-date calculations (excluding the labelled anomaly), certificate reconciliation, failed-calibration corrective actions, extension lifecycle details, use decisions, required edge-case coverage, and reproducibility.
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _write_manifest(self, output_dir):
        manifest = {
            "project": "Equipment Calibration Management System",
            "seed": self.seed,
            "date_range": {"start": self._date(self.start_date), "end": self._date(self.end_date)},
            "generator": "generator_quality.py",
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
    parser = argparse.ArgumentParser(description="Generate and validate synthetic equipment calibration data.")
    parser.add_argument("--profile", choices=("starter", "full"), default="full",
                        help="starter creates a small dataset; full creates challenge-scale data (default).")
    parser.add_argument("--seed", type=int, default=SEED, help="Fixed random seed (default: 20261022).")
    parser.add_argument("--assets", type=int, help="Override asset count.")
    parser.add_argument("--calibrations", type=int, help="Override calibration-event count.")
    parser.add_argument("--uses", type=int, help="Override production-use count.")
    parser.add_argument("--output-base", default=".", help="Directory in which output_run1 and output_run2 are created.")
    args = parser.parse_args()

    if args.profile == "starter":
        defaults = {"assets": 100, "calibrations": 250, "uses": 5000}
    else:
        defaults = {"assets": 2000, "calibrations": 5000, "uses": 100000}
    counts = {
        "assets": args.assets if args.assets is not None else defaults["assets"],
        "calibrations": args.calibrations if args.calibrations is not None else defaults["calibrations"],
        "uses": args.uses if args.uses is not None else defaults["uses"]
    }
    if counts["assets"] < 2 or counts["calibrations"] < 3 or counts["uses"] < 2:
        parser.error("assets must be >= 2, calibrations >= 3, and uses >= 2 so required edge cases can be generated")
    output_base = os.path.abspath(args.output_base)
    os.makedirs(output_base, exist_ok=True)
    out1 = os.path.join(output_base, "output_run1")
    out2 = os.path.join(output_base, "output_run2")

    print(f"Profile: {args.profile}; seed: {args.seed}; counts: {counts}")
    print("--- FIRST GENERATION RUN ---")
    gen1 = DataGenerator(seed=args.seed, num_assets=counts["assets"],
                         num_calibrations=counts["calibrations"], num_uses=counts["uses"])
    gen1.generate_all()
    gen1.export_data(out1)
    checksums1 = gen1.compute_checksums(out1)

    print("\n--- SECOND GENERATION RUN (REPRODUCIBILITY CHECK) ---")
    gen2 = DataGenerator(seed=args.seed, num_assets=counts["assets"],
                         num_calibrations=counts["calibrations"], num_uses=counts["uses"])
    gen2.generate_all()
    gen2.export_data(out2)
    checksums2 = gen2.compute_checksums(out2)

    print("\n--- REPRODUCIBILITY VALIDATION ---")
    all_files = sorted(set(checksums1) | set(checksums2))
    mismatches = []
    for filename in all_files:
        first, second = checksums1.get(filename), checksums2.get(filename)
        if first is None or first != second:
            mismatches.append(filename)
            print(f"FAIL {filename}: missing or different")
        else:
            print(f"PASS {filename}: SHA-256 MATCH")
    if not mismatches:
        print("SUCCESS: All generated files are reproducible.")
    else:
        raise SystemExit("Reproducibility validation failed: " + ", ".join(mismatches))


if __name__ == "__main__":
    main()
