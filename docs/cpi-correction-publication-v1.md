# CPI seasonal-adjustment correction publication v1

This is a **source/UI correction authorization**, not a rehash of the frozen v2
five-file receipt. Ordinary CPI mom codes G002600387/G002600388 must not be
labelled SA; reviewed headline SA codes are G005464034/G005464040. Every one of
the 23 heatmap rows needs its own source-metadata audit. Display labels alone do
not establish seasonal adjustment. The contract now has **22 SA + 2 registered
NSA independent mom sources**; the heatmap is **23 rows = 21 SA + 2 NSA**, with
core CPI's SA source counted separately. Report fields are `totalRows=23`,
`saRows=21`, `nsaRows=2`, and `independentMomSources={total:24,SA:22,NSA:2}`.

The only NSA roles are `row:food_away_yoy` / `food_away_mom`:
`G005464519`, original name `美国:CPI:家庭外就餐:当月环比`, and
`row:personal_services_yoy` / `personal_services_mom`: `G005464538`, original
name `美国:CPI:其他个人服务:当月环比`. Both require exact `NSA` classification,
`BLS-202610-footnote-1; single-ordinary-source-history` basis, and the registered
English aliases/BLS IDs (`Food away from home` / `CUUR0000SEFV`;
`Miscellaneous personal services` / `CUUR0000SEGD`). The second row retains
its existing Miscellaneous entity, yoy `G005419508` and weight `G019184837`;
the visible name is 杂项个人服务, not the distinct Other personal services.
English entity aliases are separate fields, never fabricated vendor names.
Each exception uses its full ordinary-source history without splicing old SA
values. Official exception evidence is explicitly limited to **2026-10**, not
whichever month a future refresh displays. That month's NSA footnote does not
establish the classification of every historical or future publication vintage;
`checkedAt` is an actual source acquisition time, not a renewed official-status
review. Total/core and every other role remain
strictly SA; generic total/core mom and arbitrary NSA declarations are rejected.

## Immutable history and test partition

`cpi_correction_snapshot.py` reconstructs the complete public Git set at
`48acc06192cc9c5907acecd640e97328a988a9cc` using the existing a2069 snapshot
plus `cpi-correction-base-48acc06.delta.zip`. The delta contains no nested ZIP;
all existing ZIPs are external references checked by SHA-256. Every reconstructed
file is pinned. The old gates, receipts, tests and snapshots are unchanged.

`run_data_tests.py` still discovers every `scripts/test_*.py`. Exactly the prior
54 historical publication cases and five v2 publication cases run at their exact
approved versions. The old v2 **actual receipt and gate** are also replayed.
Every other test, including current CPI data and UI contracts, stays current.
The runner compares discovered/executed case-ID **multisets**, rejects discovery
errors, skipped/expected-failing cases and incomplete execution. Public snapshot
meta-tests discover only publication modules and run with `python -S` without
private PDF dependencies. No private research archive is copied or modified.

## One-time source approval API

Finalize and audit the real corrected inflation JSON and source files first.
`verify_cpi_correction_publish.make_authorization(...)` returns an authorization
dict and deterministic gzip bytes; it does not write files. Required arguments:

- `source_files`: explicit names within `REVIEWED_SOURCE_FILES`, including all
  `REQUIRED_SOURCE_FILES`. Additional test/fixture names require an explicit
  reviewed change to that named allowlist, never a broad research prefix.
- `sa_bindings`: list of `{role, paths}`. Each path is a JSON traversal list
  (`str` object keys, `int` list indices) addressing original source metadata.
  Roles are all `row:<heatmap-row-id>`, plus `headline:cpi` and `headline:core`.
  Every row must bind both its recent and historical metadata under that row.
  Source metadata requires exact contract `code`, original `name`, provider,
  institution, unit/rawUnit, frequency and seasonal adjustment. Only the two
  roles above require `NSA`; all others require `SA`. Exception basis, English
  alias and BLS series identity are also frozen. The two headline roles
  must bind the reviewed SA headline codes. Multiple paths for headline roles
  can cover the headline/readout and plotted-series source objects together.
- `inflation_change_paths`: explicitly reviewed JSON paths for the correction.
  Only CPI-specific branches and acquisition/quality/raw-reference metadata are
  eligible; everything outside those paths must equal baseline48. These paths
  authorize the **initial correction only**, not future rolling changes.
- `source_audit_sha256`: hash of the actual complete per-row source audit.
- `correction_authorized=False`, `source_review_complete=False`: both default
  false. Set true only after the real source review and explicit authorization.

Write the returned objects to `AUTHORIZATION` and `CORRECTED_REFERENCE` using
canonical JSON for the former. Then set `AUTHORIZATION_SHA256` to the hash of
those **exact authorization bytes**. Until this real binding exists the gate
fails closed. Never create a placeholder approval or synthetic public reference.
The fixtures used in unit tests are synthetic metadata atop real old public
bytes; they are not source evidence, approval or a deployable corrected dataset.

## Per-run publication

Keep the one-time authorization/reference unchanged for later routine five-JSON
refreshes. `make_receipt(root, publication_authorized=False, qa_complete=False,
evidence_hashes=...)` creates a new per-run receipt. The four evidence keys are
`sourceAudit`, `frontend`, `data`, `browser`. Actual publication requires all
four real evidence hashes, explicit authorization and completed page QA.

The current verifier reuses unchanged `macro_refresh_v2_quality.validate_documents`
with the **corrected inflation reference**, plus the other four baseline48 JSON.
This preserves source identity, complete available history/non-null cells,
measurement fields, true calendar gaps, GDP precision closure, employment
reconciliation and PCE weight checks. Classified source metadata is checked explicitly
on every run; merely rehashing incorrect data/source/workflows does not admit it.

The new receipt is `release/cpi-correction-publication-01.json`. Existing receipts
are never rewritten. Node22, CI12000ms and maxWorkers1 remain unchanged; the only
workflow edits replace publication gate commands. Candidate CI remains read-only
and does not publish or declare page QA complete.

## Handoff state

The reviewed correction also covers calendar-safe derived monthly changes,
sample-count disclosure, metric-specific latest readings and original-batch
vintage preservation on raw replay. The public `cpi_sa_bls_2026.json` fixture
contains actual archived October observations and BLS API cross-check evidence,
so regressions do not freeze future live readings to October.

The exception integration preserves the old v2 raw bundle and original 24-source
audit. The v3 mixed-vintage bundle substitutes only the two actual full-history
payloads and their metadata/retrieval times, using the original request manifest.
`__batchGeneratedAt` remains `2026-11-12T11:14:09+00:00`; other sources, PCE
distribution and the other four macro JSON are not relabelled or changed.
Only candidate slices (`heatmapSlice`, `releaseStatus`, `cpiAudit`) in the actual
October regression fixture change; `blsResponse` and `crossCheck` are preserved.
OER's price source describes owners' equivalent rent of primary residence; the
weight source `G019184777` is catalogued as 业主所收租租金 and retains its old
`20260228` observation, not a current official September weight. It is reference
only and is not used in the direct contribution calculation.

Historical contribution differences are **not** certified as explained economic
effects: four direct contributions alone are stacked; the arithmetic difference
remains a disclosed diagnostic, outside the stack. The current candidate has
174 comparable months, 82 outside the 0.052pp published-precision budget; October
2026's 0.048pp difference is within that budget. Historical source-version
alignment remains unverified, rather than being hidden by forced closure.

The implementation intentionally contains no real correction approval, corrected
reference or publication receipt before finalized inputs are supplied. Run final
current data/frontend/build/browser/source checks separately, then generate and
bind the actual artifacts. A passing historical replay proves preservation of
past approvals, **not** correctness or publication of the current correction.
