# Public-transfer content review

The transfer uses an explicit file allowlist. It excludes virtual environments, caches, runtime homes, whole checkpoints, raw trajectories, external label datasets, secret configuration, credentials, operational logs, raw conversation history, unedited research scratch reports and earlier archive bundles.

Retained content is project-authored source/tests, public-facing specifications, synthesized research decisions, aggregate offline-check counts, pinned official source hashes/license, and the exact final paper/overview. A single machine-specific uv location in the installer was changed to a PATH lookup and is disclosed in source provenance. Public benchmark source IDs and content hashes are reproducibility identifiers, not private account identifiers.

The final DOCX was inspected as an archive: document properties contain the public repository author's name and generic office metadata; no comments, tracked-change history, embedded external files, private URLs or machine paths were found. Its bibliography custom XML contains only an empty standard bibliography record. The final paper and graphics remain byte-for-byte unchanged.

Before final GitHub publication, rerun the repository-level scan after integration, including generated artifacts and test fixtures. This review applies only to the listed transfer bytes and cannot certify later files or future model outputs. Never commit newly generated private evaluation snapshots or provider request/response logs by default.
