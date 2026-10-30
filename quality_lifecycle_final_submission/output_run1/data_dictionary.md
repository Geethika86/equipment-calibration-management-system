# Data Dictionary

All records are synthetic. Date fields use `YYYY-MM-DD`; timestamp fields use `YYYY-MM-DD HH:MM:SS`. IDs are immutable strings. Blank optional CSV references represent SQL NULL.

## `suppliers`

Supplier master records.

| Field | Type | Required | Allowed values / units | Uniqueness | Validation rule |
|---|---|---|---|---|---|
| `supplier_id` | string | Required | Free text / identifier | Primary key | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies; duplicates rejected |
| `name` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `iso_accredited` | boolean (0/1 in SQL) | Required | true/false (0/1 in SQL) | Not unique | Must be non-empty |
| `country` | string | Required | Free text / identifier | Not unique | Must be non-empty |

## `instrument_types`

Instrument classes and measurement units.

| Field | Type | Required | Allowed values / units | Uniqueness | Validation rule |
|---|---|---|---|---|---|
| `type_id` | string | Required | Free text / identifier | Primary key | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies; duplicates rejected |
| `type_name` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `measurement_unit` | string | Required | PSI | Celsius | Nm | L/min | kg (from InstrumentType) | Not unique | Must be non-empty |
| `default_interval_days` | integer | Required | Positive whole days | Not unique | Must be non-empty; value > 0 |
| `tolerance_limit` | decimal number | Required | Numeric; measurement_value uses the instrument's measurement_unit; measured_error/tolerance_limit use the same unit | Not unique | Must be non-empty; value >= 0 |

## `calibration_plans`

Calibration interval, grace period, and overdue-use policy by instrument type.

| Field | Type | Required | Allowed values / units | Uniqueness | Validation rule |
|---|---|---|---|---|---|
| `plan_id` | string | Required | Free text / identifier | Primary key | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies; duplicates rejected |
| `type_id` | string | Required | Free text / identifier | Not unique | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies |
| `interval_days` | integer | Required | Positive whole days | Not unique | Must be non-empty; value > 0 |
| `grace_period_days` | integer | Required | Zero or positive whole days | Not unique | Must be non-empty; value >= 0 |
| `policy` | string | Required | BLOCK_OVERDUE_USE | Not unique | Must be non-empty |

## `assets`

Registered instruments; current calibration dates are derived from event history.

| Field | Type | Required | Allowed values / units | Uniqueness | Validation rule |
|---|---|---|---|---|---|
| `asset_id` | string | Required | Free text / identifier | Primary key | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies; duplicates rejected |
| `type_id` | string | Required | Free text / identifier | Not unique | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies |
| `plan_id` | string | Required | Free text / identifier | Not unique | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies |
| `serial_number` | string | Required | Free text / identifier | Unique | Must be non-empty; duplicates rejected |
| `status` | string | Required | ACTIVE | MAINTENANCE | RETIRED | Not unique | Must be non-empty |
| `commissioned_date` | date string | Required | YYYY-MM-DD | Not unique | Must be non-empty |
| `last_calibration_date` | date string | Optional | YYYY-MM-DD | Not unique | May be blank/NULL |
| `next_due_date` | date string | Optional | YYYY-MM-DD | Not unique | May be blank/NULL |

## `calibration_events`

Immutable calibration history with measured result and plan-derived due date.

| Field | Type | Required | Allowed values / units | Uniqueness | Validation rule |
|---|---|---|---|---|---|
| `calibration_id` | string | Required | Free text / identifier | Primary key | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies; duplicates rejected |
| `asset_id` | string | Required | Free text / identifier | Not unique | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies |
| `supplier_id` | string | Required | Free text / identifier | Not unique | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies |
| `event_date` | timestamp string | Required | YYYY-MM-DD HH:MM:SS | Not unique | Must be non-empty |
| `result` | string | Required | PASS | FAIL | Not unique | Must be non-empty |
| `measurement_value` | decimal number | Required | Numeric; measurement_value uses the instrument's measurement_unit; measured_error/tolerance_limit use the same unit | Not unique | Must be non-empty; value >= 0 |
| `measurement_unit` | string | Required | PSI | Celsius | Nm | L/min | kg (from InstrumentType) | Not unique | Must be non-empty |
| `measured_error` | decimal number | Required | Numeric; measurement_value uses the instrument's measurement_unit; measured_error/tolerance_limit use the same unit | Not unique | Must be non-empty; value >= 0 |
| `due_date_calculated` | string | Required | Free text / identifier | Not unique | Must be non-empty; equals event date + plan interval except the labelled due-date anomaly |
| `event_status` | string | Required | COMPLETED | Not unique | Must be non-empty |

## `certificates`

Calibration evidence; certificate gaps and asset mismatches are explicitly labelled.

| Field | Type | Required | Allowed values / units | Uniqueness | Validation rule |
|---|---|---|---|---|---|
| `certificate_id` | string | Required | Free text / identifier | Primary key | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies; duplicates rejected |
| `calibration_id` | string | Required | Free text / identifier | Unique | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies; duplicates rejected |
| `asset_id` | string | Required | Free text / identifier | Not unique | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies |
| `issued_date` | date string | Required | YYYY-MM-DD | Not unique | Must be non-empty |
| `valid_from` | date string | Required | YYYY-MM-DD | Not unique | Must be non-empty |
| `valid_until` | date string | Required | YYYY-MM-DD | Not unique | Must be non-empty; must be on/after valid_from and issued_date; reconcile with derived plan due date |
| `certificate_status` | string | Required | VALID | Not unique | Must be non-empty |

## `work_orders`

Corrective actions, impact assessment, lifecycle state, and downtime for failed calibrations.

| Field | Type | Required | Allowed values / units | Uniqueness | Validation rule |
|---|---|---|---|---|---|
| `work_order_id` | string | Required | Free text / identifier | Primary key | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies; duplicates rejected |
| `asset_id` | string | Required | Free text / identifier | Not unique | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies |
| `calibration_id` | string | Required | Free text / identifier | Not unique | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies |
| `issue_description` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `corrective_action` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `impact_assessment` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `opened_at` | timestamp string | Required | YYYY-MM-DD HH:MM:SS | Not unique | Must be non-empty |
| `downtime_start` | timestamp string | Required | YYYY-MM-DD HH:MM:SS | Not unique | Must be non-empty |
| `downtime_end` | timestamp string | Required | YYYY-MM-DD HH:MM:SS | Not unique | Must be non-empty |
| `downtime_hours` | integer | Required | Zero or positive whole hours; reconciles with downtime_start/end | Not unique | Must be non-empty; value >= 0 |
| `status` | string | Required | OPEN | IN_PROGRESS | COMPLETED | Not unique | Must be non-empty |

## `production_uses`

Production-use decisions derived from calibration history, grace periods, and approved extensions.

| Field | Type | Required | Allowed values / units | Uniqueness | Validation rule |
|---|---|---|---|---|---|
| `use_id` | string | Required | Free text / identifier | Primary key | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies; duplicates rejected |
| `asset_id` | string | Required | Free text / identifier | Not unique | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies |
| `use_timestamp` | timestamp string | Required | YYYY-MM-DD HH:MM:SS | Not unique | Must be non-empty |
| `applicable_calibration_id` | string | Optional | Free text / identifier | Not unique | May be blank/NULL; referenced IDs must exist in the parent table where a declared FK applies |
| `flagged_overdue` | boolean (0/1 in SQL) | Required | true/false (0/1 in SQL) | Not unique | Must be non-empty |
| `use_decision` | string | Required | ALLOWED_IN_CALIBRATION_WINDOW | ALLOWED_EXTENSION | BLOCKED_OVERDUE | BLOCKED_FAILED_CALIBRATION | REVIEW_NO_CALIBRATION | Not unique | Must be non-empty |
| `exception_applied` | boolean (0/1 in SQL) | Required | true/false (0/1 in SQL) | Not unique | Must be non-empty |

## `calibration_extensions`

Emergency extension requests with request metadata, PENDING/APPROVED/REJECTED decisions, decision metadata, and immutable original due dates.

| Field | Type | Required | Allowed values / units | Uniqueness | Validation rule |
|---|---|---|---|---|---|
| `extension_id` | string | Required | Free text / identifier | Primary key | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies; duplicates rejected |
| `asset_id` | string | Required | Free text / identifier | Not unique | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies |
| `calibration_id` | string | Required | Free text / identifier | Not unique | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies |
| `original_due_date` | date string | Required | YYYY-MM-DD | Not unique | Must be non-empty |
| `extended_due_date` | date string | Required | YYYY-MM-DD | Not unique | Must be non-empty |
| `extension_days` | integer | Required | Positive whole days | Not unique | Must be non-empty; value > 0 |
| `reason` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `requested_by` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `requested_at` | timestamp string | Required | YYYY-MM-DD HH:MM:SS | Not unique | Must be non-empty |
| `approval_status` | string | Required | APPROVED | REJECTED | PENDING | Not unique | Must be non-empty; only APPROVED extensions affect use decisions |
| `decided_by` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `decision_reason` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `decided_at` | timestamp string | Required | YYYY-MM-DD HH:MM:SS | Not unique | Must be non-empty |

## `alerts`

Operational alerts derived from failed calibrations, blocked uses, and labelled anomalies.

| Field | Type | Required | Allowed values / units | Uniqueness | Validation rule |
|---|---|---|---|---|---|
| `alert_id` | string | Required | Free text / identifier | Primary key | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies; duplicates rejected |
| `asset_id` | string | Optional | Free text / identifier | Not unique | May be blank/NULL; referenced IDs must exist in the parent table where a declared FK applies |
| `entity_type` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `entity_id` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `alert_type` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `severity` | string | Required | LOW | MEDIUM | HIGH | Not unique | Must be non-empty |
| `description` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `status` | string | Required | OPEN | ACKNOWLEDGED | RESOLVED | Not unique | Must be non-empty |
| `created_at` | timestamp string | Required | YYYY-MM-DD HH:MM:SS | Not unique | Must be non-empty |

## `audit_records`

Append-only history of record creation and deliberate edge-case injection.

| Field | Type | Required | Allowed values / units | Uniqueness | Validation rule |
|---|---|---|---|---|---|
| `audit_id` | string | Required | Free text / identifier | Primary key | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies; duplicates rejected |
| `entity_type` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `entity_id` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `action` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `from_state` | string | Optional | Free text / identifier | Not unique | May be blank/NULL |
| `to_state` | string | Optional | Free text / identifier | Not unique | May be blank/NULL |
| `timestamp` | timestamp string | Required | YYYY-MM-DD HH:MM:SS | Not unique | Must be non-empty |

## `ground_truth`

Separate evaluation labels; exclude this dataset from model input features.

| Field | Type | Required | Allowed values / units | Uniqueness | Validation rule |
|---|---|---|---|---|---|
| `ground_truth_id` | string | Required | Free text / identifier | Primary key | Must be non-empty; referenced IDs must exist in the parent table where a declared FK applies; duplicates rejected; evaluation-only, never an input feature |
| `entity_type` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `entity_id` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `issue_type` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `details` | string | Required | Free text / identifier | Not unique | Must be non-empty |
| `expected_decision` | string | Required | Free text / identifier | Not unique | Must be non-empty |

## Relationships and cardinality

- InstrumentType 1:N Asset; InstrumentType 1:N CalibrationPlan.
- CalibrationPlan 1:N Asset; each asset references one type and one plan.
- Asset 1:N CalibrationEvent and 1:N ProductionUse.
- Supplier 1:N CalibrationEvent.
- CalibrationEvent 0:1 Certificate (certificate gaps are intentionally labelled), 0:N WorkOrder, and 0:N CalibrationExtension.
- CalibrationExtension N:1 Asset and N:1 CalibrationEvent; only APPROVED records affect decisions.
- Alert and AuditRecord use entity_type/entity_id polymorphic references; their IDs are validated against the documented entity map.
- GroundTruth is kept in separate CSV/JSON exports and is not included in `datasets.json` input data.

## Business rules and derived values

1. `due_date_calculated = event_date + calibration_plans.interval_days`; one explicitly labelled edge case intentionally violates this.
2. Use decisions select the latest calibration event at or before use time. A failed latest calibration blocks use; no prior calibration requires review.
3. For a passing calibration, use is allowed through due date plus plan grace days. An approved extension may extend that deadline; use during the extension-only window is labelled `ALLOWED_EXTENSION`.
4. Failed calibrations require a corrective work order and impact assessment except for the one explicitly labelled negative scenario.
5. Certificate asset must match its calibration event; issue/validity dates must be chronologically consistent.
6. Downtime hours must equal the duration between downtime_start and downtime_end. Ground-truth labels describe deliberate exceptions and must not be silently repaired.
