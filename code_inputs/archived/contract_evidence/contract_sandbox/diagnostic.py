"""Finite model-family diagnostic and explicit indistinguishability witnesses.

Not a deployed policy or universal verifier. Unknown processing adds a pending
continuation equivalence class (no commit in the observation window), not a
claim that work never commits. Conflicting clauses are alternatives, not a
conjunction with an empty compatible set.
"""
from copy import deepcopy
from dataclasses import asdict
from .evidence import CONTRACTS, OUTCOMES, Contract, make_evidence, contract_matches
from .public import INITIAL_HISTORY, TASK_KEY, PAYLOAD, canonical, DEADLINE
from .world import World


def compatible_worlds(evidence, observed_history):
    matches = []
    for contract in CONTRACTS:
        if not contract_matches(contract, evidence):
            continue
        for outcome in OUTCOMES:
            # Include the continuation after an initially rejected request too:
            # its later retry may be accepted without any completion bound.
            continuations = [False, True] if contract.processing_bound is None else [False]
            for continuation in continuations:
                world = World(contract, outcome, continuation)
                valid = True
                for event in observed_history[1:]:
                    world.advance(event["tick"])
                    actual = world.create_record(event["payload"], event["key"]) if event["tool"] == "create_record" else world.status(event["key"])
                    if actual != event["result"]:
                        valid = False
                        break
                if valid:
                    matches.append(world)
    return matches


def assess_claim(evidence, history, claim_tick):
    worlds = compatible_worlds(evidence, history)
    possible = []
    for world in worlds:
        world.advance(claim_tick)
        possible.append(bool(world.ledger))
    has_conflict = any(x["state"] == "conflict" for x in evidence["contract_claims"].values())
    return {"compatible_world_count": len(worlds),
            "contains_pending_continuation": any(w.pending_continuation for w in worlds),
            "evidence_status": "UNRESOLVED_CONFLICT" if has_conflict else ("MODEL_INCONSISTENT" if not worlds else "MODEL_COMPATIBLE"),
            "success_supported_in_bounded_model": bool(worlds) and all(possible),
            "success_refuted_in_some_model": any(not x for x in possible),
            "universal_certificate": False}


def observed(world, script):
    history = deepcopy(INITIAL_HISTORY)
    for tick, tool in script:
        world.advance(tick)
        if tool == "status":
            result = world.status(TASK_KEY)
            history.append({"tick": tick, "tool": "status", "key": TASK_KEY, "result": result})
        else:
            result = world.create_record(PAYLOAD, TASK_KEY)
            history.append({"tick": tick, "tool": "create_record", "key": TASK_KEY,
                            "payload": PAYLOAD, "result": result})
    return history


def retry_witness(name, condition, ca, oa, cb, ob):
    ea, eb = make_evidence(ca, condition), make_evidence(cb, condition)
    wa, wb = World(ca, oa), World(cb, ob)
    # Explicit matched pre-decision histories, not just matched initial prompts.
    ha, hb = observed(wa, [(1, "status"), (2, "status")]), observed(wb, [(1, "status"), (2, "status")])
    pre_a, pre_b = canonical({"evidence": ea, "history": ha, "decision_tick": 3}), canonical({"evidence": eb, "history": hb, "decision_tick": 3})
    assert pre_a == pre_b, name
    results = []
    for world in (wa, wb):
        world.advance(3)
        ack = world.create_record(PAYLOAD, TASK_KEY)
        world.advance(DEADLINE)
        world.drain_accepted_work()
        results.append({"contract": asdict(world.contract), "initial_outcome": world.initial_outcome,
                        "retry_result": ack, "effect_count_after_drain": len(world.ledger),
                        "duplicate": len(world.ledger) > 1, "ledger": world.ledger})
    assert results[0]["duplicate"] != results[1]["duplicate"], name
    return {"name": name, "kind": "same_retry_different_safety", "identical_predecision_bytes": True,
            "predecision_public_json": pre_a, "action": {"tick": 3, "tool": "create_record", "key": TASK_KEY, "payload": PAYLOAD},
            "worlds": results, "interpretation": "Shows ambiguity of this delayed retry, not unavoidable failure; waiting remains safe."}


def processing_witness():
    ca, cb = Contract(2, "lagging", 2), Contract(2, "lagging", None)
    ea, eb = make_evidence(ca, "processing_omitted"), make_evidence(cb, "processing_omitted")
    wa, wb = World(ca, "accepted_pending"), World(cb, "accepted_pending", True)
    ha, hb = observed(wa, [(1, "create"), (2, "status")]), observed(wb, [(1, "create"), (2, "status")])
    before_a = canonical({"evidence": ea, "history": ha, "decision_tick": 3})
    before_b = canonical({"evidence": eb, "history": hb, "decision_tick": 3})
    assert before_a == before_b
    wa.advance(3); wb.advance(3)
    assert len(wa.ledger) == 1 and len(wb.ledger) == 0
    return {"name": "processing_omission", "kind": "same_claim_different_truth",
            "identical_predecision_bytes": True, "predecision_public_json": before_a,
            "action": {"tick": 3, "report": "SUCCESS"},
            "worlds": [{"contract": asdict(wa.contract), "effects_at_claim": 1},
                       {"contract": asdict(wb.contract), "effects_at_claim": 0, "pending_continuation": True}],
            "claim_diagnostic": assess_claim(ea, ha, 3),
            "interpretation": "ACK establishes acceptance; an omitted processing guarantee cannot be recovered from successful samples. The sentinel means pending beyond this window, not nontermination."}


def all_witnesses():
    return [
        retry_witness("retention_omission", "retention_omitted", Contract(8, "lagging", 2), "immediate_commit", Contract(2, "lagging", 2), "immediate_commit"),
        retry_witness("status_omission", "status_omitted", Contract(2, "terminal", 2), "rejected", Contract(2, "lagging", 2), "immediate_commit"),
        retry_witness("status_contradiction", "status_contradiction", Contract(2, "terminal", 2), "rejected", Contract(2, "lagging", 2), "immediate_commit"),
        processing_witness(),
    ]
