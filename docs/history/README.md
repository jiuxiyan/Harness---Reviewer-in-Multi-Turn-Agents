# Research history and claim boundaries

This historical-document collection records the public-facing research decisions behind the pre-experiment reviewer-advice-lifetimes project. It preserves negative findings and the reasons earlier approaches were discontinued, so those exploratory branches cannot be mistaken for evidence supporting the current proposal.

**No formal LLM experiment has been run by this project.** Historical evidence consists of authored deterministic fixtures, an offline audit of publicly released outcome labels, a constructed randomization audit, and a small static audit of existing public trajectories. The public trajectories and outcome labels originate in other researchers' model runs; they are not new runs conducted here.

The current question concerns what happens after a reviewer's local recommendation has executed: should its text remain active, be removed after a fixed exposure, or remain present with its completed scope explicitly marked? That proposal has no measured behavioral result yet.

## Documents

- [Historical branch decisions](RESEARCH_HISTORY.md): questions, verified aggregate findings, rejected interpretations, and stopping decisions for the five earlier branches.
- [Current proposal and related work](CURRENT_PROPOSAL.md): how the research question narrowed, the P/R/C distinction, controls, and evidence still required.
- [Code and dependency map](CODE_MAP.md): candidate independently authored implementation files, protocol inputs, execution dependencies, and packaging cautions.
- [Sources and redistribution boundaries](SOURCES_AND_RIGHTS.md): public data provenance, byte-identification information, and unresolved third-party rights.

## Evidence status

The historical records were completed on 7 October 2026. This synthesis was prepared on 8 October 2026 from those records. Headline numbers were checked against saved aggregate JSON/CSV outputs. No historical computation or model experiment was rerun for this synthesis, and source websites were not reauthenticated. Literature descriptions reflect the cited versions inspected for the recorded literature audit, rather than an exhaustive novelty guarantee.

These documents contain synthesized decision records and aggregate evidence. They do not redistribute downloaded trajectory text, per-task outcome maps, selected task lists, third-party code, or private operational records. Repository-relative filenames in the code map identify reproducibility dependencies, not endorsements of unrestricted redistribution.
