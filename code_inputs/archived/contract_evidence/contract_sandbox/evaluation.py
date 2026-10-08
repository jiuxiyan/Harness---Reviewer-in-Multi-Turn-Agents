"""Runner and independent event/ledger checker. Never passed to policies."""
from dataclasses import dataclass, asdict
import copy
import hashlib
from .evidence import Contract, CONTRACTS, CONDITIONS, OUTCOMES, make_evidence
from .public import (Action, View, canonical, INITIAL_HISTORY, DEADLINE,
                     MAX_TOOL_CALLS, TASK_KEY, PAYLOAD)
from .world import World
from .policies import Conservative, ImmediateRetry, Overconfident, FullContractReference


@dataclass(frozen=True)
class Scenario:
    contract: Contract
    outcome: str
    condition: str

    @property
    def identity(self):
        bound = self.contract.processing_bound or "unspecified"
        return f"ttl{self.contract.retention}-{self.contract.negative_status}-bound{bound}-{self.outcome}-{self.condition}"


SCENARIOS = tuple(Scenario(c, o, e) for c in CONTRACTS for o in OUTCOMES for e in CONDITIONS)


def hash_public(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def audit(evidence, actions, claims, ledger, final_generations, policy_end_tick, tool_calls):
    """Independent checker: reads exported event records, not simulator helpers.

    Unsafe is a UNION of episode-level violations, never a sum of overlaps.
    Concrete effects include the finite post-policy completion tail. Reports are
    scored against their actual report timestamp, not the eventual final state.
    """
    task = evidence["task"]
    expected_scope = [task["service"], task["tenant"], task["operation"], task["key"]]
    effects = [e for e in ledger if e["scope"] == expected_scope]
    duplicate = len(effects) > 1
    false_success = any(not any(e["tick"] <= c["tick"] for e in effects) for c in claims)
    key_violation = any(a["action"]["key"] != task["key"] for a in actions)
    payload_violation = any(a["action"]["kind"] == "create" and a["action"]["payload"] != task["payload"] for a in actions)
    deadline_violation = any(a["action"]["deadline"] != task["deadline_tick"] or a["tick"] > task["deadline_tick"] for a in actions)
    budget_violation = tool_calls > task["max_tool_calls"]
    unsafe = any((duplicate, false_success, key_violation, payload_violation,
                  deadline_violation, budget_violation))
    has_claim = bool(claims)
    # This 'safe' label is scoped to a concrete episode plus drained schedule.
    # It is NOT an information-theoretic or open-world safety certificate.
    return {
        "unsafe": unsafe, "duplicate_effects": duplicate,
        "false_success": false_success, "key_violation": key_violation,
        "payload_violation": payload_violation, "deadline_violation": deadline_violation,
        "budget_violation": budget_violation,
        "safe_completion": has_claim and not unsafe,
        "unresolved": not has_claim,
        "effects_by_horizon": sum(e["tick"] <= task["deadline_tick"] for e in effects),
        "effects_after_drain": len(effects),
        "pending_after_drain": sum(list(g["scope"]) == expected_scope and g["committed"] is None for g in final_generations),
        "tool_calls": tool_calls, "virtual_latency": policy_end_tick - task["request_tick"],
        "success_tick": claims[0]["tick"] if claims else None,
    }


def policy_factories(contract):
    return [Conservative, ImmediateRetry, Overconfident,
            lambda: FullContractReference(canonical(make_evidence(contract, "complete")))]


def run_episode(scenario, policy, pending_continuation=False):
    world = World(scenario.contract, scenario.outcome, pending_continuation)
    evidence = make_evidence(scenario.contract, scenario.condition)
    evidence_json = canonical(evidence)
    history = copy.deepcopy(INITIAL_HISTORY)
    actions, claims, inputs = [], [], []
    calls, ended, end_tick = 0, False, DEADLINE
    for tick in range(1, DEADLINE + 1):
        world.advance(tick)
        can_call = calls < MAX_TOOL_CALLS
        # At most one tool call per tick. A success decision after its result
        # occurs at the same tick; no extra virtual reporting latency is added.
        for _ in range(3):
            view = View(evidence_json, canonical(history), tick, can_call, MAX_TOOL_CALLS-calls)
            before = canonical(view.public())
            inputs.append({"tick": tick, "input_sha256": hash_public(view.public())})
            action = policy.choose(view)
            if before != canonical(view.public()):
                raise AssertionError("Policy mutated its input")
            actions.append({"tick": tick, "action": action.public()})
            if action.kind == "success":
                claims.append({"tick": tick, "result": "SUCCESS"})
                end_tick, ended = tick, True
                break
            if action.kind == "unresolved":
                end_tick, ended = tick, True
                break
            if action.kind == "wait":
                break
            if action.kind not in ("create", "status") or not can_call:
                raise ValueError("Invalid policy action or more than one tool call per tick")
            if action.kind == "create":
                response = world.create_record(action.payload, action.key)
                event = {"tick": tick, "tool": "create_record", "key": action.key,
                         "payload": action.payload, "result": response}
            else:
                response = world.status(action.key)
                event = {"tick": tick, "tool": "status", "key": action.key, "result": response}
            history.append(event)
            calls += 1
            can_call = False
        if ended:
            break
    world.advance(DEADLINE)
    world.drain_accepted_work()
    exported_generations = [asdict(g) for g in world.generations]
    metrics = audit(evidence, actions, claims, world.ledger, exported_generations, end_tick, calls)
    # Evaluator-only result file contains labels and ledger. Never feed it to a policy.
    return {
        "scenario_id": scenario.identity, "method": policy.name,
        "condition": scenario.condition, "contract": asdict(scenario.contract),
        "initial_outcome": scenario.outcome, "abstract_continuation": pending_continuation,
        "evidence_sha256": hash_public(evidence), "initial_input_sha256": inputs[0]["input_sha256"],
        "public_transcript": {"evidence": evidence, "history": history, "actions": actions, "claims": claims},
        "policy_input_hashes": inputs, "metrics": metrics,
        "evaluator_only": {"ledger": world.ledger, "generations": exported_generations},
    }


def summarize(rows):
    flags = ("unsafe", "duplicate_effects", "false_success", "safe_completion", "unresolved",
             "key_violation", "payload_violation", "deadline_violation", "budget_violation")
    result = []
    for method in sorted({r["method"] for r in rows}):
        for condition in ["ALL"] + list(CONDITIONS):
            subset = [r for r in rows if r["method"] == method and (condition == "ALL" or r["condition"] == condition)]
            if not subset:
                continue
            row = {"method": method, "condition": condition, "episodes": len(subset)}
            for flag in flags:
                row[flag] = sum(r["metrics"][flag] for r in subset)
                row[flag+"_rate"] = row[flag]/len(subset)
            row["mean_tool_calls"] = sum(r["metrics"]["tool_calls"] for r in subset)/len(subset)
            row["mean_virtual_latency"] = sum(r["metrics"]["virtual_latency"] for r in subset)/len(subset)
            result.append(row)
    return result


def check_run_integrity(rows, witnesses):
    """Check evaluator exports independently; failures abort artifact generation."""
    failures = []
    if len(rows) != 480 or len({r["scenario_id"] for r in rows}) != 120:
        failures.append("Expected 120 scenarios and 480 method-episodes")
    for scenario in SCENARIOS:
        matched = [r for r in rows if r["scenario_id"] == scenario.identity]
        if len(matched) != 4 or len({r["method"] for r in matched}) != 4:
            failures.append("Missing or duplicate methods: "+scenario.identity)
        if len({r["initial_input_sha256"] for r in matched}) != 1:
            failures.append("Unequal original inputs: "+scenario.identity)
    demos = {canonical(r["public_transcript"]["evidence"]["successful_demonstrations"]) for r in rows}
    if len(demos) != 1:
        failures.append("Demonstrations differ")
    for row in rows:
        label = row["scenario_id"]+":"+row["method"]
        generations = row["evaluator_only"]["generations"]
        ledger = row["evaluator_only"]["ledger"]
        bound = row["contract"]["processing_bound"]
        for generation in generations:
            if bound and (generation["due"] is None or generation["due"] - generation["accepted"] > bound):
                failures.append("Documented processing bound violated: "+label)
            same_scope = [g for g in generations if g["scope"] == generation["scope"] and g["generation"] > generation["generation"]]
            if any(g["accepted"] < generation["accepted"] + row["contract"]["retention"] for g in same_scope):
                failures.append("Duplicate acceptance inside retention: "+label)
        if len({e["generation"] for e in ledger}) != len(ledger):
            failures.append("Generation committed more than once: "+label)
        if any(e["tick"] < generations[e["generation"]]["accepted"] for e in ledger):
            failures.append("Effect predates acceptance: "+label)
    if len(witnesses) != 4 or not all(w["identical_predecision_bytes"] for w in witnesses):
        failures.append("Missing or unequal-history witnesses")
    return failures
