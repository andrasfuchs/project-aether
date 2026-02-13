# EPO OPS Known Gaps (Engineer Notes)

## Scope
This document tracks known parity gaps between the legacy Lens provider and the current EPO OPS provider implementation.

## 1) Query Semantics Gaps

### 1.1 Boolean semantics are best-effort only
- Lens implementation used JSON DSL with explicit `must` / `should` / `must_not` blocks.
- EPO OPS implementation uses CQL approximation:
  - include terms: `ti/ab/cl` OR logic
  - exclude terms: `NOT` over `ti/ab/cl`
- Result: some precision/recall differences are expected.

### 1.2 Date filtering syntax variability
- EPO CQL date range syntax can vary by backend support profile.
- Current implementation uses `pd within "YYYYMMDD YYYYMMDD"`.
- If account/tenant behavior differs, empty result sets may occur even for valid searches.

### 1.3 Jurisdiction filtering is heuristic
- Current logic uses publication number prefix pattern (`pn=CC*`).
- This is not equivalent to Lens jurisdiction field filtering in all cases.

## 2) Field Coverage Gaps

### 2.1 Claims are often absent in search payloads
- OPS search feed frequently returns bibliographic content without full claims text.
- Current mapping sets `claims` empty when unavailable.

### 2.2 Legal status is placeholder-level in baseline flow
- Existing baseline search mapping sets:
  - `legal_status.patent_status = "UNKNOWN"`
  - `legal_status.events = []`
- Rich legal status requires additional OPS legal endpoints and per-record calls.

### 2.3 Classification extraction is less normalized
- OPS XML can return classification structures in multiple forms.
- Current mapping extracts text from available nodes but may miss edge variants.

## 3) Link Availability Gaps

### 3.1 Provider record URLs are feed-dependent
- UI now uses provider-supplied URLs only.
- If OPS feed entry omits link elements, `provider_record_url` is `None`.
- Behavior: UI intentionally shows no external link in this case.

## 4) Throughput and Reliability Gaps

### 4.1 Multi-language throughput can degrade with fallback
- EPO primary + Lens fallback is enabled.
- If EPO intermittently fails per language, fallback may produce mixed-provider batches.

### 4.2 Rate and fair-use limits differ from Lens
- OPS quota/fair-use policy differs from legacy Lens limits.
- Existing global request-per-minute settings are conservative defaults and may require tuning.

## 5) Data Model Migration Gaps

### 5.1 Transitional dual identifiers
- Canonical ID: `record_id`.
- Provider IDs:
  - `lens_id` (nullable, Lens only)
  - `epo_id` (nullable, EPO only)
- Temporary compatibility still exists in legacy code paths and artifacts.

## 6) Recommended Next Engineering Iterations

1. Add dedicated legal-status enrichment for top-N candidates only (to control API cost).
2. Add provider-specific integration tests with XML fixtures for parser hardening.
3. Add explicit query diagnostics in logs (CQL, range, result counts, provider).
4. Add deterministic fallback policy metrics (`is_fallback`, `fallback_reason`) dashboard.
5. Complete deprecation pass on Lens-specific labels after stabilization period.
