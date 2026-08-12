from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / ".agents/evals/cases.json"
ALLOWED_COMMAND = ["python3", "scripts/check_ai_workflow.py"]
COPY_EXCLUDES = (
    ".git",
    ".mypy_cache",
    ".next",
    ".omx",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
)
REQUIRED_CASE_FIELDS = {
    "id",
    "fixture",
    "command",
    "assertions",
    "expected_exit_code",
    "expected_output",
    "forbidden_output",
}


def _validate_relative_path(raw_path: str, context: str) -> None:
    path = Path(raw_path)
    if not raw_path or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{context}: path must stay inside the workspace: {raw_path!r}")


def load_catalog(path: Path) -> dict[str, Any]:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if catalog.get("schema_version") != 1:
        raise ValueError("catalog schema_version must be 1")
    cases = catalog.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("catalog cases must be a non-empty list")
    ids: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or REQUIRED_CASE_FIELDS - set(case):
            missing = sorted(REQUIRED_CASE_FIELDS - set(case if isinstance(case, dict) else {}))
            raise ValueError(f"cases[{index}] is missing required fields: {', '.join(missing)}")
        if case["id"] in ids:
            raise ValueError(f"duplicate case id: {case['id']}")
        ids.add(case["id"])
        if case["fixture"] != "repository_copy":
            raise ValueError(f"{case['id']}: unsupported fixture {case['fixture']!r}")
        if case["command"] != ALLOWED_COMMAND:
            raise ValueError(f"{case['id']}: command is outside the deterministic allowlist")
        if not isinstance(case["expected_exit_code"], int):
            raise ValueError(f"{case['id']}: expected_exit_code must be an integer")
        for field in ("assertions", "expected_output", "forbidden_output"):
            if not isinstance(case[field], list):
                raise ValueError(f"{case['id']}: {field} must be a list")
        for action in case.get("setup", []):
            if isinstance(action, dict):
                _validate_relative_path(action.get("path", ""), f"{case['id']} setup")
        for assertion in case["assertions"]:
            if not isinstance(assertion, dict):
                raise ValueError(f"{case['id']}: assertions must contain objects")
            _validate_relative_path(assertion.get("path", ""), f"{case['id']} assertion")
    return catalog


def _apply_setup(workspace: Path, setup: list[dict[str, str]]) -> None:
    for action in setup:
        if action.get("kind") != "create_directory" or not action.get("path"):
            raise ValueError(f"unsupported setup action: {action}")
        _workspace_path(workspace, action["path"]).mkdir(parents=True, exist_ok=True)


def _workspace_path(workspace: Path, raw_path: str) -> Path:
    relative = Path(raw_path)
    if relative.is_absolute():
        raise ValueError(f"path escapes workspace: {raw_path}")
    resolved = (workspace / relative).resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes workspace: {raw_path}") from exc
    return resolved


def _check_assertions(workspace: Path, assertions: list[dict[str, str]]) -> list[str]:
    failures: list[str] = []
    for assertion in assertions:
        path = _workspace_path(workspace, assertion.get("path", ""))
        if assertion.get("kind") == "path_exists":
            if not path.exists():
                failures.append(f"missing path: {assertion.get('path')}")
        elif assertion.get("kind") == "file_contains":
            value = assertion.get("value", "")
            if not path.is_file() or value not in path.read_text(encoding="utf-8"):
                failures.append(f"{assertion.get('path')} does not contain {value!r}")
        else:
            failures.append(f"unsupported assertion: {assertion}")
    return failures


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"harness-{case['id']}-") as temporary:
        workspace = Path(temporary) / "project"
        shutil.copytree(
            ROOT,
            workspace,
            ignore=shutil.ignore_patterns(*COPY_EXCLUDES),
        )

        _apply_setup(workspace, case.get("setup", []))
        result = subprocess.run(
            case["command"],
            cwd=workspace,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
        output = result.stdout + result.stderr
        failures = _check_assertions(workspace, case["assertions"])
        if result.returncode != case["expected_exit_code"]:
            failures.append(f"exit code {result.returncode}, expected {case['expected_exit_code']}")
        failures.extend(
            f"missing output fragment: {fragment!r}"
            for fragment in case["expected_output"]
            if fragment not in output
        )
        failures.extend(
            f"forbidden output fragment: {fragment!r}"
            for fragment in case["forbidden_output"]
            if fragment in output
        )
        return {"id": case["id"], "passed": not failures, "failures": failures}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic repository Harness evaluations")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--case", dest="case_id")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        catalog = load_catalog(args.catalog)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Harness eval catalog invalid: {exc}")
        return 2

    cases = catalog["cases"]
    if args.case_id:
        cases = [case for case in cases if case["id"] == args.case_id]
        if not cases:
            print(f"Unknown Harness eval case: {args.case_id}")
            return 2
    if args.dry_run:
        print(f"Harness eval catalog valid: {len(cases)} case(s)")
        return 0

    results = [run_case(case) for case in cases]
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{status} {result['id']}")
        for failure in result["failures"]:
            print(f"  - {failure}")
    passed = sum(result["passed"] for result in results)
    print(f"Harness evals: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
