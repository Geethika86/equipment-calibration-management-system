# Data Dictionary

All records are synthetic. Dates use `YYYY-MM-DD`; timestamps use `YYYY-MM-DD HH:MM:SS`. IDs are immutable strings. Empty optional foreign keys are exported as blank CSV values and NULL in SQL.

## `suppliers`

Supplier master records. supplier_id is unique; iso_accredited is boolean.

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `supplier_id` | string ID | Required | Unique primary key |
| `name` | string / enum | Required | See business rules and schema.json |
| `iso_accredited` | boolean | Required | See business rules and schema.json |
| `country` | string / enum | Required | See business rules and schema.json |

## `instrument_types`

Instrument classes. default_interval_days is a positive number of days; measurement units are explicit.

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `type_id` | string ID | Required | Unique primary key |
| `type_name` | string / enum | Required | See business rules and schema.json |
| `measurement_unit` | string / enum | Required | See business rules and schema.json |
| `default_interval_days` | integer | Required | See business rules and schema.json |
| `tolerance_limit` | number | Required | See business rules and schema.json |

## `calibration_plans`

Calibration policy by instrument type. interval_days > 0; grace_period_days >= 0; policy is BLOCK_OVERDUE_USE.

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `plan_id` | string ID | Required | Unique primary key |
| `type_id` | string ID | Required | Unique primary key |
| `interval_days` | integer | Required | See business rules and schema.json |
| `grace_period_days` | integer | Required | See business rules and schema.json |
| `policy` | string / enum | Required | See business rules and schema.json |

## `assets`

Instrument register. status is ACTIVE, MAINTENANCE, or RETIRED; type_id and plan_id must reference parent records.

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `asset_id` | string ID | Required | Unique primary key |
| `type_id` | string ID | Required | Unique primary key |
| `plan_id` | string ID | Required | Unique primary key |
| `serial_number` | string / enum | Required | See business rules and schema.json |
| `status` | string / enum | Required | See business rules and schema.json |
| `commissioned_date` | date/time string | Required | See business rules and schema.json |
| `last_calibration_date` | date/time string | Optional | See business rules and schema.json |
| `next_due_date` | date/time string | Optional | See business rules and schema.json |

## `calibration_events`

Calibration event history. result is PASS or FAIL; due_date_calculated is event date plus plan interval except labelled anomaly.

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `calibration_id` | string ID | Required | Unique primary key |
| `asset_id` | string ID | Required | Unique primary key |
| `supplier_id` | string ID | Required | Unique primary key |
| `event_date` | date/time string | Required | See business rules and schema.json |
| `result` | string / enum | Required | See business rules and schema.json |
| `measurement_value` | number | Required | See business rules and schema.json |
| `measurement_unit` | string / enum | Required | See business rules and schema.json |
| `measured_error` | number | Required | See business rules and schema.json |
| `due_date_calculated` | string / enum | Required | See business rules and schema.json |
| `event_status` | string / enum | Required | See business rules and schema.json |

## `certificates`

Certificate evidence. calibration_id is unique; asset_id must match its calibration event except the labelled mismatch.

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `certificate_id` | string ID | Required | Unique primary key |
| `calibration_id` | string ID | Required | Unique primary key |
| `asset_id` | string ID | Required | Unique primary key |
| `issued_date` | date/time string | Required | See business rules and schema.json |
| `valid_from` | date/time string | Required | See business rules and schema.json |
| `valid_until` | date/time string | Required | See business rules and schema.json |
| `certificate_status` | string / enum | Required | See business rules and schema.json |

## `work_orders`

Corrective action and downtime. failed baseline calibrations have corrective_action and impact_assessment; the labelled exception is intentionally missing.

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `work_order_id` | string ID | Required | Unique primary key |
| `asset_id` | string ID | Required | Unique primary key |
| `calibration_id` | string ID | Required | Unique primary key |
| `issue_description` | string / enum | Required | See business rules and schema.json |
| `corrective_action` | string / enum | Required | See business rules and schema.json |
| `impact_assessment` | string / enum | Required | See business rules and schema.json |
| `opened_at` | date/time string | Required | See business rules and schema.json |
| `downtime_start` | date/time string | Required | See business rules and schema.json |
| `downtime_end` | date/time string | Required | See business rules and schema.json |
| `downtime_hours` | integer | Required | See business rules and schema.json |
| `status` | string / enum | Required | See business rules and schema.json |

## `production_uses`

Use events within the 2025 one-year window, plus a labelled expired-use edge case. flagged_overdue is derived from event history and approved extensions.

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `use_id` | string ID | Required | Unique primary key |
| `asset_id` | string ID | Required | Unique primary key |
| `use_timestamp` | date/time string | Required | See business rules and schema.json |
| `applicable_calibration_id` | string ID | Optional | See business rules and schema.json |
| `flagged_overdue` | boolean | Required | See business rules and schema.json |
| `use_decision` | string / enum | Required | See business rules and schema.json |
| `exception_applied` | boolean | Required | See business rules and schema.json |
| `exception_id` | string ID | Required | See business rules and schema.json |

## `calibration_extensions`

Calibration extension source records; original due dates remain unchanged and extended_due_date is explicit.

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `extension_id` | string ID | Required | Unique primary key |
| `asset_id` | string ID | Required | Unique primary key |
| `calibration_id` | string ID | Required | Unique primary key |
| `original_due_date` | date/time string | Required | See business rules and schema.json |
| `extended_due_date` | date/time string | Required | See business rules and schema.json |
| `extension_days` | integer | Required | See business rules and schema.json |
| `reason` | string / enum | Required | See business rules and schema.json |
| `approved_by` | string / enum | Required | See business rules and schema.json |
| `approval_status` | string / enum | Required | See business rules and schema.json |
| `approved_at` | date/time string | Required | See business rules and schema.json |

## `approved_exceptions`

Approved exception records referenced by production uses; only approved records may authorize use past original due date.

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `exception_id` | string ID | Required | See business rules and schema.json |
| `asset_id` | string ID | Required | Unique primary key |
| `calibration_id` | string ID | Required | Unique primary key |
| `original_due_date` | date/time string | Required | See business rules and schema.json |
| `extended_due_date` | date/time string | Required | See business rules and schema.json |
| `extension_days` | integer | Required | See business rules and schema.json |
| `reason` | string / enum | Required | See business rules and schema.json |
| `approved_by` | string / enum | Required | See business rules and schema.json |
| `approval_status` | string / enum | Required | See business rules and schema.json |
| `approved_at` | date/time string | Required | See business rules and schema.json |

## `anomaly_findings`

Finding records linked to ground_truth by ground_truth_id; every finding has a primary key.

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `finding_id` | string ID | Required | See business rules and schema.json |
| `ground_truth_id` | string ID | Required | Unique primary key |
| `entity_type` | string / enum | Required | See business rules and schema.json |
| `entity_id` | string ID | Required | See business rules and schema.json |
| `issue_type` | string / enum | Required | See business rules and schema.json |
| `details` | string / enum | Required | See business rules and schema.json |
| `expected_decision` | string / enum | Required | See business rules and schema.json |
| `finding_status` | string / enum | Required | See business rules and schema.json |

## `alerts`

Derived operational alerts; severity is LOW, MEDIUM, or HIGH; status is OPEN, ACKNOWLEDGED, or RESOLVED.

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `alert_id` | string ID | Required | Unique primary key |
| `asset_id` | string ID | Required | Unique primary key |
| `entity_type` | string / enum | Required | See business rules and schema.json |
| `entity_id` | string ID | Required | See business rules and schema.json |
| `alert_type` | string / enum | Required | See business rules and schema.json |
| `severity` | string / enum | Required | See business rules and schema.json |
| `description` | string / enum | Required | See business rules and schema.json |
| `status` | string / enum | Required | See business rules and schema.json |
| `created_at` | date/time string | Required | See business rules and schema.json |

## `audit_records`

Append-only record of creation and injected state changes; timestamps are ISO-like date/time strings.

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `audit_id` | string ID | Required | Unique primary key |
| `entity_type` | string / enum | Required | See business rules and schema.json |
| `entity_id` | string ID | Required | See business rules and schema.json |
| `action` | string / enum | Required | See business rules and schema.json |
| `from_state` | string / enum | Optional | See business rules and schema.json |
| `to_state` | string / enum | Optional | See business rules and schema.json |
| `timestamp` | date/time string | Required | See business rules and schema.json |

## `ground_truth`

Separate known-anomaly labels and expected decisions; never use as model input features.

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `ground_truth_id` | string ID | Required | Unique primary key |
| `entity_type` | string / enum | Required | See business rules and schema.json |
| `entity_id` | string ID | Required | See business rules and schema.json |
| `issue_type` | string / enum | Required | See business rules and schema.json |
| `details` | string / enum | Required | See business rules and schema.json |
| `expected_decision` | string / enum | Required | See business rules and schema.json |

## Relationships and cardinality

- InstrumentType 1:N Asset; InstrumentType 1:N CalibrationPlan.
- CalibrationPlan 1:N Asset.
- Asset 1:N CalibrationEvent and 1:N ProductionUse.
- Supplier 1:N CalibrationEvent.
- CalibrationEvent 0:1 Certificate (certificate gaps are labelled), 0:N WorkOrder, and 0:N CalibrationExtension/ApprovedException.
- ProductionUse optionally references one ApprovedException.
- AnomalyFinding N:1 GroundTruth through ground_truth_id.
- Alert and AuditRecord use a polymorphic entity_type/entity_id pair; alert asset_id is an optional FK to Asset.
- GroundTruth is a separate evaluation-label table, not an input feature.
