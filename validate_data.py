import csv
import sys
from pathlib import Path
from datetime import date, datetime, timedelta


REQUIRED_COUNTS_BY_SCALE = {
    "starter": {
        "assets": 100,
        "calibration_events": 250,
        "production_uses": 5000,
    },
    "full": {
        "assets": 2000,
        "calibration_events": 5000,
        "production_uses": 100000,
    },
}


REQUIRED_ANOMALIES = {
    "DUE_DATE_INCONSISTENT_WITH_PLAN",
    "EXPIRED_INSTRUMENT_USED_WITHOUT_EXCEPTION",
    "CERTIFICATE_ASSET_MISMATCH",
    "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT",
}


def load_csv(folder, name):
    path = folder / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def require(condition, message, errors):
    if not condition:
        errors.append(message)


def main():
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "output_final")
    if not folder.is_dir():
        print(f"ERROR: Output directory not found: {folder}")
        return 1

    errors = []
    try:
        names = [
            "assets", "instrument_types", "calibration_plans",
            "calibration_events", "certificates", "work_orders",
            "production_uses", "suppliers", "ground_truth",
            "anomaly_findings", "approved_exceptions",
            "calibration_extensions", "audit_records", "alerts",
        ]
        data = {name: load_csv(folder, name) for name in names}
    except (OSError, csv.Error) as exc:
        print(f"ERROR loading dataset: {exc}")
        return 1

    assets = data["assets"]
    types = data["instrument_types"]
    plans = data["calibration_plans"]
    events = data["calibration_events"]
    certificates = data["certificates"]
    work_orders = data["work_orders"]
    uses = data["production_uses"]
    truth = data["ground_truth"]
    findings = data["anomaly_findings"]

    def unique(rows, field, label):
        values = [r.get(field, "") for r in rows]
        ok = all(values) and len(values) == len(set(values))
        require(ok, f"{label}: missing or duplicate {field}", errors)
        if ok:
            print(f"PASS: {label}.{field} unique ({len(rows)} rows)")
        return set(values)

    asset_ids = unique(assets, "asset_id", "assets")
    type_ids = unique(types, "type_id", "instrument_types")
    plan_ids = unique(plans, "plan_id", "calibration_plans")
    event_ids = unique(events, "calibration_id", "calibration_events")
    cert_ids = unique(certificates, "certificate_id", "certificates")
    work_ids = unique(work_orders, "work_order_id", "work_orders")
    use_ids = unique(uses, "use_id", "production_uses")

    for table, rows in data.items():
        print(f"INFO: {table}: {len(rows)} rows")

    
    actual_assets = len(data["assets"])

    if actual_assets == 100:
        expected_counts = REQUIRED_COUNTS_BY_SCALE["starter"]
    elif actual_assets == 2000:
        expected_counts = REQUIRED_COUNTS_BY_SCALE["full"]
    else:
        expected_counts = {}

        errors.append(
            f"Unsupported asset count: {actual_assets}. "
            "Expected 100 for starter or 2000 for full."
        )

    for table, expected in expected_counts.items():
        actual = len(data[table])
        require(
            actual == expected,
            f"{table}: expected {expected} rows, got {actual}",
            errors,
        )

    types_by_id = {r["type_id"]: r for r in types}
    plans_by_id = {r["plan_id"]: r for r in plans}
    assets_by_id = {r["asset_id"]: r for r in assets}
    events_by_id = {r["calibration_id"]: r for r in events}

    truth_pairs = {
        (r.get("entity_id", ""), r.get("issue_type", ""))
        for r in truth
    }
    finding_pairs = {
        (r.get("entity_id", ""), r.get("issue_type", ""))
        for r in findings
    }
    labelled_types = {issue for _, issue in truth_pairs}

    for issue in REQUIRED_ANOMALIES:
        require(issue in labelled_types,
                f"Required anomaly category not labelled: {issue}", errors)

    for pair in truth_pairs:
        require(pair in finding_pairs,
                f"Ground-truth label has no matching finding: {pair}", errors)

    # Asset relationships.
    for asset in assets:
        require(asset.get("type_id") in type_ids,
                f"Asset {asset.get('asset_id')} has invalid instrument type", errors)
        require(asset.get("plan_id") in plan_ids,
                f"Asset {asset.get('asset_id')} has invalid plan", errors)

    # Calibration dates and relationships.
    due_anomalies = {
        entity for entity, issue in truth_pairs
        if issue == "DUE_DATE_INCONSISTENT_WITH_PLAN"
    }

    for event in events:
        cid = event.get("calibration_id", "")
        aid = event.get("asset_id", "")
        require(aid in asset_ids,
                f"Calibration {cid} references missing asset {aid}", errors)

        if event.get("supplier_id"):
            require(event["supplier_id"] in {
                r.get("supplier_id") for r in data["suppliers"]
            }, f"Calibration {cid} references missing supplier", errors)

        result = event.get("result", "").upper()
        require(result in {"PASS", "FAIL"},
                f"Calibration {cid} has invalid result {result}", errors)

        try:
            event_date = datetime.fromisoformat(
                event["event_date"]
            ).date()
            actual_due = date.fromisoformat(event["due_date_calculated"])
            asset = assets_by_id.get(aid)
            plan = plans_by_id.get(asset.get("plan_id", "")) if asset else None

            if plan:
                interval = int(plan["interval_days"])
                expected_due = event_date + timedelta(days=interval)
                if actual_due != expected_due:
                    require(
                        cid in due_anomalies,
                        f"Calibration {cid} due date differs from plan without a label",
                        errors,
                    )
                else:
                    require(
                        cid not in due_anomalies,
                        f"Calibration {cid} is labelled as a due-date anomaly but dates match",
                        errors,
                    )
        except (ValueError, KeyError, TypeError):
            errors.append(f"Calibration {cid} has invalid date or plan interval")

    # Certificates must reference a real calibration. Asset mismatch is allowed
    # only when the mismatch is explicitly labelled in ground truth.
    mismatch_entities = {
        entity for entity, issue in truth_pairs
        if issue == "CERTIFICATE_ASSET_MISMATCH"
    }
    for cert in certificates:
        cert_id = cert.get("certificate_id", "")
        cid = cert.get("calibration_id", "")
        require(cid in event_ids,
                f"Certificate {cert_id} references missing calibration {cid}",
                errors)
        event = events_by_id.get(cid)
        if event:
            mismatch = cert.get("asset_id") != event.get("asset_id")
            require(
                not mismatch or cert_id in mismatch_entities,
                f"Certificate {cert_id} asset mismatch is not labelled",
                errors,
            )
            if cert_id in mismatch_entities:
                require(mismatch,
                        f"Certificate {cert_id} is labelled mismatched but assets match",
                        errors)

    # Work orders must reference valid assets; calibration references are
    # checked when the optional field is populated.
    for work in work_orders:
        wid = work.get("work_order_id", "")
        require(work.get("asset_id") in asset_ids,
                f"Work order {wid} references missing asset", errors)
        cid = work.get("calibration_id", "")
        if cid:
            require(cid in event_ids,
                    f"Work order {wid} references missing calibration", errors)

    # Production use references and required expired-use anomaly.
    for use in uses:
        uid = use.get("use_id", "")
        require(use.get("asset_id") in asset_ids,
                f"Production use {uid} references missing asset", errors)
        cid = use.get("applicable_calibration_id", "")
        if cid:
            require(cid in event_ids,
                    f"Production use {uid} references missing calibration", errors)

    # Verify that every required category has a matching finding.
    for issue in REQUIRED_ANOMALIES:
        require(any(pair[1] == issue for pair in finding_pairs),
                f"No anomaly finding exists for {issue}", errors)

    # Verify a labelled failed calibration really failed.
    failed_entities = {
        entity for entity, issue in truth_pairs
        if issue == "FAILED_CALIBRATION_NO_IMPACT_ASSESSMENT"
    }
    for cid in failed_entities:
        event = events_by_id.get(cid)
        require(event is not None,
                f"Failed-calibration anomaly references missing event {cid}", errors)
        if event:
            require(event.get("result", "").upper() == "FAIL",
                    f"Labelled failed-calibration event {cid} is not FAIL", errors)
            related = [
                w for w in work_orders
                if w.get("calibration_id") == cid
            ]
            require(not related,
                    f"Failed calibration {cid} has a related work order; review impact assessment",
                    errors)

    summary = [
        "EQUIPMENT CALIBRATION MANAGEMENT SYSTEM - VALIDATION",
        f"Output directory: {folder}",
        f"Assets: {len(assets)}",
        f"Calibration events: {len(events)}",
        f"Production uses: {len(uses)}",
        f"Certificates: {len(certificates)}",
        f"Work orders: {len(work_orders)}",
        f"Ground-truth labels: {len(truth)}",
        f"Anomaly findings: {len(findings)}",
        f"Validation result: {'FAIL' if errors else 'PASS'}",
    ]
    if errors:
        summary.append("\nERRORS:")
        summary.extend(f"- {e}" for e in errors)

    (folder / "external_validation_summary.txt").write_text(
        "\n".join(summary) + "\n", encoding="utf-8"
    )

    if errors:
        print("\nVALIDATION FAILED:")
        for error in errors[:40]:
            print(" -", error)
        print(f"\nTotal errors: {len(errors)}")
        print(f"Details saved to {folder / 'external_validation_summary.txt'}")
        return 1

    print("\nSUCCESS: All implemented validation checks passed.")
    print(f"Summary saved to {folder / 'external_validation_summary.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


