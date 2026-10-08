# Overview figure specification

Status: pre-experiment schematic. No curve, bar, percentage, or color may imply a measured model result.

Final novelty amendment: add a same-word consumed-status arm C. C preserves the entire reviewer packet at every request while marking the already completed, publicly scoped review slot as consumed. This contrast is required for a claim about advice applicability rather than deletion alone. If space is limited, show P/C/R as the three main rows and move A to the control bracket. R is a fixed one-generation exposure baseline, not an oracle-aware or event-based policy.

## Figure 1: same action, different feedback lifetime

Use a clean horizontal 3-panel figure, approximately 7.1 × 3.0 inches for a two-column paper. The central visual should be the experimental contrast, not a pile of implementation boxes.

### Panel A: unfinished workflow with progress

Title: “A shared checkpoint after progress”

Draw one short timeline with three state markers:

1. Task starts: G1 unmet; G2 unmet.
2. Shared prefix: G1 achieved; G2 still unmet.
3. Pending actor proposal a0.

Under G1: “Still required at completion.” Under G2: “Work remains.” Mark this as a generic schematic rather than a Telecom result.

Draw public history/tools to a small reviewer box. Its one immutable output is Q = (a1, critique). Place “one draw; no outcome-based redraw” underneath.

### Panel B: same correction, three exposure policies

Title: “Hold the executed action fixed”

Q feeds exactly one action/result symbol labeled “Execute a1; record actual result.” A factual receipt then feeds all three branches. Small label: “No hidden predicate enters a prompt.”

Branch rows:

- A, action only: factual receipt at actor boundary 1, then receipt/history at boundaries 2 and 3. No reviewer-packet blocks.
- R, one exposure: reviewer-packet block at boundary 1 only; a small expiry marker before boundary 2; factual receipt/history remain throughout.
- P, persistent: identical reviewer-packet blocks shown active at boundaries 1, 2, and 3. Explain in legend that the blocks depict request exposure, not duplicated trajectory messages.
- C, consumed-status: the exact same packet blocks remain, each with an outlined “slot complete” tag after the public success result. Original user goals are shown in a separate always-present strip. This is a status-label intervention; do not draw factual evidence as disappearing.

For P/R, join the first actor/user segment in one shared light-gray bar, then split before boundary 2. Label: “Common first exposure; fresh suffixes after the split.” Episodes ending in the common segment remain in the denominator.

Include B-bare/B/S as a small bottom bracket labeled “Controls: no review, receipt instrumentation, self-reconsideration.” Do not let these obscure the P/R contrast.

If C becomes the primary deployment policy before live preregistration, label the main contrast “same text, different applicability status” and the R comparison “fixed-TTL exposure baseline.” Do not suggest this decision may be made after seeing outcomes.

### Panel C: private evaluation and outcomes

Title: “Measure what remains lost”

Separate this panel with a dashed vertical firewall labeled “Evaluator only.” Inputs into the panel are actual recorded states, never arrows back to reviewer/controller. Show three small schematic terminal pathways:

- retained: true → true → true;
- transient/recovered: true → false → true;
- delayed unresolved: true → false → false at termination.

All start after the selected action, with the protected goal true. Use neutral shapes plus labels; if using colors, green for retained, amber for transient, red for unresolved. Put “Illustrative trajectories, not observations” below.

At bottom, list only: “Terminal unresolved loss • Official completion • Cost/latency.” Do not put a combined reward score on the diagram.

## Caption, ready to adapt

“Proposed feedback-lifetime experiment. An unfinished tool workflow is checkpointed after a still-required goal has been achieved. One frozen reviewer proposal supplies the same selected action and actual result to action-only (A), one-exposure (R), and persistent-packet (P) continuations. R stops re-presenting reviewer prose after its first actor exposure while preserving factual execution receipts, native history, and the audit log. Private state predicates label immediate preservation, transient recovery, and terminal unresolved loss; they never enter actor or reviewer inputs. The pathways are schematic and do not report model results.”

## Optional Figure 2: synthetic Telecom illustration

Two side-by-side timelines under a conspicuous “Synthetic example” label:

Common prefix: restore mobile data → speed still poor → reviewer selects a line-details READ → active-line result → shared actor asks network mode → user reports 2G-only.

P branch: packet remains → illustrative redundant troubleshooting → data toggled off and not restored → unresolved connectivity loss.

R branch: packet retired, facts retained → illustrative preferred-mode change → public recheck → goals satisfied.

Caption must state that every suffix is authored for explanation, no model generated it, and a single pair cannot establish a causal effect. Prefer Figure 1 if there is room for only one figure.

## Design safeguards

- Never depict R as having an oracle shield or guaranteed safe outcome.
- Never label successful API execution as “correct review.” Use “locally executable” or “immediately preserving,” as appropriate.
- Keep the evaluator arrow one-way.
- Do not show private user-simulator instructions as reviewer inputs.
- Include expiration as an exposure switch, not deletion of the audit log or earlier actor text.
- Use typography large enough for a two-column printed paper; avoid more than 11 substantive boxes.
