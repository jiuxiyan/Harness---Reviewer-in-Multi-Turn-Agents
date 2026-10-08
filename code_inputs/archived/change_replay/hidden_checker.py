"""Frozen, independent goal checker. Never import or expose this module to selectors.

This file contains all expected goal answers. It does not implement a replay
engine, generate mutations, choose tests, or inspect mutation identities.
"""

from typing import Any

_EXPECTED = {
    "A1": "Alpha",
    "A2": "Bridge",
    "A3": "Nested",
    "A4": "Plain",
    "P1": ["a", "b", "c"],
    "P2": ["one"],
    "P3": ["東京", "Zürich"],
    "P4": ["late"],
    "E1": "Recovered",
    "E2": "r-1",
    "E3": "bad_request",
    "E4": "Backup",
    "R1": "Found",
    "R2": "Hit",
    "R3": "東京-found",
    "R4": ["west", "east"],
}


def check(task_id: str, answer: Any, state: Any, transcript: Any) -> dict:
    """Check final goal semantics, without leaking the expected answer in reasons.

    The result field is compared exactly, including text case, Unicode code
    points, list order, and list multiplicity. Only E2 has a committed-write
    constraint; only E3 has an exact dispatch-count constraint. Replay budget
    and causality checks belong to the separately implemented replay engine.
    """
    if not isinstance(task_id, str) or task_id not in _EXPECTED:
        return {"passed": False, "reason": "unknown_task"}
    if not isinstance(answer, dict) or "result" not in answer:
        return {"passed": False, "reason": "missing_result"}
    expected = _EXPECTED[task_id]
    actual = answer["result"]
    if type(actual) is not type(expected) or actual != expected:
        return {"passed": False, "reason": "incorrect_result"}
    if task_id == "E2":
        if not isinstance(state, dict):
            return {"passed": False, "reason": "missing_write_state"}
        writes = state.get("committed_writes")
        if type(writes) is not int or writes != 1:
            return {"passed": False, "reason": "write_count_not_one"}
    if task_id == "E3":
        if not isinstance(transcript, (list, tuple)) or not all(
            isinstance(event, dict) for event in transcript
        ):
            return {"passed": False, "reason": "invalid_transcript"}
        dispatches = sum(event.get("kind") == "tool_dispatch" for event in transcript)
        if dispatches != 1:
            return {"passed": False, "reason": "dispatch_count_not_one"}
    return {"passed": True, "reason": "goal_satisfied"}
