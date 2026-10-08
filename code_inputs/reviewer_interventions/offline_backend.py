"""Read-only consumer of the frozen backend; imported ONLY after its no-API guard."""
from __future__ import annotations

import copy
import json
import pathlib
import random
import sys

if "no_api_guard" not in sys.modules:
    raise RuntimeError("Guard must be installed before upstream imports")

import numpy as np
import backend_checks as backend
from tau2.orchestrator.orchestrator import Role
from tau2.domains.telecom.environment import get_tasks
from tau2.data_model.message import ToolCall
from tau2.utils.llm_utils import to_litellm_messages
from tau2.environment.toolkit import get_tool_types, ToolType

from interventions import FrozenJSON, Root, SOURCE_COMMIT, digest, canonical, execution_id

PILOT = pathlib.Path(__file__).resolve().parent.parent / "reviewer_pilot"


def restore_checkpoint(checkpoint: dict):
    """Reinstate the exact pending boundary, never rewrite the original proposal."""
    c = copy.deepcopy(checkpoint)
    random.seed(0)
    np.random.seed(0)
    backend.block_uuid()
    task = next(t for t in get_tasks("base") if t.id == c["task_id"])
    assert backend.digest(task) == c["task_sha256"]
    history = [backend.decode(x) for x in c["completed_history"]]
    task_prefix = task.model_copy(deep=True)
    task_prefix.initial_state.message_history = history
    o = backend.make_orchestrator(
        task_prefix,
        [backend.decode(x) for x in c["remaining_agent_queue"]],
        [backend.decode(x) for x in c["remaining_user_queue"]],
    )
    o.initialize()
    assert o.from_role == Role.USER and o.to_role == Role.AGENT
    assert len(o.trajectory) == len(history)
    for restored, original in zip(o.trajectory, history):
        restored.timestamp = original.timestamp
        restored.turn_idx = original.turn_idx
    for role in ("agent_state", "user_state"):
        for restored, original in zip(getattr(o, role).system_messages, c["raw_checkpoint"][role]["system_messages"]):
            restored.timestamp = original["timestamp"]
            restored.turn_idx = original["turn_idx"]
    pending = backend.decode(c["pending_proposal"])
    o.agent_state.messages.extend([o.message, pending])
    o.trajectory.append(pending)
    o.message = pending
    o.from_role = Role.AGENT
    o.to_role = Role.ENV
    o.step_count = c["state"]["budget"]["step_count"]
    o.num_errors = c["state"]["budget"]["num_errors"]
    random.setstate(backend._tuples(c["state"]["rng"]["python"]))
    nr = c["state"]["rng"]["numpy"]
    np.random.set_state((nr[0], np.array(nr[1], dtype=np.uint32), nr[2], nr[3], nr[4]))
    raw = backend.orch_state(o, False)
    assert raw == c["raw_checkpoint"], backend._different(raw, c["raw_checkpoint"])
    assert digest(raw) == c["raw_checkpoint_sha256"]
    assert backend.orch_state(o) == c["state"]
    assert backend.effective_views(o) == c["raw_checkpoint"]["effective_model_history"]
    assert backend.dump(o.message) == c["pending_proposal"]
    return o, task


def load_root() -> tuple[Root, dict, set[str]]:
    checkpoint = json.loads((PILOT / "results/task_0_checkpoint.json").read_text())
    coverage = json.loads((PILOT / "results/read_tool_summary.json").read_text())
    o, _ = restore_checkpoint(checkpoint)
    catalog = {tool.name: tool for tool in o.environment.get_tools()}
    names = set(coverage["read_tool_names"])
    assert all(get_tool_types(o.environment.tools)[name] == ToolType.READ for name in names)
    projection = backend.effective_views(o)
    constraint = {
        "intervention_scope": "One assistant-side diagnostic READ only",
        "allowed_intervention_tool_names": sorted(names),
        "multi_call_or_mutation": "out_of_scope_record_once_no_resampling",
        "actor_future_tool_catalog": "Full original catalog preserved; this restriction applies only to the intervention slot",
        "known_fidelity_limit": "Concrete verified arguments have environment-transition coverage; replacement provider/orchestrator continuation remains unvalidated",
    }
    root = Root(
        "checkpoint-0-scripted-fixture", FrozenJSON.of(checkpoint),
        FrozenJSON.of(checkpoint["pending_proposal"]), digest(checkpoint["pending_proposal"]),
        FrozenJSON.of(projection["agent"]), FrozenJSON.of(projection["user"]),
        FrozenJSON.of([tool.openai_schema for tool in o.environment.get_tools()]),
        FrozenJSON.of(constraint), checkpoint["raw_checkpoint_sha256"],
    )
    return root, catalog, names


def execute_read(root: Root, action: dict, call_id: str) -> dict:
    """Fresh restored environment per call; no replacement is put in actor history."""
    before_root = root.private_checkpoint.text
    o, _ = restore_checkpoint(root.private_checkpoint.copy())
    names = set(root.public_constraint.copy()["allowed_intervention_tool_names"])
    if action["name"] not in names:
        raise ValueError("Public READ study scope violated")
    assert get_tool_types(o.environment.tools)[action["name"]] == ToolType.READ
    raw_before = backend.orch_state(o, False)
    state_before = backend.state(o.environment)
    original_message_before = backend.dump(o.message)
    call = ToolCall(id=call_id, name=action["name"], arguments=copy.deepcopy(action["arguments"]), requestor="assistant")
    response = o.environment.get_response(call)
    state_after = backend.state(o.environment)
    assert backend.dump(o.message) == original_message_before
    assert root.private_checkpoint.text == before_root
    assert state_before == state_after, "Even a READ must be checked for unexpected mutation"
    coverage = json.loads((PILOT / "results/read_tool_summary.json").read_text())
    concrete = coverage["concrete_argument_sets"].get(action["name"])
    if action["arguments"] == concrete:
        fidelity = "concrete_READ_environment_transition_verified; override_orchestration_unvalidated"
    else:
        fidelity = "test_probe_arguments_only; no_inherited_fidelity_claim"
    return {
        "raw_tool_response": backend.dump(response),
        "public_tool_projection": to_litellm_messages([response]),
        "before": digest(state_before), "after": digest(state_after),
        "preintervention_checkpoint": digest(raw_before), "fidelity": fidelity,
    }


def shadow_analysis(root: Root, action: dict) -> dict:
    """Private analysis only. Fresh restore and copy-based oracle; never model input."""
    before_root = root.private_checkpoint.text
    o, task = restore_checkpoint(root.private_checkpoint.copy())
    before = backend.state(o.environment)
    initial = backend.vector(o.environment, task)
    response = o.environment.get_response(ToolCall(
        id=execution_id(root, action), name=action["name"],
        arguments=copy.deepcopy(action["arguments"]), requestor="assistant"))
    terminal = backend.vector(o.environment, task)
    assert root.private_checkpoint.text == before_root
    assert before == backend.state(o.environment)
    preserved = all(not had or has for had, has in zip(initial, terminal))
    return {
        "analysis_stratum": "V+" if preserved else "not_V+",
        "private_only_never_feedback_or_gate": True,
        "public_tool_error": response.error,
        "environment_state_unchanged": True,
        "not_a_terminal_result": True,
    }
