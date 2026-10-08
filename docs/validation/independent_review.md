# Independent code and protocol review

The release received a separate, read-only agent review of the new runner,
configuration, provider boundary, protocol and tests. The reviewer did not
modify source, read real credentials, or make model/API calls.

Issues found and fixed before the final review:

- Malformed provider JSON is classified after persistence rather than escaping
  the endpoint ledger through unchecked object types.
- Analysis refuses unsettled runs so omitted assignments cannot create narrow
  missingness bounds.
- Initially-true properties are excluded from acquired protected membership.
- Strict replay failures become explicit restore failures.
- Echoed virtual credentials and authorization fields are redacted; received
  and stored response digests are distinct and persisted event hashes verify.
- A terminal common segment is never padded with imaginary missing suffixes
  when a later common segment fails.
- Draw-consumed and intervention-executed state survives the actual production
  fork/restore path, refusing redraw and duplicate execution.

The intermediate reviewer independently ran the offline unit/integration suite (28 outer
unittest cases), and subsequently reran the final guarded integration and
cross-process restore test after the last execution-state fix. The final review
found no remaining blocker for the explicitly bounded READ development release.

This review does not certify real-provider acceptance, broad benchmark support,
confirmation readiness or an empirical result. See the current validation JSON
for the exact final source-tree digest and clean-directory command outcomes.

## V2 extension review

A separate read-only review covered bounded roaming WRITE, all eight arms,
multi-root sampling, frozen confirmation, cost ancestry and explicit recovery.
It identified and prompted fixes to: empty-message validation before native
error handling; cached response model checks; reference failures in confirmation
verdicts; original wall-time inheritance; and cumulative per-logical retry limits.
Multiple/hallucinated tools are model errors; known unsupported WRITEs remain
explicit capability missingness. The reviewer independently ran all eight
recovery tests successfully and found no remaining blocker to clean-directory
acceptance. Capabilities, operational protocol and runbook were checked together.

Final acceptance additionally exercises actual roaming repair and harm,
non-idempotent initialization/history, fresh-process restoration, interrupted
reviewer recovery, and a two-task/four-root/eight-arm fixture. These checks do not
measure provider compatibility or establish an empirical scientific finding.
