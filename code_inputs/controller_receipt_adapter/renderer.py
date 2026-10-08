"""Scripted-only controller receipts; no provider/client path is implemented."""
from __future__ import annotations

import copy
import hashlib
import sys
from dataclasses import dataclass

if 'no_api_guard' not in sys.modules:
    raise RuntimeError('Use launch.py: no-API guards must precede upstream imports')

from tau2.data_model.message import AssistantMessage, SystemMessage, ToolMessage, UserMessage
from tau2.utils.llm_utils import to_litellm_messages, validate_message_history
from interventions import FrozenJSON, canonical, digest, parse_json, check_privacy

INTRO = ('Controller event record. This is a derived intervention transcript, not a new model output or user message. '
         'The original actor proposal is preserved as proposal data below. Only the selected execution actually ran. '
         'The tool result is copied from that execution. This record makes no claim about hidden model state.\n')
PROPOSAL_INTRO = ('Controller proposal record. The following pending actor proposal is data only; '
                  'it has not executed. This request does not contain an unresolved native tool call.\n')
MODE = 'scripted_fixture'
TAG = 'derived_intervention_execution'


class AdapterError(ValueError):
    pass


class ProviderBlocked(RuntimeError):
    pass


def provider_request(*args, **kwargs):
    raise ProviderBlocked('Provider runtime disabled. Separate approval of tiny format test, provider/model and total budget is required; no client created.')


def raw(message):
    return message.model_dump(mode='json')


def reject_nontext(message):
    if getattr(message, 'is_audio', False) or getattr(message, 'audio_content', None) is not None or getattr(message, 'chunk_id', None) is not None or not getattr(message, 'is_final_chunk', True):
        raise AdapterError('Voice, audio and streaming messages are unsupported')


def action_of(message):
    reject_nontext(message)
    if type(message) is not AssistantMessage or message.content not in (None, ''):
        raise AdapterError('Slot requires one text-free assistant tool call')
    if not message.tool_calls or len(message.tool_calls) != 1 or message.is_audio:
        raise AdapterError('Slot requires exactly one non-audio call')
    call = message.tool_calls[0]
    if not call.id or not call.name or call.requestor != 'assistant':
        raise AdapterError('Invalid call identity/routing')
    canonical(call.arguments)
    return {'name': call.name, 'arguments': copy.deepcopy(call.arguments)}


def execution_id(original, action):
    a0 = action_of(original)
    if canonical(a0) == canonical(action):
        return original.tool_calls[0].id
    return 'controller-exec-' + digest({'original_id': original.tool_calls[0].id, 'action': action})[:20]


@dataclass(frozen=True)
class ObservedModelOutput:
    """Immutable full captured message; fixtures explicitly are not model generations."""
    record_id: str
    component: str
    message: FrozenJSON
    raw_provider_response: str | None = None
    mode: str = MODE

    def __post_init__(self):
        if type(self.message) is not FrozenJSON:
            raise AdapterError('Observed message must be immutable FrozenJSON')
        if not self.record_id or self.component not in {'actor', 'reviewer', 'self'} or self.mode != MODE:
            raise AdapterError('Only labeled offline fixture records are supported')
        if self.raw_provider_response is not None:
            raise AdapterError('This offline build cannot claim an actual provider response')

    def export(self):
        return {'kind': 'ObservedModelOutput', 'record_id': self.record_id, 'component': self.component,
                'message': self.message.copy(), 'message_sha256': digest(self.message),
                'raw_provider_response': self.raw_provider_response, 'mode': self.mode,
                'actual_model_calls': 0}


@dataclass(frozen=True)
class ExecutionRecord:
    """Immutable audit record. Only public_receipt()/packet reach the actor."""
    value: FrozenJSON

    @classmethod
    def create(cls, observed, decision, derived, result, packet):
        return cls(FrozenJSON.of({'observed': observed.export(), 'decision': decision,
                                 'derived_call': raw(derived), 'actual_result': raw(result),
                                 'packet': packet, 'mode': MODE}))

    def __post_init__(self):
        if type(self.value) is not FrozenJSON:
            raise AdapterError('Execution record must be immutable FrozenJSON')
        v = self.value.copy()
        if not isinstance(v, dict):
            raise AdapterError('Execution record must be an object')
        if set(v) != {'observed', 'decision', 'derived_call', 'actual_result', 'packet', 'mode'} or v['mode'] != MODE:
            raise AdapterError('Unknown execution record shape')
        obs, dec = v['observed'], v['decision']
        if set(obs) != {'kind','record_id','component','message','message_sha256','raw_provider_response','mode','actual_model_calls'}:
            raise AdapterError('Unknown observed record shape')
        if obs['kind'] != 'ObservedModelOutput' or obs['component'] != 'actor' or obs['mode'] != MODE or obs['actual_model_calls'] != 0 or obs['raw_provider_response'] is not None:
            raise AdapterError('Fixture provenance invalid')
        if digest(obs['message']) != obs['message_sha256']:
            raise AdapterError('Observed proposal digest mismatch')
        original = AssistantMessage.model_validate(obs['message'])
        a0 = action_of(original)
        if set(dec) != {'kind','source','selected_action','classification','proposal_sha256','packet_sha256','recommendation'}:
            raise AdapterError('Unknown decision shape')
        if dec['kind'] != 'InterventionDecision' or dec['source'] not in {'original','reviewer_fixture','self_fixture'} or dec['proposal_sha256'] != obs['message_sha256']:
            raise AdapterError('Decision provenance mismatch')
        action = dec['selected_action']
        recommendation = dec['recommendation']
        if dec['source'] == 'original':
            if canonical(action) != canonical(a0):
                raise AdapterError('Original source cannot select changed action')
            if recommendation is not None or v['packet']:
                raise AdapterError('Original record cannot carry a reviewer packet')
        else:
            if not isinstance(recommendation, dict) or recommendation.get('mode') != MODE or recommendation.get('actual_model_calls') != 0 or recommendation.get('raw_provider_response') is not None:
                raise AdapterError('Missing immutable fixture recommendation')
            if recommendation.get('component') != ('reviewer' if dec['source'] == 'reviewer_fixture' else 'self') or digest(recommendation.get('message')) != recommendation.get('message_sha256'):
                raise AdapterError('Recommendation provenance mismatch')
            recorded = recommendation['message']
            if not isinstance(recorded, dict) or set(recorded) != {'selected_action', 'packet'} or recorded['selected_action'] != action or (v['packet'] and v['packet'] != recorded['packet']):
                raise AdapterError('Selected package differs from captured fixture output')
        if not isinstance(action, dict) or set(action) != {'name','arguments'} or not isinstance(action['name'], str) or not isinstance(action['arguments'], dict):
            raise AdapterError('Invalid selected action')
        expected_classification = 'unchanged' if canonical(a0) == canonical(action) else 'valid_changed'
        if dec['classification'] != expected_classification or digest(v['packet']) != dec['packet_sha256']:
            raise AdapterError('Decision or packet mismatch')
        derived = AssistantMessage.model_validate(v['derived_call'])
        result = ToolMessage.model_validate(v['actual_result'])
        if action_of(derived) != action or derived.tool_calls[0].id != execution_id(original, action):
            raise AdapterError('Derived execution mismatch')
        expected_metadata = {'record_kind': TAG, 'original_proposal_sha256': obs['message_sha256'],
                             'authored_by': 'controller', 'backend_requestor_is_routing_only': True}
        if derived.raw_data != expected_metadata or derived.cost is not None or derived.usage is not None:
            raise AdapterError('Derived call must not carry observed-generation cost or provenance')
        if derived.timestamp != original.timestamp or result.id != derived.tool_calls[0].id or result.requestor != 'assistant':
            raise AdapterError('Execution identity/timestamp/routing mismatch')
        if not result.timestamp or not derived.timestamp or result.timestamp < derived.timestamp:
            raise AdapterError('Result precedes its execution; preserve raw time and reject this branch')
        validate_packet(v['packet'])
        check_privacy(self.public_receipt())

    @property
    def call_id(self):
        return self.value.copy()['actual_result']['id']

    def public_receipt(self):
        v = self.value.copy()
        original = AssistantMessage.model_validate(v['observed']['message'])
        action = v['decision']['selected_action']
        return {'kind': 'controller_execution_receipt_v1',
                'proposed_action': action_of(original), 'proposal_call_id': original.tool_calls[0].id,
                'proposal_disposition': 'executed' if action_of(original) == action else 'not_executed',
                'executed_action': action, 'execution_call_id': v['actual_result']['id'],
                'executor': 'benchmark_controller',
                'tool_result': {k: v['actual_result'][k] for k in ('content', 'error')}}


def validate_packet(packet):
    if packet == {}:
        return
    fields = {'kind', 'critique', 'actor_revision_instruction', 'provenance'}
    if not isinstance(packet, dict) or set(packet) != fields:
        raise AdapterError('Only empty or explicitly recorded critique/revision fixture packets supported')
    if packet['kind'] != 'reviewer_critique_actor_revision_fixture_packet' or packet['provenance'] != 'scripted_fixture_not_model_generated':
        raise AdapterError('Packet cannot claim real reviewer generation')
    if any(not isinstance(packet[k], str) or not packet[k] for k in fields):
        raise AdapterError('Packet strings must be nonempty')
    check_privacy(packet)


def validate_native(messages, *, actor_only=True, allow_pending=False):
    """Sequence/IDs/routing/half-duplex validation stronger than upstream helper."""
    pending = []
    seen = set()
    for message in messages:
        if type(message) not in (SystemMessage, AssistantMessage, UserMessage, ToolMessage):
            raise AdapterError('Unknown, multimodal or unflattened message type')
        if pending:
            if type(message) is not ToolMessage:
                raise AdapterError('Call must be immediately followed by its actual results')
            call_id, requestor = pending.pop(0)
            if message.id != call_id or message.requestor != requestor:
                raise AdapterError('Result ID/requestor mismatch')
            continue
        if type(message) is ToolMessage:
            raise AdapterError('Orphan or duplicate result')
        if type(message) is SystemMessage:
            if not message.content or not message.content.strip():
                raise AdapterError('Empty system message')
            continue
        reject_nontext(message)
        if message.is_audio:
            raise AdapterError('Only text messages supported')
        if message.tool_calls is not None:
            if not message.tool_calls or message.content not in (None, ''):
                raise AdapterError('Empty or mixed-content native call')
            if actor_only and type(message) is UserMessage:
                raise AdapterError('User tool calls would be dropped by provider converter')
            for tc in message.tool_calls:
                if not tc.id or tc.id in seen or not tc.name or tc.requestor != message.role:
                    raise AdapterError('Invalid/duplicate native call identity or routing')
                canonical(tc.arguments)
                seen.add(tc.id)
                pending.append((tc.id, message.role))
        elif not message.content or not message.content.strip():
            raise AdapterError('Empty participant message')
    if pending and not allow_pending:
        raise AdapterError('Unresolved native calls')
    return seen


@dataclass(frozen=True)
class ActorRequestProjection:
    payload: FrozenJSON
    source_messages_sha256: str
    purpose: str = 'actor_continuation'
    provider_acceptance: str = 'UNTESTED_RUNTIME_BLOCKED'

    @property
    def bytes(self):
        return self.payload.text.encode('utf-8')

    def export(self):
        return {'kind': 'ActorRequestProjection', 'payload': self.payload.copy(),
                'payload_sha256': digest(self.payload), 'source_messages_sha256': self.source_messages_sha256,
                'purpose': self.purpose, 'mode': MODE, 'provider_acceptance': self.provider_acceptance}


class ControllerReceiptRendererV1:
    """Stateless renderer; immutable record registry must accompany every state."""
    version = 'ControllerReceiptRendererV1'

    def render(self, system_messages, messages, records, tools, config, private_canaries=()):
        native = copy.deepcopy(system_messages + messages)
        validate_native(native)
        registry = {r.call_id: r for r in records}
        if len(registry) != len(records):
            raise AdapterError('Duplicate registry identity')
        found = set()
        rendered = []
        i = 0
        while i < len(native):
            message = native[i]
            derived_tag = type(message) is AssistantMessage and isinstance(message.raw_data, dict) and message.raw_data.get('record_kind') == TAG
            ids = [tc.id for tc in (getattr(message, 'tool_calls', None) or [])]
            linked = [x for x in ids if x in registry]
            if derived_tag or linked:
                if len(ids) != 1 or not derived_tag or not linked or linked[0] in found:
                    raise AdapterError('Missing, ambiguous or untyped derived span')
                record = registry[linked[0]]
                v = record.value.copy()
                if raw(message) != v['derived_call'] or i + 1 >= len(native) or raw(native[i + 1]) != v['actual_result']:
                    raise AdapterError('Derived span or actual response changed')
                receipt = {'execution_receipt': record.public_receipt(), 'extra_packet': v['packet']}
                check_privacy(receipt, private_canaries)
                rendered.append(SystemMessage(role='system', content=INTRO + canonical(receipt)))
                found.add(record.call_id)
                i += 2
            else:
                rendered.append(message)
                i += 1
        if found != set(registry):
            raise AdapterError('Persisted registry span missing from request')
        validate_native(rendered)
        validate_message_history(rendered)
        wire = to_litellm_messages(rendered)
        if len(wire) != len(rendered):
            raise AdapterError('Converter silently dropped messages')
        payload = {'messages': wire, 'tools': copy.deepcopy(tools), 'config': copy.deepcopy(config)}
        check_privacy(payload, private_canaries)
        return ActorRequestProjection(FrozenJSON.of(payload), digest([raw(m) for m in native]))

    def proposal_request(self, system_messages, messages, records, tools, config, instruction, private_canaries=()):
        """Review/self requests label the pending proposal as data, never native call."""
        if not messages:
            raise AdapterError('Missing proposal')
        pending = messages[-1]
        action = action_of(pending)
        base = self.render(system_messages, messages[:-1], records, tools, config, private_canaries)
        payload = base.payload.copy()
        event = {'kind': 'pending_proposal_data', 'proposal_call_id': pending.tool_calls[0].id,
                 'proposed_action': action, 'instruction': instruction,
                 'fixture_provenance': 'scripted_fixture_not_model_generated'}
        check_privacy(event, private_canaries)
        payload['messages'].append({'role': 'system', 'content': PROPOSAL_INTRO + canonical(event)})
        return ActorRequestProjection(FrozenJSON.of(payload), digest([raw(m) for m in system_messages + messages]), 'review_or_self_revision')


def records_to_json(records):
    return canonical([r.value.copy() for r in records])


def records_from_json(value):
    parsed = parse_json(value)
    if not isinstance(parsed, list) or canonical(parsed) != value:
        raise AdapterError('Registry must be canonical array')
    return tuple(ExecutionRecord(FrozenJSON.of(x)) for x in parsed)


class RawUsageLedger:
    """Deduplicated fixture records and complete local requests, never inferred dollars."""
    def __init__(self):
        self.outputs = {}
        self.requests = {}

    def record_output(self, observed, test_units=0):
        if type(test_units) is not int or test_units < 0:
            raise AdapterError('Invalid TEST_UNITS')
        row = {'observed': observed.export(), 'test_units': test_units}
        self._insert(self.outputs, observed.record_id, row)

    def record_request(self, request_id, projection):
        if not request_id:
            raise AdapterError('Missing request identity')
        self._insert(self.requests, request_id, projection.export())

    @staticmethod
    def _insert(table, key, value):
        if key in table and table[key] != value:
            raise AdapterError('Conflicting reuse of usage identity')
        table[key] = copy.deepcopy(value)

    def report(self):
        return {'mode': MODE, 'denomination': 'TEST_UNITS', 'actual_model_calls': 0,
                'actual_charges': 0, 'real_token_usage': None, 'test_units': sum(x['test_units'] for x in self.outputs.values()),
                'observed_fixture_outputs': copy.deepcopy(self.outputs), 'effective_requests': copy.deepcopy(self.requests),
                'future_cost_policy': 'Each real generation including reviewer/self and repeated receipt context must be counted once by raw provider call identity; no synthetic execution cost attribution.'}

    @classmethod
    def restore(cls, report):
        obj = cls()
        if report.get('mode') != MODE or report.get('actual_model_calls') != 0 or report.get('actual_charges') != 0:
            raise AdapterError('Invalid offline ledger')
        for key, row in report['observed_fixture_outputs'].items():
            obs = row['observed']
            observed = ObservedModelOutput(obs['record_id'], obs['component'], FrozenJSON.of(obs['message']), obs['raw_provider_response'], obs['mode'])
            if key != observed.record_id or observed.export() != obs:
                raise AdapterError('Stored observed output digest or provenance mismatch')
            obj.record_output(observed, row['test_units'])
        for key, row in report['effective_requests'].items():
            projection = ActorRequestProjection(FrozenJSON.of(row['payload']), row['source_messages_sha256'], row['purpose'], row['provider_acceptance'])
            if projection.export() != row or projection.provider_acceptance != 'UNTESTED_RUNTIME_BLOCKED':
                raise AdapterError('Stored request digest or provenance mismatch')
            obj.record_request(key, projection)
        if obj.report() != report:
            raise AdapterError('Ledger totals or policy changed')
        return obj
