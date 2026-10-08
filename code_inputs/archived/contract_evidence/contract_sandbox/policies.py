"""Hand-written controls; no LLM, learning, or hidden evaluator imports."""
from .public import Action, View, latest_observation


def known(evidence, field):
    item = evidence["contract_claims"][field]
    return item["value"] if item["state"] == "known" else None


class Conservative:
    name = "conservative"

    def choose(self, view: View) -> Action:
        latest = latest_observation(view)
        if latest["result"] == "COMMITTED":
            return Action("success")
        if not view.can_call or not view.calls_remaining:
            return Action("wait")
        docs = view.evidence
        ttl = known(docs, "retention_ticks")
        origin = docs["task"]["request_tick"]
        previous_creates = [x for x in view.history if x["tool"] == "create_record" and x["result"] != "TIMEOUT"]
        # One recovery retry, anchored to the earliest possible acceptance. The
        # interval is [first acceptance, first acceptance + TTL), never closed.
        valid = ttl is not None and view.tick - origin < ttl
        terminal_absence = (known(docs, "negative_status") == "terminal" and
                            latest["tool"] == "status" and latest["result"] == "ABSENT")
        if not previous_creates and (valid or terminal_absence):
            return Action("create")
        return Action("status")


class Overconfident:
    """Deliberately faulty, trace-overgeneralizing control, not a proposed method.

    Missing/conflicting retention is guessed as 8; missing/conflicting negative
    status as terminal; missing processing as 2. Additionally mistakes ACK for
    commitment. Known explicit values and 'no finite bound' are kept.
    """
    name = "overconfident_faulty"

    def choose(self, view: View) -> Action:
        latest = latest_observation(view)
        if latest["result"] in ("COMMITTED", "ACK"):
            return Action("success")
        if not view.can_call or not view.calls_remaining:
            return Action("wait")
        claims = view.evidence["contract_claims"]
        ttl = known(view.evidence, "retention_ticks") or 8
        semantics = known(view.evidence, "negative_status") or "terminal"
        process = claims["processing_bound_ticks"]
        assumed_bound = process["value"] if process["state"] == "known" else (None if process["state"] == "no_guarantee" else 2)
        # A fixed one-tick backoff makes the expiry boundary observable.
        if view.tick == 1:
            return Action("wait")
        if (latest["tool"] == "status" and latest["result"] == "PENDING" and
                assumed_bound is not None and view.tick >= assumed_bound):
            return Action("success")  # Fault: converts a guessed bound into a report.
        previous_creates = [x for x in view.history if x["tool"] == "create_record" and x["result"] != "TIMEOUT"]
        negative = latest["tool"] == "status" and latest["result"] == "ABSENT"
        if not previous_creates and (view.tick < ttl or (negative and semantics == "terminal")):
            return Action("create")
        return Action("status")


class FullContractReference(Conservative):
    """Privileged full docs, never hidden state; not an optimal oracle or ceiling."""
    name = "full_contract_reference"

    def __init__(self, full_evidence_json):
        self.full_evidence_json = full_evidence_json

    def choose(self, view):
        # Original public evidence/history/budgets remain equal at the boundary.
        # This extra information disqualifies the reference as an equal-input competitor.
        privileged = View(self.full_evidence_json, view.history_json,
                          view.tick, view.can_call, view.calls_remaining)
        return super().choose(privileged)


class ImmediateRetry:
    """Simple null control: t=1 same-key retry, then poll for actual COMMITTED.

    Uses no evaluator fields. Safe on the chosen TTL>=2 grid, but its retry is
    not justified by omitted-TTL docs, which supply no minimum retention.
    """
    name = "immediate_same_key_retry"

    def choose(self, view):
        if latest_observation(view)["result"] == "COMMITTED":
            return Action("success")
        if not view.can_call or not view.calls_remaining:
            return Action("wait")
        if view.tick == 1:
            return Action("create")
        return Action("status")
