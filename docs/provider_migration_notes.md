# Provider Migration Notes (Engineer-Only)

## Current State
- Primary provider: `epo`
- Fallback provider: `lens`
- Provider selected via `PATENT_PROVIDER` (default: `epo`)

## Identifier Contract

All normalized records must follow:
- `record_id`: canonical app identifier (always populated)
- `lens_id`: nullable, populated only for Lens records
- `epo_id`: nullable, populated only for EPO records (DOCDB-style)

Additional provider metadata:
- `provider_name`
- `provider_record_id`
- `provider_record_url`
- `provider_api_url`
- `is_fallback` (set by orchestration)
- `fallback_reason` (when fallback is triggered)

## Routing and Fallback

- Search orchestration runs against primary provider first.
- On primary failure, the fallback provider is attempted.
- Records are stamped with fallback metadata when fallback is used.

## UI and Linking Rules

- UI should render provider URLs only from `provider_record_url`.
- UI must not synthesize provider URLs from IDs.
- If URL is missing, show a non-blocking “link unavailable” state.

## Deprecation Readiness (Lens)

Criteria to deprecate Lens fallback:
1. EPO success rate stable at target SLO for multi-language searches.
2. Acceptable parity on relevance distribution and analyst triage volume.
3. No critical blocking gaps in legal-status enrichment for priority workflows.

Planned deprecation steps:
1. Warn on fallback usage in logs and docs.
2. Disable fallback by default via config flag.
3. Remove Lens connector from active runtime path.
4. Remove Lens-only compatibility fields in final major cleanup.

## Configuration Reference

Required for EPO primary:
- `PATENT_PROVIDER=epo`
- `EPO_CONSUMER_KEY`
- `EPO_CONSUMER_SECRET`
- Optional: `EPO_OPS_BASE_URL`, `EPO_OPS_AUTH_URL`, `EPO_REQUEST_TIMEOUT_SECONDS`

Optional fallback:
- `LENS_ORG_API_TOKEN`

## Validation Checklist

- Confirm provider selection and fallback logs in one search run.
- Confirm all assessment rows include `record_id`.
- Confirm EPO records have `epo_id` and nullable `lens_id`.
- Confirm Lens fallback records have `lens_id` and nullable `epo_id`.
- Confirm external links render only when `provider_record_url` is present.
