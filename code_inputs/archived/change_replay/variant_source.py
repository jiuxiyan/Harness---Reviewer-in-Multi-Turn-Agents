"""Author independent synthetic edits to pure deterministic harness hooks.

The actual generated source files, rather than hand-assigned fault tags, define
AST diff IDs. Function contract/capability labels are not added to the selector.
"""
import ast
import hashlib
from types import SimpleNamespace
from common import ROOT, component_id, digest, file_hash, save_json

BASE = '''from copy import deepcopy

def system_prompt():
    return "Use tools to satisfy the user. Preserve exact values. Finish only when complete."

def normalize_arguments(arguments):
    return deepcopy(arguments)

def prepare_observation(observation):
    return deepcopy(observation)

def retry_arguments(tool, arguments, observation, attempt):
    if attempt == 0 and observation.get("transient") is True and (tool != "write" or "idempotency_key" in arguments):
        return deepcopy(arguments)
    return None

def should_terminate(tool, observation):
    return False
'''

VARIANTS = {
    "C_NO_OP": BASE,
    "C_REFACTOR": BASE.replace("    return deepcopy(arguments)\n\ndef prepare", "    preserved = deepcopy(arguments)\n    return preserved\n\ndef prepare", 1),
    "C_GLOBAL_PROMPT": BASE.replace("Finish only when complete.", "Finish only when complete. Use concise responses."),
    "M_ARGUMENT_NORMALIZATION": BASE.replace("    return deepcopy(arguments)\n\ndef prepare", '''    def lower(value):
        if isinstance(value, str):
            return value.casefold()
        if isinstance(value, list):
            return [lower(item) for item in value]
        if isinstance(value, dict):
            return {key: lower(item) for key, item in value.items()}
        return value
    return lower(deepcopy(arguments))

def prepare''', 1),
    "M_CURSOR_TRUNCATION": BASE.replace("    return deepcopy(observation)", '''    result = deepcopy(observation)
    if isinstance(result.get("next_cursor"), str):
        result["next_cursor"] = result["next_cursor"][:8]
    return result''', 1),
    "M_RETRY_IDEMPOTENCY": BASE.replace('if attempt == 0 and observation.get("transient") is True and (tool != "write" or "idempotency_key" in arguments):\n        return deepcopy(arguments)', '''if attempt == 0 and observation.get("error"):
        retried = deepcopy(arguments)
        if tool == "write":
            retried.pop("idempotency_key", None)
        return retried''', 1),
    "M_PREMATURE_TERMINATION": BASE.replace("    return False", '''    if observation.get("items") == []:
        return True
    return False''', 1),
}


def load_source(source):
    namespace = {}
    exec(compile(source, "<local-authored-hooks>", "exec"), namespace)
    return SimpleNamespace(**{name: value for name, value in namespace.items() if not name.startswith("__")})


def functions(source):
    return {node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}


def structural_diff(source):
    before, after = functions(BASE), functions(source)
    result = []
    for name in sorted(set(before) | set(after)):
        old = ast.dump(before[name], include_attributes=False) if name in before else None
        new = ast.dump(after[name], include_attributes=False) if name in after else None
        if old != new:
            result.append({"diff_id": "ast-" + digest([name, old, new])[:24], "component_id": component_id(name), "component_name_for_audit_only": name})
    return result


def write_sources():
    folder = ROOT / "variants"
    folder.mkdir(exist_ok=True)
    (folder / "H0.py").write_text(BASE, encoding="utf-8")
    for name, source in VARIANTS.items():
        (folder / (name + ".py")).write_text(source, encoding="utf-8")
    manifest = {"source_kind": "locally_authored_synthetic_edits", "files": {path.name: file_hash(path) for path in sorted(folder.glob("*.py"))}, "structural_diffs": {name: structural_diff(source) for name, source in VARIANTS.items()}}
    save_json(ROOT / "variant_manifest.json", manifest)
    return manifest
