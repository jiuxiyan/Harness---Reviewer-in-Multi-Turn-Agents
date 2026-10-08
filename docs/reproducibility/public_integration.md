# Public integration migration

Inputs were extracted from reviewed Git commit
`87d665519223aa97c2a52ed9fa3ce9c59545cdd0` on `prep/research-inputs`.
All archive SHA-256 digests matched before extraction:

| Archive | SHA-256 |
| --- | --- |
| Research/source | `9176e5ebbb0ed5d9f1e1460d0727811fafb8f85560d5887dcac6c78411ccb02d` |
| Experiment plan | `53f95af3b40aad95f21c5f3b3e9792993641938e3cd6fe90a012ad91b4ca37cb` |
| Official source supplement | `197a8ccd0a91f74f63f3f64c6daf3b398043374216dba0e0d737bdcb8af79843` |

The final DOCX/PNG/SVG and manuscript are preserved exactly. Original transfer
hash inventories live in `docs/provenance/`; they describe the inputs, not this
modified release. `PUBLIC_MANIFEST.json` describes the public release instead.
The public integration binding is not a historical preregistration and never
inherits a prior PASS flag.

Historical implementation layers remain siblings in `code_inputs/`. The
controller and lifetime launchers now verify `PUBLIC_PACKAGE_MANIFEST.json`
against current source/spec files rather than omitted historical runtime
manifests. Lifetime uses `public_integration_freeze.json`, binding the public
manuscript and scientific protocol. Its binding test was renamed accordingly.
Existing model/network guards are unchanged. Their old live-denial behavior
is retained and is distinct from the new local runner.

`tools/offline_checks.py` regenerates seven official script checkpoints, fourteen
fresh-process restores, the READ-tool summary and both READ-probe replicates,
then runs intervention/controller/lifetime suites sequentially. New launchers
must not run concurrently with dependency-mutating fixture regeneration: their
integrity checks intentionally reject such changes.

The new runner has its own strict schema and CPU-local HTTP adapter. Planning
configurations under `docs/planning/configs/` remain design examples; executable
configs are at root `configs/`. The complete paper study has not been silently
reduced to current software scope; see `docs/CAPABILITIES.md` for differences.
