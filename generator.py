import os
import csv
import json
import random
import hashlib
from datetime import datetime, timedelta

# Project Seed for Reproducibility
SEED = 20261022

class DataGenerator:
    def __init__(self, seed=SEED, num_assets=2000, num_calibrations=5000, num_uses=100000):
        self.seed = seed
        self.num_assets = num_assets
        self.num_calibrations = num_calibrations
        self.num_uses = num_uses
        
        random.seed(self.seed)
        
        self.start_date = datetime(2025, 1, 1)
        self.end_date = datetime(2025, 12, 31)

        # Storage
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

    def generate_all(self):
        print("Generating Master Data...")
        self._generate_master_data()
        
        print(f"Generating Assets ({self.num_assets})...")
        self._generate_assets()
        
        print(f"Generating Calibration Events ({self.num_calibrations})...")
        self._generate_calibrations()
        
        print(f"Generating Production Uses ({self.num_uses})...")
        self._generate_production_uses()
        
        print("Running Anomaly Injections and Ground Truth compilation...")
        self._inject_edge_cases()
        
        print("Generating Audit Records...")
        self._generate_audit_records()

    def _generate_master_data(self):
        # Suppliers
        for i in range(1, 10):
            self.suppliers.append({
                "supplier_id": f"SUP-{i:03d}",
                "name": f"Calibration Vendor {i} Ltd.",
                "iso_accredited": True if i % 2 == 0 else False
            })

        # Instrument Types
        types = [
            ("PRESSURE_GAUGE", 90, "PSI"),
            ("TEMP_SENSOR", 180, "Celsius"),
            ("TORQUE_WRENCH", 30, "Nm"),
            ("FLOW_METER", 365, "L/min"),
            ("SCALE_BALANCE", 120, "kg")
        ]
        for idx, (t_name, interval, unit) in enumerate(types, 1):
            self.instrument_types.append({
                "type_id": f"IT-{idx:03d}",
                "type_name": t_name,
                "measurement_unit": unit,
                "default_interval_days": interval
            })

        # Calibration Plans
        for it in self.instrument_types:
            self.calibration_plans.append({
                "plan_id": f"PLAN-{it['type_id']}",
                "type_id": it['type_id'],
                "interval_days": it['default_interval_days'],
                "grace_period_days": 7
            })

    def _generate_assets(self):
        statuses = ["ACTIVE", "MAINTENANCE", "RETIRED"]
        for i in range(1, self.num_assets + 1):
            asset_id = f"AST-{i:06d}"
            itype = random.choice(self.instrument_types)
            plan = next(p for p in self.calibration_plans if p['type_id'] == itype['type_id'])
            
            self.assets.append({
                "asset_id": asset_id,
                "type_id": itype['type_id'],
                "plan_id": plan['plan_id'],
                "serial_number": f"SN-{random.randint(100000, 999999)}",
                "status": random.choice(statuses),
                "last_calibration_date": None,
                "next_due_date": None
            })

    def _generate_calibrations(self):
        for i in range(1, self.num_calibrations + 1):
            asset = random.choice(self.assets)
            plan = next(p for p in self.calibration_plans if p['plan_id'] == asset['plan_id'])
            supplier = random.choice(self.suppliers)
            
            cal_id = f"CAL-{asset['asset_id']}-2026-{i:06d}"
            event_date = self.start_date + timedelta(days=random.randint(0, 360))
            
            # 92% Pass, 8% Fail
            result = "PASS" if random.random() > 0.08 else "FAIL"
            
            due_date = event_date + timedelta(days=plan['interval_days'])
            asset['last_calibration_date'] = event_date.strftime("%Y-%m-%d")
            asset['next_due_date'] = due_date.strftime("%Y-%m-%d")

            self.calibration_events.append({
                "calibration_id": cal_id,
                "asset_id": asset['asset_id'],
                "supplier_id": supplier['supplier_id'],
                "event_date": event_date.strftime("%Y-%m-%d"),
                "due_date_calculated": due_date.strftime("%Y-%m-%d"),
                "result": result
            })

            # Certificate
            cert_id = f"CERT-{cal_id}"
            self.certificates.append({
                "certificate_id": cert_id,
                "calibration_id": cal_id,
                "asset_id": asset['asset_id'],
                "issued_date": event_date.strftime("%Y-%m-%d"),
                "valid_until": due_date.strftime("%Y-%m-%d")
            })

            # Work order for failed calibrations
                        # Create a corrective work order for failed calibrations
            if result == "FAIL":
                wo_id = f"WO-2026-{len(self.work_orders)+1:06d}"

                status_cycle = ["OPEN", "IN_PROGRESS", "COMPLETED"]
                status = status_cycle[
                    len(self.work_orders) % len(status_cycle)
                ]

                self.work_orders.append({
                    "work_order_id": wo_id,
                    "asset_id": asset["asset_id"],
                    "calibration_id": cal_id,
                    "issue_description": "Failed tolerance verification",
                    "corrective_action": (
                        "Inspect instrument, adjust calibration, "
                        "and perform verification"
                    ),
                    "impact_assessment": (
                        "Review measurements produced since the last "
                        "successful calibration"
                    ),
                    "status": status
                })
    def _generate_production_uses(self):
        for i in range(1, self.num_uses + 1):
            asset = random.choice(self.assets)
            use_timestamp = self.start_date + timedelta(seconds=random.randint(0, 31536000))
            ts_str = use_timestamp.strftime("%Y%m%d%H%M%S")
            
            use_id = f"USE-{asset['asset_id']}-{ts_str}"
            
            # Check if used outside calibration window
            is_overdue = False

            if not asset['next_due_date']:
                # No calibration history: flag use for compliance review.
                # This treats an unknown calibration status as requiring review.
                is_overdue = True
            else:
                due_dt = datetime.strptime(
                    asset['next_due_date'], "%Y-%m-%d"
                )
                if use_timestamp > due_dt:
                    is_overdue = True

            self.production_uses.append({
                "use_id": use_id,
                "asset_id": asset['asset_id'],
                "use_timestamp": use_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "flagged_overdue": is_overdue
            })

    def _inject_edge_cases(self):
        # 1. Inconsistent due date
        if len(self.calibration_events) > 0:
            cal = self.calibration_events[0]
            cal['due_date_calculated'] = "2099-01-01"
            self.ground_truth.append({
                "entity_id": cal['calibration_id'],
                "issue_type": "DUE_DATE_INCONSISTENT_WITH_PLAN",
                "details": "Calculated due date overrides plan logic."
            })

        # 2. Certificate refers to wrong asset
        # 2. Certificate refers to wrong asset
        if len(self.certificates) > 1:
            cert = self.certificates[1]
            cert['asset_id'] = "AST-999999"
            self.ground_truth.append({
                "entity_id": cert['certificate_id'],
                "issue_type": "CERTIFICATE_ASSET_MISMATCH",
                "details": "Certificate links to non-existent/incorrect asset."
            })

        # 3. Failed calibration without work order / impact assessment
        if len(self.calibration_events) > 2:
            cal = self.calibration_events[2]
            cal['result'] = "FAIL"
            self.ground_truth.append({
                "entity_id": cal['calibration_id'],
                "issue_type": "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT",
                "details": "Calibration failed but no corrective action created."
            })

    def _generate_audit_records(self):
        for idx, cal in enumerate(self.calibration_events[:100], 1):
            self.audit_records.append({
                "audit_id": f"AUD-{idx:06d}",
                "entity_type": "CalibrationEvent",
                "entity_id": cal['calibration_id'],
                "action": "RECORD_CREATED",
                "timestamp": cal['event_date'] + " 00:00:00"
            })

    def export_data(self, output_dir="output"):
        os.makedirs(output_dir, exist_ok=True)

        datasets = {
            "suppliers": self.suppliers,
            "instrument_types": self.instrument_types,
            "calibration_plans": self.calibration_plans,
            "assets": self.assets,
            "calibration_events": self.calibration_events,
            "certificates": self.certificates,
            "work_orders": self.work_orders,
            "production_uses": self.production_uses,
            "audit_records": self.audit_records,
            "ground_truth": self.ground_truth
        }

        for name, data in datasets.items():
            if not data:
                continue
            # CSV Export
            csv_path = os.path.join(output_dir, f"{name}.csv")
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

        print(f"All files exported successfully to directory: '{output_dir}/'")

    def compute_checksums(self, output_dir="output"):
        checksums = {}
        for fname in sorted(os.listdir(output_dir)):
            if fname.endswith(".csv"):
                fpath = os.path.join(output_dir, fname)
                with open(fpath, "rb") as f:
                    checksums[fname] = hashlib.md5(f.read()).hexdigest()
        return checksums


if __name__ == "__main__":
    print("--- FIRST GENERATION RUN ---")
    gen1 = DataGenerator(seed=SEED)
    gen1.generate_all()
    gen1.export_data("output_run1")
    chk1 = gen1.compute_checksums("output_run1")

    print("\n--- SECOND GENERATION RUN (REPRODUCIBILITY CHECK) ---")
    gen2 = DataGenerator(seed=SEED)
    gen2.generate_all()
    gen2.export_data("output_run2")
    chk2 = gen2.compute_checksums("output_run2")

    print("\n--- REPRODUCIBILITY VALIDATION ---")
    match = True
    for file, md5_1 in chk1.items():
        md5_2 = chk2.get(file)
        if md5_1 == md5_2:
            print(f"✓ {file}: MATCH ({md5_1})")
        else:
            print(f"✗ {file}: MISMATCH ({md5_1} vs {md5_2})")
            match = False

    if match:
        print("\nSUCCESS: Both generation runs are identical and 100%  reproducible!")