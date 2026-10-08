"""Narrow READ execution bridge and receipt-aware scripted LLMAgent/state wrapper."""
from __future__ import annotations
import copy
import json
import random
import sys
import time

if 'no_api_guard' not in sys.modules:
    raise RuntimeError('Use guarded launch.py')

import numpy as np
from tau2.agent.llm_agent import LLMAgent, LLMAgentState
from tau2.data_model.message import AssistantMessage, ToolMessage, ToolCall, UserMessage
from tau2.data_model.simulation import TerminationReason
from tau2.orchestrator.orchestrator import Role, Orchestrator
from tau2.environment.toolkit import ToolType, get_tool_types
from tau2.domains.telecom.environment import get_tasks
from tau2.utils.utils import get_now
from tau2.user.user_simulator_base import UserState
import backend_checks as backend
from offline_backend import restore_checkpoint
from interventions import FrozenJSON, canonical, digest, check_privacy
from renderer import (AdapterError, ControllerReceiptRendererV1, ExecutionRecord, ObservedModelOutput,
                      RawUsageLedger, TAG, action_of, execution_id, raw, records_from_json,
                      records_to_json, validate_native, validate_packet, provider_request)


class ReceiptAwareState(LLMAgentState):
    renderer_version: str = 'ControllerReceiptRendererV1'
    receipt_records_json: str  # Required: omitting registry cannot silently use vanilla state.
    actor_boundary_count: int = 0


class ReceiptAwareOfflineAgent(LLMAgent):
    """Every actor boundary is rendered. Queue outputs are labeled scripted fixtures."""
    def __init__(self, *, queue, branch_id, ledger, private_canaries=(), **kwargs):
        super().__init__(**kwargs)
        self.queue = copy.deepcopy(queue)
        self.branch_id = branch_id
        self.ledger = ledger
        self.private_canaries = tuple(private_canaries)
        self.renderer = ControllerReceiptRendererV1()

    def request_for(self, message, state):
        if type(state) is not ReceiptAwareState or state.renderer_version != self.renderer.version:
            raise AdapterError('Required persistent receipt-aware state missing')
        if type(message) not in (UserMessage, ToolMessage):
            raise AdapterError('Only single text/user or tool boundary supported')
        incoming = copy.deepcopy(message)
        if type(incoming) is ToolMessage and any(type(m) is ToolMessage and m.id == incoming.id for m in state.messages):
            raise AdapterError('Incoming result was already appended')
        return self.renderer.render(state.system_messages, state.messages + [incoming],
                                    records_from_json(state.receipt_records_json),
                                    [t.openai_schema for t in self.tools],
                                    {'model': self.llm, 'args': self.llm_args}, self.private_canaries)

    def generate_next_message(self, message, state):
        request = self.request_for(message, state)
        if not self.queue:
            raise AdapterError('Scripted queue exhausted; no live fallback')
        result = copy.deepcopy(self.queue[0])
        if type(result) is not AssistantMessage:
            raise AdapterError('Scripted queue contains wrong role')
        validate_native([result], allow_pending=True)
        result.timestamp = get_now()
        new_state = state.model_copy(deep=True)
        new_state.messages.extend([copy.deepcopy(message), result])
        new_state.actor_boundary_count += 1
        key = self.branch_id + ':actor:' + str(new_state.actor_boundary_count)
        self.ledger.record_request(key, request)
        self.ledger.record_output(ObservedModelOutput(key, 'actor', FrozenJSON.of(raw(result))), 2)
        self.queue.pop(0)
        return result, new_state

    def generate_live(self, *args, **kwargs):
        return provider_request(*args, **kwargs)


def bind_agent(o, branch_id, ledger=None, private_canaries=()):
    """Replace only the actor adapter; retain native tools/config/queue/state."""
    if type(o.agent_state) is ReceiptAwareState:
        raise AdapterError('Already bound')
    old = o.agent
    o.agent = ReceiptAwareOfflineAgent(queue=old.queue, branch_id=branch_id, ledger=ledger or RawUsageLedger(),
                                      private_canaries=private_canaries, tools=old.tools,
                                      domain_policy=old.domain_policy, llm=old.llm, llm_args=old.llm_args)
    o.agent_state = ReceiptAwareState(**o.agent_state.model_dump(), receipt_records_json='[]')
    return o


def select_and_execute(o, action, *, source='original', packet=None, recommendation=None):
    """Copy pending slot into derived replay, then call official step exactly once."""
    if o.done or o.from_role != Role.AGENT or o.to_role != Role.ENV or type(o.agent_state) is not ReceiptAwareState:
        raise AdapterError('Not a bound pre-execution boundary')
    if o.timeout is not None:
        raise AdapterError('Timed checkpoints unsupported; never reset/refund elapsed timeout')
    packet = {} if packet is None else copy.deepcopy(packet)
    validate_packet(packet)
    check_privacy({'action': action, 'packet': packet}, o.agent.private_canaries)
    original = o.message.model_copy(deep=True)
    a0 = action_of(original)
    if source not in {'original', 'reviewer_fixture', 'self_fixture'}:
        raise AdapterError('Unknown recommendation source')
    if source != 'original':
        if not isinstance(recommendation, ObservedModelOutput) or recommendation.component != ('reviewer' if source == 'reviewer_fixture' else 'self'):
            raise AdapterError('Immutable recommendation fixture must be recorded before execution')
        recorded = recommendation.message.copy()
        if not isinstance(recorded, dict) or set(recorded) != {'selected_action', 'packet'} or recorded['selected_action'] != action or (packet and packet != recorded['packet']):
            raise AdapterError('Action/packet differs from captured recommendation fixture')
    elif recommendation is not None or packet:
        raise AdapterError('Original branch cannot carry recommendation or packet')
    if source == 'original' and canonical(action) != canonical(a0):
        raise AdapterError('Original source cannot prescribe a changed action')
    if not isinstance(action, dict) or set(action) != {'name', 'arguments'} or not isinstance(action['arguments'], dict):
        raise AdapterError('Invalid action shape')
    catalog = {t.name: t for t in o.agent.tools}
    name = action['name']
    allowed = set(json.loads((backend.R / 'results/read_tool_summary.json').read_text())['read_tool_names'])
    if name not in catalog or name not in allowed or get_tool_types(o.environment.tools)[name] != ToolType.READ:
        raise AdapterError('Intervention limited to declared assistant READs')
    if set(action['arguments']) - set(catalog[name].params.model_json_schema().get('properties', {})):
        raise AdapterError('Unknown tool arguments')
    catalog[name].params.model_validate(action['arguments'], strict=True)
    if not o.agent_state.messages or not o.trajectory or raw(o.agent_state.messages[-1]) != raw(original) or raw(o.trajectory[-1]) != raw(original):
        raise AdapterError('Pending slot missing or ambiguous')
    validate_native(o.trajectory, actor_only=False, allow_pending=True)
    records = records_from_json(o.agent_state.receipt_records_json)
    if records or o.agent_state.actor_boundary_count != 0:
        raise AdapterError('V1 supports exactly the original checkpoint intervention slot, once')
    call_id = execution_id(original, action)
    prior_ids = {c.id for m in o.trajectory[:-1] for c in (getattr(m, 'tool_calls', None) or [])}
    if call_id in prior_ids or any(r.call_id == call_id for r in records):
        raise AdapterError('Execution ID collides with existing history')
    observed = ObservedModelOutput('shared-proposal:' + digest(raw(original)), 'actor', FrozenJSON.of(raw(original)))
    decision = {'kind': 'InterventionDecision', 'source': source, 'selected_action': copy.deepcopy(action),
                'classification': 'unchanged' if canonical(action) == canonical(a0) else 'valid_changed',
                'proposal_sha256': digest(observed.message), 'packet_sha256': digest(packet),
                'recommendation': recommendation.export() if recommendation is not None else None}
    derived = AssistantMessage(role='assistant', content=None,
                               tool_calls=[ToolCall(id=call_id, name=name, arguments=copy.deepcopy(action['arguments']), requestor='assistant')],
                               timestamp=original.timestamp,
                               raw_data={'record_kind': TAG, 'original_proposal_sha256': digest(observed.message),
                                         'authored_by': 'controller', 'backend_requestor_is_routing_only': True})
    before = FrozenJSON.of(backend.orch_state(o, False))
    state_before = backend.state(o.environment)
    queues = backend.dump([o.agent.queue, o.user.queue])
    user = backend.dump(o.user_state)
    steps, errors = o.step_count, o.num_errors
    # Never mutate aliased original message objects.
    o.agent_state.messages[-1] = derived.model_copy(deep=True)
    o.trajectory[-1] = derived.model_copy(deep=True)
    o.message = derived.model_copy(deep=True)
    o.step()
    o._check_termination()
    result = o.message
    if type(result) is not ToolMessage or result.id != call_id or result.requestor != 'assistant':
        raise AdapterError('Official execution returned unexpected response')
    if o.step_count != steps + 1 or o.num_errors != errors + int(result.error) or o.from_role != Role.ENV or o.to_role != Role.AGENT:
        raise AdapterError('Native accounting or routing changed')
    if backend.state(o.environment) != state_before or backend.dump([o.agent.queue, o.user.queue]) != queues or backend.dump(o.user_state) != user:
        raise AdapterError('READ execution changed environment, queue or user state')
    record = ExecutionRecord.create(observed, decision, derived, result, packet)
    records = records + (record,)
    o.agent_state.receipt_records_json = records_to_json(records)
    o.agent.ledger.record_output(observed, 1)
    if recommendation is not None:
        o.agent.ledger.record_output(recommendation, 3)
    validate_derived_history(o)
    # Validate immediately even if native termination prevents another generation.
    o.agent.request_for(o.message, o.agent_state)
    return record, before


def validate_derived_history(o):
    validate_native(o.trajectory, actor_only=False)
    Orchestrator.validate_message_history(o.trajectory)
    ordered = o.get_trajectory()
    # Sorting may add turn_idx, but must not change message event order.
    if backend.normalize(ordered) != backend.normalize(o.trajectory):
        raise AdapterError('Timestamp sort changes replay event order')
    return ordered


def checkpoint(o, base_checkpoint):
    """Persist full official state plus registry/usage. Only timeout=None is supported."""
    if o.timeout is not None or type(o.agent_state) is not ReceiptAwareState:
        raise AdapterError('Unsupported checkpoint state')
    if o.to_role != Role.AGENT or o.from_role not in (Role.ENV, Role.USER):
        raise AdapterError('Save only at a complete actor boundary')
    validate_derived_history(o)
    o.agent.request_for(o.message, o.agent_state)
    payload = {'kind': 'ControllerReceiptCheckpointV1', 'mode': 'scripted_fixture',
               'base_checkpoint': copy.deepcopy(base_checkpoint), 'official_state': backend.orch_state(o, False),
               'branch_id': o.agent.branch_id, 'ledger': o.agent.ledger.report(),
               'run_start_time': o._run_start_time, 'elapsed_seconds': time.perf_counter() - o._run_start_perf,
               'saved_wall_unix_seconds': time.time(), 'timeout_policy': 'None_only_no_timer_refund'}
    return FrozenJSON.of({'payload': payload, 'sha256': digest(payload)})


def restore(saved, private_canaries=()):
    """Replay actual completed events, never pending or fake cancellation actions."""
    data = saved.copy()
    if set(data) != {'payload', 'sha256'} or digest(data['payload']) != data['sha256']:
        raise AdapterError('Checkpoint integrity mismatch')
    p = data['payload']
    if p['kind'] != 'ControllerReceiptCheckpointV1' or p['mode'] != 'scripted_fixture' or p['timeout_policy'] != 'None_only_no_timer_refund':
        raise AdapterError('Unknown checkpoint version')
    state = p['official_state']
    if state['budget']['timeout'] is not None:
        raise AdapterError('Timed checkpoint unsupported')
    restored_agent_state = ReceiptAwareState.model_validate(state['agent_state'])
    records_from_json(restored_agent_state.receipt_records_json)
    base = p['base_checkpoint']
    task = next(t for t in get_tasks('base') if t.id == base['task_id'])
    if backend.digest(task) != base['task_sha256']:
        raise AdapterError('Pinned task changed')
    o = backend.make_orchestrator(task, [backend.decode(x) for x in state['agent_queue']],
                                  [backend.decode(x) for x in state['user_queue']])
    o.agent.set_seed(o.seed)
    o.user.set_seed(o.seed)
    o.agent_state = LLMAgentState(system_messages=restored_agent_state.system_messages, messages=restored_agent_state.messages)
    bind_agent(o, p['branch_id'], RawUsageLedger.restore(p['ledger']), private_canaries)
    history = [backend.decode(x) for x in state['history']]
    validate_native(history, actor_only=False)
    # Official replay applies only executed events, once in this newly restored branch.
    o.environment.set_state(task.initial_state.initialization_data, task.initial_state.initialization_actions, history, strict=True)
    o.trajectory = history
    o.agent_state = restored_agent_state
    o.user_state = UserState.model_validate(state['user_state'])
    o.agent.queue = [backend.decode(x) for x in state['agent_queue']]
    o.user.queue = [backend.decode(x) for x in state['user_queue']]
    o.message = backend.decode(state['routing']['message'])
    o.from_role, o.to_role = Role(state['routing']['from']), Role(state['routing']['to'])
    for field in ('step_count', 'max_steps', 'num_errors', 'max_errors', 'timeout'):
        setattr(o, field, state['budget'][field])
    o.done = state['done']
    o.termination_reason = TerminationReason(state['termination_reason']) if state['termination_reason'] else None
    o._run_start_time = p['run_start_time']
    elapsed = p['elapsed_seconds']
    downtime = time.time() - p['saved_wall_unix_seconds']
    if not isinstance(elapsed, (int, float)) or elapsed < 0 or downtime < 0:
        raise AdapterError('Invalid/backward wall timing; cannot preserve elapsed duration')
    o._run_start_perf = time.perf_counter() - elapsed - downtime
    random.setstate(backend._tuples(state['rng']['python']))
    nr = state['rng']['numpy']
    np.random.set_state((nr[0], np.array(nr[1], dtype=np.uint32), nr[2], nr[3], nr[4]))
    if backend.orch_state(o, False) != state:
        raise AdapterError('Full official state differs after restore: ' + ','.join(backend._different(backend.orch_state(o, False), state)))
    validate_derived_history(o)
    o.agent.request_for(o.message, o.agent_state)
    return o, task
