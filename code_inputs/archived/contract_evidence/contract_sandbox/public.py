"""Only these immutable JSON-shaped values cross into a policy.

No world object, evaluator identity, random seed, outcome, or ledger is exposed.
Python module boundaries are an audit aid, not a security sandbox.
"""
from dataclasses import dataclass
import json
from typing import Any

DEADLINE = 6
MAX_TOOL_CALLS = 6
TASK_KEY = "request-001"
PAYLOAD = "record-value"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class Action:
    kind: str
    key: str = TASK_KEY
    payload: str = PAYLOAD
    deadline: int = DEADLINE

    def public(self) -> dict:
        return {"kind": self.kind, "key": self.key,
                "payload": self.payload, "deadline": self.deadline}


@dataclass(frozen=True)
class View:
    """Policy gets a fresh serialized snapshot, never a mutable world reference."""
    evidence_json: str
    history_json: str
    tick: int
    can_call: bool
    calls_remaining: int

    @property
    def evidence(self) -> dict:
        return json.loads(self.evidence_json)

    @property
    def history(self) -> list:
        return json.loads(self.history_json)

    def public(self) -> dict:
        return {"evidence": self.evidence, "history": self.history,
                "tick": self.tick, "can_call": self.can_call,
                "calls_remaining": self.calls_remaining}


def latest_observation(view: View) -> dict:
    return view.history[-1]


def fixed_evidence() -> dict:
    return {
        "task": {"service": "records", "tenant": "example-tenant",
                 "operation": "create_record", "key": TASK_KEY,
                 "payload": PAYLOAD, "request_tick": 0,
                 "deadline_tick": DEADLINE, "max_tool_calls": MAX_TOOL_CALLS,
                 "budget_counts": "recovery calls only; initial call excluded"},
        "fixed_guarantees": [
            "Keys are scoped by service, tenant, operation, and key.",
            "A key is permanently bound to its first accepted payload; a different payload conflicts.",
            "Retention starts at the first accepted request for a deduplication generation.",
            "ACK confirms acceptance, not commitment.",
            "While a deduplication generation is retained, the same key never creates a second effect, including while pending.",
            "At the exact retention boundary the deduplication guarantee has ended.",
            "Expiry does not cancel pending work or erase committed effects.",
            "COMMITTED is authoritative evidence of a durable effect; effects do not disappear.",
            "A documented processing bound guarantees successful durable commitment within that many ticks after acceptance; without one, no finite commitment time is guaranteed.",
            "The initial TIMEOUT gives no evidence about acceptance or commitment.",
            "The initial request is processed at tick 0; there are no concurrent external writers or delayed network arrivals.",
        ],
        "successful_demonstrations": [{
            "task": {"key": "demo-key", "payload": "demo-value"},
            "events": [
                {"tick": 0, "tool": "create_record", "result": "ACK"},
                {"tick": 8, "tool": "status", "result": "COMMITTED"},
            ],
            "note": "A separate reset run with relative ticks; a successful sample, not a timing or generalization guarantee.",
        }],
    }


INITIAL_HISTORY = [{"tick": 0, "observed_tick": 1,
                    "tool": "create_record", "key": TASK_KEY,
                    "payload": PAYLOAD, "result": "TIMEOUT"}]
