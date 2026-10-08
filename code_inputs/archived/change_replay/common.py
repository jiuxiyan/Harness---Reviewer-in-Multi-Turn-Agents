"""Lossless canonical JSON and hashes. No external dependencies or I/O services."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def verify_freeze():
    manifest = json.loads((ROOT / "freeze_manifest.json").read_text())
    for item in manifest["frozen_payloads"]:
        assert file_hash(ROOT / item["path"]) == item["sha256"], item["path"]
    return manifest


def component_id(name):
    return "component-" + hashlib.sha256(name.encode()).hexdigest()[:16]


def tie_hash(task_id):
    return hashlib.sha256(("change-replay-tie-v1:" + task_id).encode()).hexdigest()
