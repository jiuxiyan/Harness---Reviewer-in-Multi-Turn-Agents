"""Evaluator-side construction of docs; policies see only its JSON output."""
from dataclasses import dataclass
from itertools import product
from .public import fixed_evidence


@dataclass(frozen=True)
class Contract:
    retention: int
    negative_status: str
    processing_bound: int | None


CONDITIONS = ("complete", "retention_omitted", "status_omitted",
              "processing_omitted", "status_contradiction")
OUTCOMES = ("rejected", "immediate_commit", "accepted_pending")
CONTRACTS = tuple(Contract(*x) for x in product((2, 8), ("terminal", "lagging"), (2, None)))


def claim(state: str, value=None) -> dict:
    return {"state": state, "value": value}


def make_evidence(contract: Contract, condition: str) -> dict:
    if condition not in CONDITIONS:
        raise ValueError(condition)
    result = fixed_evidence()
    result["contract_claims"] = {
        "retention_ticks": claim("known", contract.retention),
        "negative_status": claim("known", contract.negative_status),
        "processing_bound_ticks": claim("known", 2) if contract.processing_bound else claim("no_guarantee"),
    }
    result["status_definitions"] = {
        "terminal": "PENDING means accepted and unfinished; ABSENT means neither pending work nor a committed effect exists now.",
        "lagging": "Status may show an older snapshot, with no documented lag bound. ABSENT does not establish current absence.",
    }
    field = {"retention_omitted": "retention_ticks", "status_omitted": "negative_status",
             "processing_omitted": "processing_bound_ticks"}.get(condition)
    if field:
        result["contract_claims"][field] = claim("unknown")
    if condition == "status_contradiction":
        result["contract_claims"]["negative_status"] = claim("conflict", ["terminal", "lagging"])
        result["contradiction_notice"] = "Two equal-priority sources disagree about negative status. No precedence or resolution is provided."
    return result


def contract_matches(contract: Contract, evidence: dict) -> bool:
    values = {"retention_ticks": contract.retention,
              "negative_status": contract.negative_status,
              "processing_bound_ticks": contract.processing_bound}
    for name, entry in evidence["contract_claims"].items():
        if entry["state"] == "known" and values[name] != entry["value"]:
            return False
        if entry["state"] == "no_guarantee" and values[name] is not None:
            return False
    return True
