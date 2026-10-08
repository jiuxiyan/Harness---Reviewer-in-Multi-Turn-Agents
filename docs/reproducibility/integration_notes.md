# Integrating the source snapshot into a runnable repository

## Important release boundary

This archive transfers original implementation inputs, not a newly verified portable release. The recorded 36/37/40 checks and seven backend witnesses were executed in the historical prepared environment. Do not label those records as a fresh checkout or CI pass. No historical runtime checkpoint, results trajectory, installed environment or cache is included.

The final repository needs a normal installation path, a safe local experiment configuration, offline fixture regeneration, and CI against the integrated code. Never solve portability by copying the omitted files or weakening privacy/integrity guards.

## Current code chain

Keep `reviewer_pilot`, `reviewer_interventions`, `controller_receipt_adapter` and `advice_lifetime_controls` as sibling source components until imports are deliberately refactored. The layer imports and Path-relative sibling lookups assume this arrangement.

1. `tools/fetch_tau2_source.py` downloads only the 281 entries of the recorded official allowlist, at commit `4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699`, verifies byte length, SHA-256 and Git blob SHA-1, and writes provenance locally. It does not execute source. The expected checkout size is 18,106,301 bytes. The public official MIT notice is included.
2. The historical `install_locked.py` installs unchanged official locked dependencies with uv and hash-pinned import-gap requirements. Its hardcoded installation-tool path has been replaced by a PATH lookup in this transfer. Python 3.12 and the recorded uv.lock were used previously. The launchers still assume POSIX `.venv/bin/python`; a portable project wrapper must address that explicitly. Do not claim Windows support from this snapshot.
3. `backend_checks.py`, `backend_worker.py`, `launch_offline.py` and `run_suite.py` generate seven scripted root snapshots and their fresh-process continuations under the no-model/no-network guard. `task_audit.json` is a safe public-benchmark-derived task index, not a private runtime snapshot. Restore this layer before running dependent tests.
4. `reviewer_interventions/launch.py` checks pinned source and runs 36 wire/privacy/budget fixtures. The preserved `SPEC.md` and its original plan hash remain consistent.
5. `controller_receipt_adapter/launch.py` consumes the two previous layers, checks manifests and runs 37 persistence/rendering/provenance fixtures.
6. `advice_lifetime_controls/launch.py` consumes all three layers and runs 40 same-text status/exposure/persistence/accounting fixtures.

## Historical assumptions that require explicit migration

- Old `BUNDLE_MANIFEST.json` files are omitted because their file lists include omitted historical runtime-derived outputs or internal operational reports. Create **new public-package manifests** from checked source/spec files, with a new version. Do not manufacture old-manifest continuity or silently call a new hash a preregistration.
- The original lifetime `plan_freeze.json` is omitted because it binds an internal delivery receipt and obsolete directory layout. The public final manuscript and exact hashes are present. Replace its input binding with the public paper/protocol paths, update corresponding tests, and record a new public integration freeze.
- `reviewer_pilot/static_audit.py` contains an assertion about the original machine's missing packages and expects historical GitHub response JSON. It is supplied as research source, not a portable bootstrap. Replace that environment assertion and obtain/validate public metadata as needed, or create a focused task-index validator against the supplied source manifest.
- `verify_final.py` expects the historical installed-package inventory and old result schemas. Generate an inventory in the new environment and use a new transparent validation receipt. No old installation stdout or machine paths are transferred.
- The current guards are process-local application guards, not a kernel network isolation proof. Preserve credential-free environments and fail-closed provider entrypoints in offline CI.
- Existing checks use authored actor/reviewer/user fixtures and artificial TEST_UNITS. They do not provide model-token prices, dollar costs, real output retention, provider compatibility or effect estimates.
- The primary scientific comparison is C/P; the older intervention layer's P corresponds to P0 in the lifetime overlay. Preserve this mapping when unifying configuration and result schemas.

## Archived research branches

`contract_evidence` is a stdlib-only deterministic sandbox. `change_replay` is a stdlib-only deterministic synthetic replay/mutation/selection validator. Their small authored fixtures are included. Treat their quantitative outcomes as historical designed checks, not evidence about the current method.

`regression_data_audit` and `decision_validity_audit` require two separately acquired external label files. Raw inputs and task-level output rows are excluded. Original expected hashes and algorithms are provided. The cleaned decision protocol has a new byte hash, so its hardcoded historical protocol hash must be deliberately migrated, not bypassed. Historical aggregate findings and license cautions appear in `docs/history/`.

## Paper reproducibility

The DOCX, overview SVG and PNG are exact final supplied artifacts. `manuscript.txt`, `build_docx.py` and `make_figure.py` are the final source generators. Document generation uses python-docx, and the figure script emits SVG; SVG-to-PNG rendering requires a separately documented renderer. Fonts include Times New Roman and Noto CJK families. No font files are redistributed. Do not claim byte-identical regeneration across office/rendering versions. Re-render and visually inspect all pages after any change; preserve the delivered final binaries until a reviewed replacement exists.

## Suggested release checks

- Source, package and paper hashes; license inventory; privacy/secret scan including DOCX XML and image metadata
- Fresh checkout install with pinned upstream verification
- Regenerate scripted fixtures without model/network calls during test execution
- Run every current unit/integration suite and fresh-process restore test
- Pure-synthetic historical suites when included in the supported release target
- Validate CLI dry-run, missing-config, budget-cap, interruption/resume and fail-closed paths
- Report passed, failed and never-run checks separately; retain truthful no-formal-results status
