from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / ".agents/evals/live-cases.json"
RUNTIME_ROOT = ROOT / ".omx/harness-evals"
EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".omx",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
REQUIRED_FIELDS = {
    "id",
    "prompt",
    "setup",
    "sandbox",
    "timeout_seconds",
    "validators",
    "allowed_changes",
    "required_changes",
}


def load_catalog(path: Path) -> dict[str, Any]:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if catalog.get("schema_version") != 1:
        raise ValueError("live catalog schema_version must be 1")
    cases = catalog.get("cases")
    if not isinstance(cases, list) or len(cases) < 5:
        raise ValueError("live catalog must contain at least five cases")
    seen: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or REQUIRED_FIELDS - set(case):
            missing = sorted(REQUIRED_FIELDS - set(case if isinstance(case, dict) else {}))
            raise ValueError(f"cases[{index}] missing fields: {', '.join(missing)}")
        if case["id"] in seen:
            raise ValueError(f"duplicate case id: {case['id']}")
        seen.add(case["id"])
        if case["sandbox"] not in {"read-only", "workspace-write"}:
            raise ValueError(f"{case['id']}: unsupported sandbox")
        if not isinstance(case["timeout_seconds"], int) or case["timeout_seconds"] <= 0:
            raise ValueError(f"{case['id']}: timeout_seconds must be positive")
        if not case["validators"] or not all(
            isinstance(command, list) and command for command in case["validators"]
        ):
            raise ValueError(f"{case['id']}: validators must contain command arrays")
    return catalog


def _snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if not path.is_file() or EXCLUDED_PARTS.intersection(relative.parts):
            continue
        result[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _seed(workspace: Path, actions: list[str]) -> None:
    for action in actions:
        if action != "seed_request_id_regression":
            raise ValueError(f"unsupported live eval setup action: {action}")
        path = workspace / "apps/api/app/core/middleware.py"
        content = path.read_text(encoding="utf-8")
        original = "0 < len(request_id) <= _REQUEST_ID_MAX_LENGTH"
        if original not in content:
            raise ValueError("request-ID seed target not found")
        path.write_text(
            content.replace(original, "len(request_id) > _REQUEST_ID_MAX_LENGTH", 1),
            encoding="utf-8",
        )


def _agent_command(workspace: Path, case: dict[str, Any], override: list[str] | None) -> list[str]:
    if override:
        return [
            part.replace("{workspace}", str(workspace)).replace("{prompt}", case["prompt"])
            for part in override
        ]
    return [
        "codex",
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "--sandbox",
        case["sandbox"],
        "--cd",
        str(workspace),
        case["prompt"],
    ]


def _changed_files(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(
        path for path in before.keys() | after.keys() if before.get(path) != after.get(path)
    )


def _policy_violations(case: dict[str, Any], changed: list[str], workspace: Path) -> list[str]:
    violations = [
        f"unrelated file changed: {path}"
        for path in changed
        if not any(fnmatch.fnmatch(path, pattern) for pattern in case["allowed_changes"])
    ]
    for required in case["required_changes"]:
        if required not in changed:
            violations.append(f"required file unchanged: {required}")
    violations.extend(
        f"forbidden environment file changed: {path}"
        for path in changed
        if Path(path).name == ".env"
    )
    for path in workspace.rglob("*"):
        relative = path.relative_to(workspace)
        if {".codex", ".claude"}.intersection(relative.parts) or path.name == "CLAUDE.md":
            violations.append(f"forbidden path created: {relative.as_posix()}")
    return violations


def _run_validators(workspace: Path, commands: list[list[str]]) -> list[dict[str, Any]]:
    validations: list[dict[str, Any]] = []
    for command in commands:
        started = time.monotonic()
        result = subprocess.run(
            command, cwd=workspace, capture_output=True, check=False, text=True, timeout=60
        )
        output = (result.stdout + result.stderr)[-2000:]
        validations.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "duration_seconds": round(time.monotonic() - started, 3),
                "output": output,
            }
        )
    return validations


def run_case(
    case: dict[str, Any], agent_override: list[str] | None, preserve_failures: bool
) -> dict[str, Any]:
    started_at = dt.datetime.now(dt.timezone.utc)  # noqa: UP017 -- system Python 3.9
    started = time.monotonic()
    temporary = Path(tempfile.mkdtemp(prefix=f"live-harness-{case['id']}-"))
    workspace = temporary / "project"
    result_class = "infrastructure_fail"
    agent_exit_code: int | None = None
    timed_out = False
    validations: list[dict[str, Any]] = []
    changed: list[str] = []
    policy: list[str] = []
    try:
        shutil.copytree(
            ROOT,
            workspace,
            ignore=shutil.ignore_patterns(*sorted(EXCLUDED_PARTS | {".env"})),
        )
        _seed(workspace, case["setup"])
        before = _snapshot(workspace)
        command = _agent_command(workspace, case, agent_override)
        try:
            agent = subprocess.run(
                command,
                cwd=workspace,
                capture_output=True,
                check=False,
                text=True,
                timeout=case["timeout_seconds"],
            )
            agent_exit_code = agent.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
        after = _snapshot(workspace)
        changed = _changed_files(before, after)
        validations = _run_validators(workspace, case["validators"])
        policy = _policy_violations(case, changed, workspace)
        if timed_out:
            result_class = "timeout"
        elif policy:
            result_class = "policy_fail"
        elif any(item["exit_code"] != 0 for item in validations):
            result_class = "task_fail"
        elif agent_exit_code != 0:
            result_class = "infrastructure_fail"
        else:
            result_class = "task_pass"
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        validations.append(
            {"command": [], "exit_code": None, "duration_seconds": 0, "output": str(exc)}
        )
    finally:
        if preserve_failures and result_class != "task_pass":
            destination = RUNTIME_ROOT / "workspaces" / f"{case['id']}-{int(time.time())}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            if workspace.exists():
                shutil.copytree(
                    workspace, destination, ignore=shutil.ignore_patterns(".env", ".venv", ".omx")
                )
        shutil.rmtree(temporary, ignore_errors=True)
    ended_at = dt.datetime.now(dt.timezone.utc)  # noqa: UP017 -- system Python 3.9
    return {
        "case_id": case["id"],
        "catalog_version": 1,
        "result_class": result_class,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_seconds": round(time.monotonic() - started, 3),
        "attempt_count": 1,
        "agent_exit_code": agent_exit_code,
        "changed_files": changed,
        "validations": validations,
        "policy_violations": policy,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run optional live coding-agent Harness evaluations"
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--case", dest="case_id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preserve-failures", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--agent-command", nargs=argparse.REMAINDER)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        catalog = load_catalog(args.catalog)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Live Harness eval catalog invalid: {exc}")
        return 2
    cases = catalog["cases"]
    if args.case_id:
        cases = [case for case in cases if case["id"] == args.case_id]
        if not cases:
            print(f"Unknown live Harness eval case: {args.case_id}")
            return 2
    if args.dry_run:
        print(f"Live Harness eval catalog valid: {len(cases)} case(s); no agent invoked")
        return 0
    results = [run_case(case, args.agent_command, args.preserve_failures) for case in cases]
    summary = {
        "catalog_version": 1,
        "results": results,
        "task_pass_rate": sum(item["result_class"] == "task_pass" for item in results)
        / len(results),
        "policy_violation_count": sum(len(item["policy_violations"]) for item in results),
    }
    output = args.output or RUNTIME_ROOT / f"run-{int(time.time())}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for item in results:
        print(f"{item['result_class'].upper()} {item['case_id']} ({item['duration_seconds']}s)")
    print(f"Live Harness eval result: {output}")
    return 0 if all(item["result_class"] == "task_pass" for item in results) else 1


if __name__ == "__main__":
    sys.exit(main())
