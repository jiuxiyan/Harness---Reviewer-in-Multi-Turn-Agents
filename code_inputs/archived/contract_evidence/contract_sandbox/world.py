"""Evaluator-only simulator. Policy code must not import this module.

Expiry removes a deduplication reservation, not work, a payload binding, or a
durable effect. Status queries the durable operation history, not the cache.
"""
from dataclasses import dataclass, field
from .evidence import Contract, OUTCOMES
from .public import TASK_KEY, PAYLOAD


@dataclass
class Generation:
    scope: tuple[str, str, str, str]
    payload: str
    accepted: int
    due: int | None
    generation: int
    committed: int | None = None


@dataclass
class World:
    contract: Contract
    initial_outcome: str
    pending_continuation: bool = False
    now: int = 0
    generations: list[Generation] = field(default_factory=list)
    ledger: list[dict] = field(default_factory=list)
    bindings: dict = field(default_factory=dict)
    snapshots: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.initial_outcome not in OUTCOMES:
            raise ValueError(self.initial_outcome)
        if self.pending_continuation and self.contract.processing_bound is not None:
            raise ValueError("An unknown-processing continuation cannot violate a documented bound.")
        if self.initial_outcome != "rejected":
            due = 0 if self.initial_outcome == "immediate_commit" else self._due(0)
            self._accept(self.scope(TASK_KEY), PAYLOAD, due)
        self._commit_due()
        self._snapshot()
        self.advance(1)

    @staticmethod
    def scope(key, service="records", tenant="example-tenant", operation="create_record"):
        return service, tenant, operation, key

    def _due(self, tick):
        if self.pending_continuation:
            return None  # Abstract pending beyond the selected observation window; later outcome unspecified.
        return tick + (self.contract.processing_bound or 4)

    def _accept(self, scope, payload, due):
        self.bindings[scope] = payload
        generation = Generation(scope, payload, self.now, due, len(self.generations))
        self.generations.append(generation)
        return generation

    def _commit_due(self):
        for generation in self.generations:
            if generation.committed is None and generation.due is not None and generation.due <= self.now:
                generation.committed = generation.due
                self.ledger.append({"scope": list(generation.scope), "payload": generation.payload,
                                    "tick": generation.due, "generation": generation.generation})

    def _truth(self, scope):
        relevant = [g for g in self.generations if g.scope == scope]
        if any(g.committed is not None for g in relevant):
            return "COMMITTED"
        if relevant:
            return "PENDING"
        return "ABSENT"

    def _snapshot(self):
        self.snapshots[self.now] = {scope: self._truth(scope) for scope in self.bindings}

    def advance(self, tick):
        if tick < self.now:
            raise ValueError("Virtual clock cannot move backward")
        while self.now < tick:
            self.now += 1
            self._commit_due()
            self._snapshot()

    def create_record(self, payload, key, service="records", tenant="example-tenant", operation="create_record"):
        scope = self.scope(key, service, tenant, operation)
        if scope in self.bindings and self.bindings[scope] != payload:
            return "CONFLICT"
        live = [g for g in self.generations if g.scope == scope and self.now < g.accepted + self.contract.retention]
        if not live:
            self._accept(scope, payload, self._due(self.now))
        self._commit_due()
        self._snapshot()
        return "ACK"

    def status(self, key, service="records", tenant="example-tenant", operation="create_record"):
        scope = self.scope(key, service, tenant, operation)
        if self.contract.negative_status == "terminal":
            return self._truth(scope)
        # The lag is an evaluator parameter. It is NEVER disclosed as a guarantee.
        return self.snapshots.get(self.now - 4, {}).get(scope, "ABSENT")

    def drain_accepted_work(self):
        finite_due = [g.due for g in self.generations if g.due is not None]
        self.advance(max([self.now] + finite_due))
