PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS instrument_types (
    type_id TEXT PRIMARY KEY,
    type_name TEXT NOT NULL,
    measurement_unit TEXT,
    default_interval_days INTEGER
);

CREATE TABLE IF NOT EXISTS calibration_plans (
    plan_id TEXT PRIMARY KEY,
    type_id TEXT NOT NULL,
    interval_days INTEGER NOT NULL CHECK (interval_days > 0),
    grace_period_days INTEGER NOT NULL CHECK (grace_period_days >= 0),
    FOREIGN KEY (type_id) REFERENCES instrument_types(type_id)
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    iso_accredited TEXT
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    type_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    serial_number TEXT,
    status TEXT NOT NULL,
    last_calibration_date TEXT,
    next_due_date TEXT,
    FOREIGN KEY (type_id) REFERENCES instrument_types(type_id),
    FOREIGN KEY (plan_id) REFERENCES calibration_plans(plan_id)
);

CREATE TABLE IF NOT EXISTS calibration_events (
    calibration_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    supplier_id TEXT,
    event_date TEXT NOT NULL,
    due_date_calculated TEXT,
    result TEXT NOT NULL,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

CREATE TABLE IF NOT EXISTS certificates (
    certificate_id TEXT PRIMARY KEY,
    calibration_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    issued_date TEXT,
    valid_until TEXT,
    FOREIGN KEY (calibration_id) REFERENCES calibration_events(calibration_id)
);

CREATE TABLE IF NOT EXISTS work_orders (
    work_order_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    calibration_id TEXT,
    issue_description TEXT,
    corrective_action TEXT,
    impact_assessment TEXT,
    status TEXT,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id),
    FOREIGN KEY (calibration_id) REFERENCES calibration_events(calibration_id)
);

CREATE TABLE IF NOT EXISTS production_uses (
    use_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    use_timestamp TEXT NOT NULL,
    flagged_overdue TEXT,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);

CREATE TABLE IF NOT EXISTS approved_exceptions (
    exception_id TEXT PRIMARY KEY,
    use_id TEXT,
    approved_by TEXT,
    reason TEXT,
    valid_until TEXT,
    FOREIGN KEY (use_id) REFERENCES production_uses(use_id)
);

CREATE TABLE IF NOT EXISTS compliance_flags (
    use_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    use_timestamp TEXT NOT NULL,
    compliance_status TEXT NOT NULL,
    exception_approved TEXT,
    reason_codes TEXT,
    FOREIGN KEY (use_id) REFERENCES production_uses(use_id),
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);

CREATE TABLE IF NOT EXISTS anomaly_findings (
    entity_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    details TEXT
);

CREATE TABLE IF NOT EXISTS ground_truth (
    entity_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    details TEXT
);

CREATE TABLE IF NOT EXISTS audit_records (
    audit_id TEXT PRIMARY KEY,
    entity_type TEXT,
    entity_id TEXT,
    action TEXT,
    timestamp TEXT
);

CREATE INDEX IF NOT EXISTS idx_assets_plan ON assets(plan_id);
CREATE INDEX IF NOT EXISTS idx_events_asset_date ON calibration_events(asset_id, event_date);
CREATE INDEX IF NOT EXISTS idx_certificates_asset ON certificates(asset_id);
CREATE INDEX IF NOT EXISTS idx_production_uses_asset_timestamp ON production_uses(asset_id, use_timestamp);
CREATE INDEX IF NOT EXISTS idx_compliance_status ON compliance_flags(compliance_status);
CREATE INDEX IF NOT EXISTS idx_findings_issue_type ON anomaly_findings(issue_type);
