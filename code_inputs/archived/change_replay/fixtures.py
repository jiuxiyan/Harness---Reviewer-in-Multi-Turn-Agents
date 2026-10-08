"""Explicit HANDSCRIPTED instrumentation fixtures, never model trajectories.

Two tapes per task use the same action skeleton with different assistant wording.
Answers here are authored scripts, not observed model successes.
"""
from copy import deepcopy
import json
from common import ROOT, canonical

NESTED_A = {"owner": {"name": "Zoë", "aliases": ["Q", "ß"]}, "ids": ["X-1", "x-2"]}
NESTED_R = {"owner": {"name": "東京", "aliases": ["Zoë", "ß"]}, "ids": ["R-3", "r-3"]}
CURSOR_1 = "Cursor-00000001-opaque"
CURSOR_2 = "Cursor-00000002-opaque"
LONG_TEXT = "国際的な観測・Zoë・Straße・" * 256


def call(name, **arguments):
    return {"tool_call": {"name": name, "arguments": arguments}}


def final(value):
    return {"final": {"result": value}}


# No mutation identities, checker imports, or selector features in these scripts.
SCRIPTS = {
    "A1": [call("get", id="AbC-07"), final("Alpha")],
    "A2": [call("get", id="Straße-東京"), final("Bridge")],
    "A3": [call("query", query=NESTED_A), final("Nested")],
    "A4": [call("get", id="plain-4"), final("Plain")],
    "P1": [call("list", collection="p1"), call("list", collection="p1", cursor=CURSOR_1), call("list", collection="p1", cursor=CURSOR_2), final(["a", "b", "c"])],
    "P2": [call("list", collection="p2"), final(["one"])],
    "P3": [call("list", collection="p3"), call("list", collection="p3", cursor=CURSOR_1), final(["東京", "Zürich"])],
    "P4": [call("list", collection="p4"), call("list", collection="p4", cursor=CURSOR_1), final(["late"])],
    "E1": [call("read", id="e1"), final("Recovered")],
    "E2": [call("write", operation="e2", idempotency_key="op-E2"), final("r-1")],
    "E3": [call("read", id="e3"), final("bad_request")],
    "E4": [call("read", id="e4", source="primary"), call("read", id="e4", source="backup"), final("Backup")],
    "R1": [call("lookup", id="r1"), call("search", query="r1"), final("Found")],
    "R2": [call("lookup", id="r2"), final("Hit")],
    "R3": [call("lookup", query=NESTED_R), call("search", query=NESTED_R), final("東京-found")],
    "R4": [call("lookup", id="r4"), call("search", query="r4"), call("search", query="r4", cursor=CURSOR_1), final(["west", "east"])],
}


def public_tasks():
    return json.loads((ROOT / "public_tasks.json").read_text(encoding="utf-8"))


def tapes(task_id):
    result = []
    for number in (1, 2):
        responses = deepcopy(SCRIPTS[task_id])
        for i, response in enumerate(responses):
            response["content"] = ("" if number == 1 else f"Scripted fixture step {i + 1}.")
        result.append({"tape_id": f"{task_id}-T{number}", "source_kind": "HANDSCRIPTED", "responses": responses})
    return result


class UnsupportedPath(Exception):
    pass


class ToolWorld:
    """Each run owns an independent world; even bad writes stay local."""
    def __init__(self, task_id):
        self.task_id = task_id
        self.state = {"committed_writes": 0, "ledger": {}, "invocations": 0}

    def snapshot(self):
        return deepcopy(self.state)

    def invoke(self, name, args):
        self.state["invocations"] += 1
        task = self.task_id
        if name == "get":
            values = {"AbC-07": "Alpha", "Straße-東京": "Bridge", "plain-4": "Plain"}
            return {"label": values[args["id"]]} if args.get("id") in values else {"error": "not_found", "transient": False}
        if name == "query":
            return {"label": "Nested"} if args.get("query") == NESTED_A else {"error": "not_found", "transient": False}
        if name == "list":
            pages = {
                "p1": {None: {"items": ["a"], "next_cursor": CURSOR_1}, CURSOR_1: {"items": ["b"], "next_cursor": CURSOR_2}, CURSOR_2: {"items": ["c"], "next_cursor": None}},
                "p2": {None: {"items": ["one"], "next_cursor": None}},
                "p3": {None: {"items": ["東京"], "next_cursor": CURSOR_1, "detail": LONG_TEXT}, CURSOR_1: {"items": ["Zürich"], "next_cursor": None}},
                "p4": {None: {"items": [], "next_cursor": CURSOR_1}, CURSOR_1: {"items": ["late"], "next_cursor": None}},
            }
            page = pages.get(args.get("collection"), {}).get(args.get("cursor"))
            return deepcopy(page) if page is not None else {"error": "bad_cursor", "transient": False}
        if name == "read":
            if task == "E1":
                return {"error": "unavailable", "transient": True} if self.state["invocations"] == 1 else {"label": "Recovered"}
            if task == "E3":
                return {"error": "bad_request", "transient": False}
            if task == "E4":
                return {"error": "not_found", "transient": False} if args.get("source") == "primary" else {"label": "Backup"}
        if name == "write" and task == "E2":
            key = args.get("idempotency_key")
            if key is not None and key in self.state["ledger"]:
                return {"receipt": self.state["ledger"][key], "deduplicated": True}
            self.state["committed_writes"] += 1
            receipt = "r-" + str(self.state["committed_writes"])
            if key is not None:
                self.state["ledger"][key] = receipt
            if self.state["invocations"] == 1:
                return {"error": "response_timeout_after_commit", "transient": True}
            return {"receipt": receipt, "deduplicated": False}
        if name == "lookup":
            if task == "R2":
                return {"items": ["Hit"]}
            return {"items": []}
        if name == "search":
            if task == "R1":
                return {"items": ["Found"]}
            if task == "R3":
                return {"items": ["東京-found"]} if args.get("query") == NESTED_R else {"items": []}
            if task == "R4":
                return {"items": ["west"], "next_cursor": CURSOR_1} if args.get("cursor") is None else {"items": ["east"], "next_cursor": None}
        raise UnsupportedPath("No authored fixture for tool path")
