> Historical component documentation. See the current integration notes before running. Referenced runtime results and old internal reports are not transferred; bounded aggregate validation is in docs/validation.

# Advice lifetime controls, offline stage

This directory is a new overlay on the frozen controller receipt adapter. It does
not rename or overwrite old results. In this package P0 means the frozen adapter's
raw persistent packet treatment; P is a new treatment with a neutral status header.
All examples, reviewer packets, and actor/user continuations are scripted fixtures.
No effectiveness, natural-frequency, provider-token or causal claim is supported.

## Reproduce

With the unchanged sibling reviewer_pilot, reviewer_interventions and
controller_receipt_adapter directories and the existing private venv in place:

    python code_inputs/advice_lifetime_controls/launch.py

The launcher uses the previously installed venv, a sanitized credential-free
environment, -I -B, and the existing guard before upstream imports. It checks the
three frozen manifests, all 281 official source entries, the pre-execution plan
and final paper inputs. It writes only this directory's results/private runtime.
Never run worker.py or import upstream directly. No installation is necessary.
Application-level network/model guards are not a kernel network sandbox.

## Operational contract

1. Restore the original supported checkpoint, then bind the frozen receipt adapter.
2. Capture one raw reviewer fixture with explicit public declaration before action
   execution. Keep every malformed, unsupported, unchanged or violating draw.
3. Execute the accepted selected action exactly once; malformed/action-out-of-scope
   draws take original-action/no-packet fallback. A missing/malformed declaration
   is invalid. A well-formed mixed/ongoing/unresolved declaration remains available
   and cannot close. Tool errors are actual errors, never relabeled as bad format.
4. First P/R/C requests have identical packet bytes, neutral header, role, position,
   tools/config and factual receipt. Render attempts are not valid responses.
5. Advance one shared valid actor response and all intervening native events to the
   next actor boundary. Save complete state, user events, queues, budgets and RNG.
6. Restore each branch freshly. C changes only its fixed status sentence when the
   predeclared target call actually returned successfully. R stops attaching the
   whole packet and header. P continues attaching both. User constraints, native
   history and independent factual receipt remain untouched.
7. Save/recover the policy context together with the underlying adapter checkpoint.
   Native user events have explicit fixture capture identities. Physical fixture
   usage is deduplicated across copies, while deployment branches each retain their
   logical shared cost. All TEST_UNITS are artificial, not real token or dollar data.

The closed status means a call requirement was fulfilled. It does not mean a goal
was restored, reviewer advice was correct, or the user task is complete. Scope
semantics come from declared public fields. Outcome-blind semantic violations are
logged, not hidden behind an oracle or discarded. A misleading action-local field
can still close even if its prose is mixed. This is an explicit limitation.

The alternative-neutral sentence is a read-only counterfactual render probe. It is
not an added experimental arm or a finding about behavior. Fixed-width ASCII status
sentences make character/UTF-8 lengths equal; provider token lengths are unknown.

## File map

- PLAN.md and plan_freeze.json: pre-execution contract and paper-input hashes
- lifetime.py: draw capture, scope gate, projection, state/restore and usage overlay
- test_lifetime.py: concrete scripted invariant tests and fresh-process probes
- launch.py, worker.py: guarded launch and verification
- results/run_status.json: authoritative latest aggregate status
- results/integrity.json: tested source hashes and frozen dependency checks
- results/tests.json and stderr.txt: named test results
- results/process_restart.json: independent-process second/third-boundary checks
- results/demonstration.json: labeled request/receipt/draw/accounting example
- REVIEW.md and REPORT.md: independent review disposition and bounded conclusions

Private full checkpoints remain in .runtime and are not included in the archive.
The bundle needs its existing pinned dependencies; it is not a standalone installer.

## Before any API stage

Separate authorization is still required for an exact provider/model and a capped
format-test budget. Existing live entry points remain unconditionally blocked.
A provider-specific mapping, actual request capture, role/order retention tests,
provider token matching, SDK retry/cost accounting, and natural actor/reviewer/user
continuations are not implemented here. The limited scripted shared-prefix state
checks do not validate stochastic model state or arbitrary tools/checkpoints.
No new benchmark, extra hypothesis, mixed-scope semantic extension, or natural
experiment follows automatically from this package.
