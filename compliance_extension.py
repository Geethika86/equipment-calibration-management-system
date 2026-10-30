
import csv
import json
import shutil
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 20261022
SOURCE_DIR = Path("output_run1")
OUTPUT_DIR = Path("output_completed")


def read_csv(filename):
    path = SOURCE_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows, fieldnames=None):
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_date(value):
    return date.fromisoformat(value[:10]) if value else None


def parse_datetime(value):
    return datetime.fromisoformat(value) if value else None


def add_ground_truth(rows, entity_id, issue_type, details):
    # Do not add duplicate labels for the same entity and issue.
    exists = any(
        row["entity_id"] == entity_id
        and row["issue_type"] == issue_type
        for row in rows
    )

    if not exists:
        rows.append({
            "entity_id": entity_id,
            "issue_type": issue_type,
            "details": details,
        })


def main():
    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(
            f"Cannot find {SOURCE_DIR.resolve()}. "
            "Run this script from your project folder."
        )

    # Load source datasets.
    assets = read_csv("assets.csv")
    plans = read_csv("calibration_plans.csv")
    events = read_csv("calibration_events.csv")
    certificates = read_csv("certificates.csv")
    work_orders = read_csv("work_orders.csv")
    uses = read_csv("production_uses.csv")
    suppliers = read_csv("suppliers.csv")
    instrument_types = read_csv("instrument_types.csv")
    existing_ground_truth = read_csv("ground_truth.csv")
    audit_records = read_csv("audit_records.csv")

    # Preserve source files. All modifications apply to output copies.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in SOURCE_DIR.glob("*.csv"):
        shutil.copy2(path, OUTPUT_DIR / path.name)

    # Make independent working copies.
    assets_by_id = {row["asset_id"]: row for row in assets}
    plans_by_id = {row["plan_id"]: row for row in plans}
    events_by_id = {row["calibration_id"]: row for row in events}

    certificates_by_event = defaultdict(list)
    for certificate in certificates:
        certificates_by_event[certificate["calibration_id"]].append(
            certificate
        )

    events_by_asset = defaultdict(list)
    for event in events:
        events_by_asset[event["asset_id"]].append(event)

    for asset_id in events_by_asset:
        events_by_asset[asset_id].sort(
            key=lambda row: (row["event_date"], row["calibration_id"])
        )

    # Work on copied records, not the original CSV files.
    work_orders = [row.copy() for row in work_orders]
    uses = [row.copy() for row in uses]
    ground_truth = [row.copy() for row in existing_ground_truth]

    findings = []
    finding_keys = set()

    def add_finding(entity_id, issue_type, details):
        key = (entity_id, issue_type)
        if key not in finding_keys:
            findings.append({
                "entity_id": entity_id,
                "issue_type": issue_type,
                "details": details,
            })
            finding_keys.add(key)

    # 1. Check every calibration event against its plan interval.
    expected_due_by_event = {}

    for event in events:
        asset = assets_by_id.get(event["asset_id"])
        if not asset:
            add_finding(
                event["calibration_id"],
                "CALIBRATION_ASSET_NOT_FOUND",
                f"Asset {event['asset_id']} does not exist.",
            )
            continue

        plan = plans_by_id.get(asset["plan_id"])
        if not plan:
            add_finding(
                event["calibration_id"],
                "CALIBRATION_PLAN_NOT_FOUND",
                f"Plan {asset['plan_id']} does not exist.",
            )
            continue

        event_date = parse_date(event["event_date"])
        if event_date is None:
            add_finding(
                event["calibration_id"],
                "INVALID_CALIBRATION_DATE",
                "Calibration event has no valid event date.",
            )
            continue

        expected_due = event_date + timedelta(
            days=int(plan["interval_days"])
        )
        expected_due_by_event[event["calibration_id"]] = expected_due

        recorded_due = parse_date(event["due_date_calculated"])
        if recorded_due != expected_due:
            details = (
                f"Recorded due date: {event['due_date_calculated']}; "
                f"expected event date + {plan['interval_days']} days "
                f"= {expected_due.isoformat()}."
            )
            add_finding(
                event["calibration_id"],
                "DUE_DATE_INCONSISTENT_WITH_PLAN",
                details,
            )
            add_ground_truth(
                ground_truth,
                event["calibration_id"],
                "DUE_DATE_INCONSISTENT_WITH_PLAN",
                details,
            )

    # 2. Validate certificate-to-event and certificate-to-asset relationships.
    for certificate in certificates:
        event = events_by_id.get(certificate["calibration_id"])

        if event is None:
            details = (
                f"Certificate references missing calibration "
                f"{certificate['calibration_id']}."
            )
            add_finding(
                certificate["certificate_id"],
                "CERTIFICATE_CALIBRATION_NOT_FOUND",
                details,
            )
            continue

        event_asset_id = event["asset_id"]
        certificate_asset_id = certificate["asset_id"]

        if (
            certificate_asset_id != event_asset_id
            or certificate_asset_id not in assets_by_id
        ):
            details = (
                f"Certificate asset is {certificate_asset_id}; "
                f"calibration event asset is {event_asset_id}."
            )
            add_finding(
                certificate["certificate_id"],
                "CERTIFICATE_ASSET_MISMATCH",
                details,
            )
            add_ground_truth(
                ground_truth,
                certificate["certificate_id"],
                "CERTIFICATE_ASSET_MISMATCH",
                details,
            )

        issued_date = parse_date(certificate["issued_date"])
        valid_until = parse_date(certificate["valid_until"])

        if (
            issued_date is None
            or valid_until is None
            or valid_until < issued_date
        ):
            add_finding(
                certificate["certificate_id"],
                "INVALID_CERTIFICATE_DATES",
                "Certificate dates are missing or valid_until precedes "
                "issued_date.",
            )

    # 3. Check failed calibrations and their impact assessments.
    work_orders_by_event = defaultdict(list)
    for work_order in work_orders:
        work_orders_by_event[work_order["calibration_id"]].append(
            work_order
        )

    for event in events:
        if event["result"].strip().upper() != "FAIL":
            continue

        linked_orders = work_orders_by_event.get(
            event["calibration_id"], []
        )

        missing_assessment = (
            not linked_orders
            or all(
                not order.get("impact_assessment", "").strip()
                for order in linked_orders
            )
        )

        if missing_assessment:
            details = (
                "Failed calibration has no linked work order with a "
                "recorded impact assessment."
            )
            add_finding(
                event["calibration_id"],
                "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT",
                details,
            )
            add_ground_truth(
                ground_truth,
                event["calibration_id"],
                "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT",
                details,
            )

    # Preserve the original generator's third labelled scenario by
    # making its missing impact assessment explicit in the output copy.
    target_failed = next(
        (
            row["entity_id"]
            for row in ground_truth
            if row["issue_type"]
            == "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT"
            and row["entity_id"] in events_by_id
        ),
        None,
    )

    if target_failed:
        linked_orders = work_orders_by_event.get(target_failed, [])
        if linked_orders:
            # Blank the assessment in the copied output to make the
            # labelled exception true and independently detectable.
            linked_orders[0]["impact_assessment"] = ""

            details = (
                "Injected labelled anomaly: failed calibration has a "
                "work order but its impact assessment is blank."
            )
            add_finding(
                target_failed,
                "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT",
                details,
            )
            add_ground_truth(
                ground_truth,
                target_failed,
                "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT",
                details,
            )

    # 4. Calculate production-use compliance from the actual event,
    # plan and certificate data, not the original flagged_overdue field.
    approved_exceptions = set()  # No exception records supplied.
    compliance_flags = []

    def assess_use(use):
        use_time = parse_datetime(use["use_timestamp"])
        asset_id = use["asset_id"]

        reasons = []

        if use_time is None:
            return ["INVALID_USE_TIMESTAMP"]

        if asset_id not in assets_by_id:
            return ["USE_ASSET_NOT_FOUND"]

        asset_events = [
            event for event in events_by_asset.get(asset_id, [])
            if parse_date(event["event_date"]) <= use_time.date()
        ]

        if not asset_events:
            return ["NO_PRIOR_CALIBRATION"]

        latest_event = asset_events[-1]
        calibration_id = latest_event["calibration_id"]

        if latest_event["result"].strip().upper() != "PASS":
            reasons.append("LATEST_CALIBRATION_FAILED")

        plan = plans_by_id.get(assets_by_id[asset_id]["plan_id"])
        if plan:
            expected_due = (
                parse_date(latest_event["event_date"])
                + timedelta(days=int(plan["interval_days"]))
            )
            grace_end = expected_due + timedelta(
                days=int(plan["grace_period_days"])
            )
            if use_time.date() > grace_end:
                reasons.append("CALIBRATION_OVERDUE_AFTER_GRACE")

        valid_certificate = False
        for certificate in certificates_by_event.get(calibration_id, []):
            if certificate["asset_id"] != asset_id:
                continue

            issued = parse_date(certificate["issued_date"])
            valid_until = parse_date(certificate["valid_until"])

            if (
                issued
                and valid_until
                and issued <= use_time.date() <= valid_until
            ):
                valid_certificate = True
                break

        if not valid_certificate:
            reasons.append("NO_VALID_MATCHING_CERTIFICATE")

        return reasons

    for use in uses:
        reasons = assess_use(use)
        exception_approved = use["use_id"] in approved_exceptions
        flagged = bool(reasons) and not exception_approved

        compliance_flags.append({
            "use_id": use["use_id"],
            "asset_id": use["asset_id"],
            "use_timestamp": use["use_timestamp"],
            "compliance_status": "NON_COMPLIANT" if flagged else "COMPLIANT",
            "exception_approved": str(exception_approved).lower(),
            "reason_codes": "|".join(reasons),
        })

        if flagged:
            for reason in reasons:
                add_finding(
                    use["use_id"],
                    reason,
                    f"Production use at {use['use_timestamp']}; "
                    f"asset {use['asset_id']}; no approved exception.",
                )

    # Ensure the required expired-use scenario exists in the enhanced
    # dataset. If none is naturally present, move one copied use to a
    # clearly expired date and keep its ID consistent with its timestamp.
    if not any(
        row["issue_type"] in {
            "CALIBRATION_OVERDUE_AFTER_GRACE",
            "NO_VALID_MATCHING_CERTIFICATE",
        }
        and row["entity_id"].startswith("USE-")
        for row in findings
    ):
        if not uses:
            raise ValueError("No production-use rows are available.")

        candidate = uses[0]
        candidate["use_timestamp"] = "2026-12-31 23:59:59"
        stamp = datetime.strptime(
            candidate["use_timestamp"], "%Y-%m-%d %H:%M:%S"
        ).strftime("%Y%m%d%H%M%S")
        candidate["use_id"] = f"USE-{candidate['asset_id']}-{stamp}"

        # Rebuild use compliance after this controlled anomaly injection.
        findings = [
            row for row in findings
            if not (
                row["entity_id"] == candidate["use_id"]
                and row["issue_type"].startswith("USE_")
            )
        ]
        finding_keys = {
            (row["entity_id"], row["issue_type"]) for row in findings
        }
        compliance_flags = []
        for use in uses:
            reasons = assess_use(use)
            exception_approved = use["use_id"] in approved_exceptions
            flagged = bool(reasons) and not exception_approved

            compliance_flags.append({
                "use_id": use["use_id"],
                "asset_id": use["asset_id"],
                "use_timestamp": use["use_timestamp"],
                "compliance_status": (
                    "NON_COMPLIANT" if flagged else "COMPLIANT"
                ),
                "exception_approved": str(exception_approved).lower(),
                "reason_codes": "|".join(reasons),
            })

            if flagged:
                for reason in reasons:
                    add_finding(
                        use["use_id"],
                        reason,
                        f"Production use at {use['use_timestamp']}; "
                        f"asset {use['asset_id']}; no approved exception.",
                    )

    # Add a clear ground-truth label for a production use that has no
    # valid certificate or is overdue beyond the plan's grace period.
    expired_use = next(
        (
            row for row in compliance_flags
            if row["compliance_status"] == "NON_COMPLIANT"
            and (
                "CALIBRATION_OVERDUE_AFTER_GRACE" in row["reason_codes"]
                or "NO_VALID_MATCHING_CERTIFICATE" in row["reason_codes"]
            )
        ),
        None,
    )

    
    if expired_use:
        details = (
            "Production use was outside the valid calibration/certificate "
            "window and no approved exception was recorded."
        )

        add_finding(
            expired_use["use_id"],
            "EXPIRED_INSTRUMENT_USED_WITHOUT_EXCEPTION",
            details,
        )

        add_ground_truth(
            ground_truth,
            expired_use["use_id"],
            "EXPIRED_INSTRUMENT_USED_WITHOUT_EXCEPTION",
            details,
        )

    # Export all enhanced datasets.
    write_csv(OUTPUT_DIR / "work_orders.csv", work_orders)
    write_csv(OUTPUT_DIR / "production_uses.csv", uses)
    write_csv(OUTPUT_DIR / "ground_truth.csv", ground_truth)
    write_csv(
        OUTPUT_DIR / "compliance_flags.csv",
        compliance_flags,
        [
            "use_id", "asset_id", "use_timestamp",
            "compliance_status", "exception_approved", "reason_codes",
        ],
    )
    write_csv(
        OUTPUT_DIR / "anomaly_findings.csv",
        findings,
        ["entity_id", "issue_type", "details"],
    )
    write_csv(
        OUTPUT_DIR / "approved_exceptions.csv",
        [],
        ["exception_id", "use_id", "approved_by", "reason", "valid_until"],
    )

    # Simple manifest with counts and reproducibility metadata.
    manifest = {
        "project": "Equipment Calibration System",
        "seed": SEED,
        "source_directory": str(SOURCE_DIR),
        "output_directory": str(OUTPUT_DIR),
        "synthetic_data": True,
        "source_files_preserved": True,
        "rules": {
            "expected_due_date": "event_date + plan.interval_days",
            "overdue_policy": (
                "Use is overdue after interval_days plus grace_period_days."
            ),
            "certificate_policy": (
                "Certificate must match the calibration and asset, "
                "be issued by use date, and not be expired."
            ),
            "exceptions": (
                "No approved exception records were provided; "
                "the exception register is empty."
            ),
        },
        "record_counts": {
            "assets": len(assets),
            "calibration_plans": len(plans),
            "calibration_events": len(events),
            "certificates": len(certificates),
            "work_orders": len(work_orders),
            "production_uses": len(uses),
            "compliance_flags": len(compliance_flags),
            "anomaly_findings": len(findings),
            "ground_truth": len(ground_truth),
            "suppliers": len(suppliers),
            "instrument_types": len(instrument_types),
            "audit_records": len(audit_records),
        },
    }

    with (OUTPUT_DIR / "manifest.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(manifest, file, indent=2)

    print(f"\nEnhanced files written to: {OUTPUT_DIR.resolve()}")
    print(f"Assets: {len(assets)}")
    print(f"Calibration events: {len(events)}")
    print(f"Production uses: {len(uses)}")
    print(f"Compliance flags: {len(compliance_flags)}")
    print(f"Anomaly findings: {len(findings)}")
    print(f"Ground-truth labels: {len(ground_truth)}")
    print("Original output_run1 files were not modified.")


if __name__ == "__main__":
    main()
