"""Bounded deterministic instrumentation; no model client exists in this code.

Replay only uses a historical response if its complete preceding request agrees.
Any first differing boundary raises immediately, before a differing dispatch is
executed. No divergent run is continued, graded, or called a model regression.
"""
from copy import deepcopy
from common import canonical, component_id, digest
from fixtures import ToolWorld, UnsupportedPath

TOOLS = [{"type": "function", "function": {"name": name, "description": "Local fixture " + name, "parameters": {"type": "object", "additionalProperties": True}}} for name in ("get", "query", "list", "read", "write", "lookup", "search")]


class StopReplay(Exception):
    def __init__(self, status, detail):
        self.status = status
        self.detail = detail


class Harness:
    def __init__(self, task, hooks, tape, reference=None, world=None):
        self.task = deepcopy(task)
        self.hooks = hooks
        self.tape = deepcopy(tape)
        self.reference = deepcopy(reference)
        self.world = world if world is not None else ToolWorld(task["id"])
        self.events = []
        self.hook_calls = []
        self.request_bindings = []
        self.responses_consumed = 0
        self.model_requests = 0
        self.dispatches = 0
        self.boundaries_attempted = 0
        self.answer = None
        self.messages = [{"role": "user", "content": task["prompt"]}]

    def hook(self, name, *args):
        result = getattr(self.hooks, name)(*deepcopy(args))
        self.hook_calls.append({"component_id": component_id(name), "component_name_for_audit_only": name, "arguments": deepcopy(args), "result": deepcopy(result), "next_boundary_index": len(self.events)})
        return result

    def emit(self, kind, payload, components=()):
        event = {"kind": kind, "payload": deepcopy(payload)}
        self.boundaries_attempted += 1
        if self.reference is not None:
            index = len(self.events)
            expected_events = self.reference["events"]
            expected = expected_events[index] if index < len(expected_events) else None
            if canonical(event) != canonical(expected):
                raise StopReplay("diverged_unknown", {"boundary_index": index, "old_kind": expected["kind"] if expected else "end_of_tape", "new_kind": kind, "old_sha256": digest(expected), "new_sha256": digest(event), "responses_consumed_at_stop": self.responses_consumed})
        self.events.append(event)
        # Instrumentation metadata are separate from observable event equality.
        return event

    def terminate(self, reason, answer=None, exhausted=None):
        self.emit("termination", {"reason": reason, "answer": deepcopy(answer), "model_request_count": self.model_requests, "tool_dispatch_count": self.dispatches, "exhausted_budget": exhausted})
        self.answer = deepcopy(answer)

    def budget(self, resource, limit, used):
        self.emit("budget", {"resource": resource, "limit": limit, "used": used})
        self.terminate("budget_exhausted", exhausted=resource)

    def request(self):
        return {"model": "FIXED_MODEL_PLACEHOLDER_NO_API", "messages": [{"role": "system", "content": self.hook("system_prompt")}] + deepcopy(self.messages), "tools": deepcopy(TOOLS), "tool_choice": "auto", "generation": {"temperature": 0, "max_output_tokens": 1024}, "response_format": {"type": "fixture_tool_call_or_final"}, "metadata": {"fixture_protocol": "request-v1"}}

    def consume(self, request):
        index = self.responses_consumed
        if self.reference is not None:
            bindings = self.reference["request_bindings"]
            if index >= len(bindings):
                raise StopReplay("unsupported_unknown", {"reason": "no_historical_response_for_request"})
            binding = bindings[index]
            # A second explicit guard makes request/response causality auditable.
            if canonical(binding["request"]) != canonical(request):
                raise StopReplay("diverged_unknown", {"reason": "request_binding_mismatch", "responses_consumed_at_stop": index})
            response = deepcopy(binding["response"])
        else:
            if index >= len(self.tape["responses"]):
                raise StopReplay("unsupported_unknown", {"reason": "authored_tape_exhausted"})
            response = deepcopy(self.tape["responses"][index])
        self.responses_consumed += 1
        self.request_bindings.append({"request": deepcopy(request), "response": deepcopy(response)})
        return response

    def run(self):
        status, detail = "complete", None
        try:
            while True:
                if self.model_requests >= self.task["horizon_model_requests"]:
                    self.budget("model_requests", self.task["horizon_model_requests"], self.model_requests)
                    status = "budget_exhausted"
                    break
                request = self.request()
                self.model_requests += 1  # Attempted boundary, not a real API call.
                self.emit("model_request", request)
                response = self.consume(request)
                self.messages.append({"role": "assistant", "content": deepcopy(response)})
                if "final" in response:
                    self.terminate("scripted_final", response["final"])
                    break
                tool = response.get("tool_call")
                if not isinstance(tool, dict) or set(tool) != {"name", "arguments"}:
                    raise StopReplay("unsupported_unknown", {"reason": "unsupported_authored_response"})
                name, arguments, attempt = tool["name"], deepcopy(tool["arguments"]), 0
                while True:
                    if self.dispatches >= self.task["tool_dispatch_budget"]:
                        self.budget("tool_dispatches", self.task["tool_dispatch_budget"], self.dispatches)
                        status = "budget_exhausted"
                        return self.result(status, detail)
                    arguments = self.hook("normalize_arguments", arguments)
                    self.emit("tool_dispatch", {"name": name, "arguments": arguments, "attempt": attempt})
                    self.dispatches += 1  # Only now is the accepted dispatch executed.
                    try:
                        raw = self.world.invoke(name, deepcopy(arguments))
                    except UnsupportedPath:
                        raise StopReplay("unsupported_unknown", {"reason": "unsupported_tool_path"})
                    observation = self.hook("prepare_observation", raw)
                    self.emit("tool_observation", {"name": name, "observation": observation, "attempt": attempt})
                    self.messages.append({"role": "tool", "tool_call_id": f"request-{self.model_requests}-attempt-{attempt}", "name": name, "content": deepcopy(observation)})
                    if self.hook("should_terminate", name, observation):
                        self.terminate("early_empty_observation", {"result": []})
                        return self.result("complete", detail)
                    retry = self.hook("retry_arguments", name, arguments, observation, attempt)
                    if retry is None:
                        break
                    arguments, attempt = retry, attempt + 1
        except StopReplay as stop:
            status, detail = stop.status, stop.detail
        if status == "complete" and self.reference is not None:
            if len(self.events) != len(self.reference["events"]):
                status, detail = "unsupported_unknown", {"reason": "reference_tail_unmatched"}
            else:
                status = "historical_path_equivalent"
        return self.result(status, detail)

    def result(self, status, detail):
        return {"task_id": self.task["id"], "tape_id": self.tape["tape_id"], "source_kind": "HANDSCRIPTED_INSTRUMENTATION_FIXTURE", "status": status, "detail": detail, "answer": deepcopy(self.answer), "state": self.world.snapshot(), "events": deepcopy(self.events), "request_bindings": deepcopy(self.request_bindings), "hook_calls": deepcopy(self.hook_calls), "responses_consumed": self.responses_consumed, "model_request_boundaries_attempted": self.model_requests, "actual_tool_dispatches": self.dispatches, "boundaries_attempted": self.boundaries_attempted, "scripted_synthetic_units": self.model_requests + self.dispatches, "goal_outcome": "unknown_after_divergence" if status in ("diverged_unknown", "unsupported_unknown") else "not_evaluated_by_replay"}


def local_predicate_probe(recording, hooks, diffs):
    """Simple strong control: inspect changed pure hooks on valid H0 contexts.

    This stops at the first changed hook return; it never reads later contexts.
    No checker, task goal, new-model behavior, or mutation label is consulted.
    Outputs only structural metadata. It is a local diagnostic, not a selector
    with privileged answers, and is limited to this toy's pure hook interface.
    """
    changed = {item["component_id"] for item in diffs}
    evaluations = 0
    encountered = set()
    for context in recording["hook_calls"]:
        if context["component_id"] not in changed:
            continue
        encountered.add(context["component_id"])
        evaluations += 1
        result = getattr(hooks, context["component_name_for_audit_only"])(*deepcopy(context["arguments"]))
        if canonical(result) != canonical(context["result"]):
            return {"status": "changed_local_return", "next_boundary_index": context["next_boundary_index"], "component_id": context["component_id"], "hook_evaluations": evaluations}
    return {"status": "unknown_unexposed_component" if changed - encountered else "no_changed_return_on_historical_contexts", "next_boundary_index": None, "component_id": None, "hook_evaluations": evaluations}
