"""Sanitized offline launcher; never imports an upstream module in the parent."""
import hashlib
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PILOT = HERE.parent / "reviewer_pilot"
PRIVATE = HERE / ".runtime"
for name in ("home", "xdg", "cache", "hf"):
    (PRIVATE / name).mkdir(parents=True, exist_ok=True)
env = {
    "PATH": str(PILOT / ".venv/bin") + ":/usr/bin:/bin",
    "HOME": str(PRIVATE / "home"), "XDG_CONFIG_HOME": str(PRIVATE / "xdg"),
    "XDG_CACHE_HOME": str(PRIVATE / "cache"), "HF_HOME": str(PRIVATE / "hf"),
    "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
    "TAU2_DATA_DIR": str(PILOT / "upstream/data"),
    "PYTHON_DOTENV_DISABLED": "1", "LITELLM_MODE": "PRODUCTION",
    "LITELLM_LOCAL_MODEL_COST_MAP": "true", "LITELLM_DISABLE_LAZY_LOADING": "false",
    "HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
    "TOKENIZERS_PARALLELISM": "false", "PYTHONHASHSEED": "0",
}
# All ordinary frozen backend files, excluding runtime directories and bytecode.
def snapshot():
    paths = [p for p in PILOT.rglob("*") if p.is_file() and not any(
        part.startswith(".") or part.startswith("private_") or part == "__pycache__"
        for part in p.relative_to(PILOT).parts)]
    return {str(p.relative_to(PILOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
# Verify the recorded source pin and every official file before guarded imports.
commit = "4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699"
assert json.loads((PILOT / "commit_response.json").read_text())["sha"] == commit
source_manifest = json.loads((PILOT / "source_manifest_final.json").read_text())
for row in source_manifest:
    actual = hashlib.sha256((PILOT / "upstream" / row["path"]).read_bytes()).hexdigest()
    if actual != row["sha256"]:
        raise SystemExit("Pinned source differs from frozen manifest: " + row["path"])
(HERE / "results/source_pin_check.json").write_text(json.dumps({
    "commit": commit, "official_files_verified": len(source_manifest),
    "all_match_recorded_sha256": True, "network_verification_performed": False,
    "source": "Previously verified frozen local manifest and commit response",
}, indent=2) + "\n")
before = snapshot()
result = subprocess.run([str(PILOT / ".venv/bin/python"), "-I", "-B", str(HERE / "worker.py"), *sys.argv[1:]],
                        cwd=HERE, env=env, capture_output=True, text=True)
after = snapshot()
unchanged = before == after
(HERE / "results/dependency_readonly_check.json").write_text(json.dumps({
    "frozen_backend_files_checked": len(before), "all_unchanged": unchanged,
    "scope": "non-runtime backend/source/evidence files; -B also suppresses dependency bytecode writes",
    "manifest_before_sha256": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
    "manifest_after_sha256": hashlib.sha256(json.dumps(after, sort_keys=True).encode()).hexdigest(),
}, indent=2) + "\n")
print(result.stdout, end="")
if result.stderr:
    print(result.stderr, end="", file=sys.stderr)
if not unchanged:
    raise SystemExit("Frozen dependency changed")
sys.exit(result.returncode)
