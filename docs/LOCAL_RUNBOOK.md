# Local execution and recovery

Use the root README setup on Linux/Python 3.12 with official `uv`. Run from a
checkout. Linux is validated; macOS execution has not been validated. The pinned
`tau2-bench` repository is the τ³ release line, package `tau2==1.0.1`, commit
`4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699`; it is not the earlier τ² paper snapshot.
All supplied dry-runs and tests are offline after dependency setup.

```sh
python3 -m unittest discover -s tests -v
python3 tools/offline_checks.py
python3 -m local_experiments run --config configs/write-smoke.json --output-dir results/write-smoke
python3 -m local_experiments run --config configs/natural-pilot.json --output-dir results/pilot
python3 -m local_experiments analyze --input-dir results/pilot --output-dir results/pilot-analysis
```

The WRITE smoke uses exposed task 4 and a real official roaming state mutation.
The pilot fixture uses two exposed tasks, up to two roots per reference, all
8 arms, two common segments and two suffixes. A cap is not a promise that a
natural trajectory contains that many roots. Inspect `status.json`, coverage,
assignments and per-path costs. Fixtures always have `real_model_calls=0` and
`scripted_fixture`; analysis never turns them into effect evidence.

For user-local live runs, set only the five environment names in `.env.example`
through your normal secret manager, then add `--mode live`. No dotenv loader
runs. Configure sampling and request/time/output limits before execution. HTTPS,
nonstreaming Chat Completions is the only supported wire format. Redirects are
rejected. No real-provider compatibility test was performed during preparation.

## Frozen confirmation

`configs/confirmatory-roots.json` is an intentionally incomplete design template,
not a permanent runner stub. Set delta, epsilon, sample size, task selection,
model identities, repetition counts and budgets **before** freezing. All supplied
witnesses are exposed and cannot serve as heldout confirmation. A metadata-only
manifest has this schema (hash is SHA-256 of canonical sorted compact UTF-8 JSON
of the exact pinned upstream task object):

```json
{"source_commit":"4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699","tasks":[{"task_id":"<exact pinned task ID>","task_sha256":"<canonical task hash>","family_id":"<fault tokens between first ] and [PERSONA:>","research_partition":"heldout_confirmatory"}]}
```

Only fixed-goal Telecom ENV_ASSERTION tasks are supported. Set dataset manifest
and indices, `population=heldout_confirmatory`, and explicitly attest unseen
status after checking your own history. Include every earlier run's
`derived/exposure_manifest.json` in `dataset.exposure_manifests`. Built-in
exposures are always excluded. Near-family normalization removes terminal
on/off polarity and merges enabled/disabled; containment or Jaccard >= 0.5 is
excluded. Confirmation tasks must also share no normalized fault token with
one another. Choose independent units based on substantive knowledge as well;
this lexical rule cannot establish independence.

Set actor/reviewer/user model IDs and `require_reported_model=true`; actual
provider environment IDs and returned model IDs must match exactly. S uses the
actor model. Select a provider/version that reports the frozen identity.

```sh
python3 -m local_experiments freeze --config results/confirm-config.json --output-file results/design-freeze.json
```

Then set `gates.frozen_protocol_receipt` to that path in the same config. This
path alone is excluded from the binding; changing any design, task, exposure,
model or source requires a new freeze before data collection. The freeze is a
local integrity record, **not external preregistration or proof of readiness**.
The natural-coverage and mutation-receipt fields are reserved and reject non-null values; they are not empirical readiness
checks. Keep them null and document substantive readiness independently.

```sh
python3 -m local_experiments validate --config results/confirm-config.json
python3 -m local_experiments run --config results/confirm-config.json --mode live --output-dir results/confirm-001
python3 -m local_experiments analyze --input-dir results/confirm-001 --output-dir results/confirm-analysis
```

A confirmation verdict requires every selected task represented, no reference
failure, no missing endpoints, and the predeclared paired interval criteria.
No-trigger tasks prevent that verdict. Coverage/missingness still must be
reported. This is a root-conditioned fixed-goal study, not episode-start utility
or support for goals that users later revoke. `end-to-end` remains an extension.

## Interrupted or uncertain requests

Stop safely with Ctrl-C. Never overwrite the run. Preserve its private files.
Create a decision template without reading credentials or calling a provider:

```sh
python3 -m local_experiments recovery-plan --input-dir results/interrupted --output-file results/recovery-decisions.json
```

For each unknown request choose `abandon`, or choose `retry` and explicitly set
`accept_possible_duplicate_charge=true`. No option is selected automatically.
A retry after later recorded requests is rejected; it would change the replay
sequence. Retry does not expand the frozen physical/per-request limits. Known
HTTP failures remain their original missing outcomes. A torn journal or changed
source/config/payload fails closed and needs manual diagnosis.

```sh
python3 -m local_experiments resume --config results/original-config.json --input-dir results/interrupted --decisions results/recovery-decisions.json --output-dir results/recovered
```

Add `--mode live` only for resuming a live run. Confirmed responses replay without
new model calls. The original wall-time budget includes the interruption pause;
resume does not silently reset it. Fresh run directories preserve all evidence.

Analyze only settled runs; `export` writes a typed aggregate allowlist into a new
local folder and never uploads. Review aggregates before sharing. Private raw
responses, trajectories, checkpoints and decision files stay ignored.
