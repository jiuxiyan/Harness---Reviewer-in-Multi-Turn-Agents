# Licensing and external data

## Project-authored material

The implementation, tests, research summaries, manuscript and overview artwork in this transfer were authored for this project. This input archive does not invent a new project license grant. No license is currently specified for original code, documents or figures; no new license grant is made by this release.

## Official benchmark

The implementation references [Sierra Research tau2-bench](https://github.com/sierra-research/tau2-bench/tree/4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699), package namespace tau2, at commit `4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699`. The inspected upstream license is MIT, Copyright (c) 2025 Sierra Research; its exact notice is preserved in `third_party/tau2-bench-LICENSE.txt`.

This integrated repository vendors the 281 exact allowed official code/data files under `code_inputs/reviewer_pilot/upstream/`, retaining the upstream MIT notice. A pinned allowlist and a verification-only fetch recipe are supplied. Synthetic names, telephone values and tool IDs used by tests are public fake benchmark fixtures. The redistributed files are the reviewed pinned allowlist; optional or separately licensed assets are not added.

The dependency lock is fetched from the official pinned source. Dependency packages retain their own licenses and are not bundled. Fonts named by document generators are not redistributed and retain their owners' terms.

## Historical external datasets

The fixed-setup audit used the [swe-agent-subset-selection-vectors dataset](https://huggingface.co/datasets/Mahmoud-queens/swe-agent-subset-selection-vectors). Raw matrices, repository maps, vectors, trajectory identifiers and task-level derived rows are not included. Public accessibility does not establish a redistribution license. Check the exact version's terms before acquiring or republishing data.

The natural-evidence feasibility audit used published trajectory sources referenced in `docs/history/`. No raw conversations, model reasoning, task-level annotations or trajectory excerpts are transferred. Only aggregate counts and source-grounded research conclusions are included.

Literature documents contain paraphrased research comparisons and primary-source citations, not full copied papers. They are dated assessments rather than guarantees of exhaustive novelty or independently reproduced results.
