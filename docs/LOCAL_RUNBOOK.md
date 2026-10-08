# Tested local runbook

Use the exact setup and dry-run commands in the root README on Linux/Python
3.12. Setup needs ordinary PyPI access and official `uv`; subsequent dry-runs,
tests, analysis and export require no credentials or network. The committed
source allowlist makes a second GitHub download unnecessary.

1. Run `python3 tools/public_manifest.py --check` before setup. This checks the
   public release files and all 281 upstream files without importing them.
2. Run both `install_locked.py` commands from README. These install unchanged
   official locked wheels plus the hash-pinned websockets import gap. Do not
   run the upstream broad test/evaluation commands: they include unrelated
   optional/live integrations. This repository's test commands are offline.
3. Validate and dry-run `configs/wire-smoke.json` into a fresh directory. Inspect
   `status.json`: `evidence_kind=scripted_fixture`, `real_model_calls=0`. Analysis
   should report `model_outcomes=not_run` and null effect estimates.
4. Run `configs/natural-pilot.json` with `--mode dry-run` to exercise two common
   segments, two independent suffixes and seven implemented arms on task 0.
   This is still an authored fixture.
5. If you choose live execution, configure `MODEL_API_BASE_URL`, `MODEL_API_KEY`,
   `ACTOR_MODEL`, `REVIEWER_MODEL`, `USER_MODEL` in your own local shell or secret
   manager. The supplied `.env.example` documents names only; no dotenv loader
   runs. Use HTTPS and a provider supporting the documented nonstreaming Chat
   Completions fields. Unsupported formats fail visibly. Never paste a key into
   a command, configuration JSON, issue, or result report.
6. Explicitly add `--mode live` to the run command. Start with wire-smoke, then
   examine private outgoing payloads, role/tool pairing, request usage, receipt
   and P/C status changes before a pilot. Real-provider compatibility has not
   been measured by this release. Live actor/user outputs are newly generated;
   the mock policy is never substituted when a real request fails.
7. Analyze only settled runs and inspect missingness, task/family counts and
   coverage before interpretation. Use `export` to a new local staging folder;
   review aggregates before any sharing. Export is not publication.

`configs/confirmatory-roots.json` and `configs/end-to-end.json` intentionally
return exit 2. The former also reports missing delta, epsilon and sample size;
all exposed tasks are ineligible. Do not fill dummy values to force a claim.
S is explicitly unsupported. Consult the paper and full planning documents to
complete the research design before implementing these stages.

Every physical retry is separately recorded. Unknown billing/response outcomes
remain unknown, with no automatic retry of ambiguous network loss. There is no
mandatory token ceiling or assistant approval step. Prices/currency costs and
logical deployment-cost attribution are not implemented; monetary caps reject.

Checkpoints validate fresh-object/fresh-process restoration for supported
state, but there is no user-facing automatic resume command for incomplete API
runs. A new run directory protects prior evidence. Existing directories always
reject rather than overwrite. Keep failed runs private for diagnosis.

The historical four-layer test launchers regenerate their ignored development
fixtures and manifests under `code_inputs/*/results`; those directories are
not experiment observations. Do not commit their raw scripted trajectories.
