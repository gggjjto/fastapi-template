from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType


def _load_script(name: str) -> ModuleType:
    path = Path(__file__).resolve().parents[4] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _minimal_harness(root: Path) -> ModuleType:
    guard = _load_script("check_ai_workflow")
    for relative in guard.REQUIRED_PATHS:
        content = ""
        if relative.startswith("docs/") and relative.endswith(".md"):
            content = (
                "---\ndoc_type: index\nstatus: active\nauthority: supporting\n"
                "scope: test\nlast_reviewed: 2026-08-12\n---\n"
            )
        if relative.endswith("/SKILL.md"):
            name = Path(relative).parent.name
            content = f"---\nname: {name}\ndescription: test workflow\n---\n"
        _write(root / relative, content)
    return guard


def test_harness_guard_required_paths(tmp_path: Path) -> None:
    guard = _minimal_harness(tmp_path)

    assert guard.check_required_paths(tmp_path) == []
    (tmp_path / ".agents/README.md").unlink()

    failures = guard.check_required_paths(tmp_path)
    assert any(".agents/README.md" in failure and "Restore" in failure for failure in failures)


def test_harness_guard_internal_links(tmp_path: Path) -> None:
    guard = _minimal_harness(tmp_path)
    _write(tmp_path / ".agents/rules/example.md", "# Example\n")
    _write(tmp_path / "AGENTS.md", "[valid](.agents/rules/example.md)\n")

    assert guard.check_internal_links(tmp_path) == []
    _write(tmp_path / "AGENTS.md", "[broken](.agents/rules/missing.md)\n")

    failures = guard.check_internal_links(tmp_path)
    assert any("AGENTS.md" in failure and "missing.md" in failure for failure in failures)


def test_harness_guard_indexes_and_lifecycle(tmp_path: Path) -> None:
    guard = _minimal_harness(tmp_path)
    _write(tmp_path / ".agents/rules/example.md", "# Example\n")
    _write(tmp_path / ".agents/rules/INDEX.md", "- `example.md`\n")
    _write(tmp_path / ".agents/requirements/topic.md", "# Topic\n")
    _write(tmp_path / ".agents/requirements/INDEX.md", "- `topic.md`\n")
    _write(tmp_path / ".agents/requirements.md", "### Active\n**Status:** Accepted\n")

    assert guard.check_index_coverage(tmp_path) == []
    assert guard.check_active_requirements(tmp_path) == []

    _write(tmp_path / ".agents/rules/INDEX.md", "# Empty\n")
    _write(tmp_path / ".agents/requirements.md", "### Old work\n**Status:** Completed\n")
    assert any("example.md" in failure for failure in guard.check_index_coverage(tmp_path))
    assert any("Old work" in failure for failure in guard.check_active_requirements(tmp_path))


def test_harness_guard_skill_shape(tmp_path: Path) -> None:
    guard = _minimal_harness(tmp_path)
    skill = tmp_path / ".agents/skills/example/SKILL.md"
    _write(skill, "---\nname: example\ndescription: example workflow\n---\n")

    assert guard.check_skill_shape(tmp_path) == []
    _write(skill, "---\nname: wrong\n---\n")

    failures = guard.check_skill_shape(tmp_path)
    assert any("description" in failure for failure in failures)
    assert any("does not match" in failure for failure in failures)


def test_harness_guard_documentation_contract(tmp_path: Path) -> None:
    guard = _minimal_harness(tmp_path)
    _write(
        tmp_path / "docs/README.md",
        "---\ndoc_type: index\nstatus: active\nauthority: normative\n"
        "scope: docs\nlast_reviewed: 2026-08-12\n---\n"
        "[ADR](adr/0002-documentation-as-a-governed-knowledge-system.md)\n"
        "[Harness](harness-engineering.md)\n"
        "[Guide](guide.md)\n",
    )
    _write(
        tmp_path / "docs/guide.md",
        "---\ndoc_type: runbook\nstatus: active\nauthority: supporting\n"
        "scope: test\nlast_reviewed: 2026-08-12\n---\n",
    )

    assert guard.check_documentation_contract(tmp_path) == []

    _write(
        tmp_path / "docs/guide.md",
        "---\ndoc_type: runbook\nstatus: historical\nauthority: normative\n"
        "scope: test\nlast_reviewed: yesterday\n---\n",
    )
    failures = guard.check_documentation_contract(tmp_path)
    assert any("non-active document is normative" in failure for failure in failures)
    assert any("invalid last_reviewed date" in failure for failure in failures)


def test_harness_guard_import_boundaries(tmp_path: Path) -> None:
    guard = _minimal_harness(tmp_path)
    app = tmp_path / "apps/api/app"
    _write(app / "users/models.py")
    _write(app / "users/repository.py", "from app.users.models import User\n")
    _write(app / "users/service.py", "from app.users.models import User\n")
    _write(app / "core/config.py", "from pathlib import Path\n")

    assert guard.check_import_boundaries(tmp_path) == []

    _write(app / "users/repository.py", "from fastapi import Depends\n")
    _write(app / "users/service.py", "from app.users.dependencies import CurrentUser\n")
    _write(app / "core/config.py", "from app.users.models import User\n")
    failures = guard.check_import_boundaries(tmp_path)

    assert any("repository imports HTTP layer" in failure for failure in failures)
    assert any("service imports HTTP layer" in failure for failure in failures)
    assert any("core imports business domain" in failure for failure in failures)


def test_deterministic_harness_eval_catalog_and_suite(tmp_path: Path) -> None:
    evaluator = _load_script("run_harness_evals")
    root = Path(__file__).resolve().parents[4]

    catalog = evaluator.load_catalog(root / ".agents/evals/cases.json")
    assert len(catalog["cases"]) == 5
    assert {case["fixture"] for case in catalog["cases"]} == {"repository_copy"}

    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"schema_version": 2, "cases": []}', encoding="utf-8")
    try:
        evaluator.load_catalog(invalid)
    except ValueError as exc:
        assert "schema_version" in str(exc)
    else:
        raise AssertionError("Expected invalid Harness eval schema to fail")

    result = subprocess.run(
        [sys.executable, str(root / "scripts/run_harness_evals.py")],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Harness evals: 5/5 passed" in result.stdout


def test_live_harness_eval_dry_run_and_disposable_execution(tmp_path: Path) -> None:
    evaluator = _load_script("eval_ai_workflow")
    root = Path(__file__).resolve().parents[4]
    catalog = evaluator.load_catalog(root / ".agents/evals/live-cases.json")
    assert len(catalog["cases"]) == 5

    dry_run = subprocess.run(
        [sys.executable, str(root / "scripts/eval_ai_workflow.py"), "--dry-run"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )
    assert dry_run.returncode == 0, dry_run.stdout + dry_run.stderr
    assert "no agent invoked" in dry_run.stdout

    output = tmp_path / "live-result.json"
    execution = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/eval_ai_workflow.py"),
            "--case",
            "forbidden-workflow-path",
            "--output",
            str(output),
            "--agent-command",
            sys.executable,
            "-c",
            "pass",
        ],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
        timeout=20,
    )
    assert execution.returncode == 0, execution.stdout + execution.stderr
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["results"][0]["result_class"] == "task_pass"
    assert result["results"][0]["changed_files"] == []


def test_live_harness_eval_detects_nested_environment_files(tmp_path: Path) -> None:
    evaluator = _load_script("eval_ai_workflow")
    nested_env = tmp_path / "apps/api/.env"
    _write(nested_env, "SECRET=value\n")

    snapshot = evaluator._snapshot(tmp_path)
    assert "apps/api/.env" in snapshot

    case = {"allowed_changes": ["apps/api/**"], "required_changes": []}
    violations = evaluator._policy_violations(case, ["apps/api/.env"], tmp_path)
    assert any("forbidden environment file" in violation for violation in violations)


def test_doctor_render_results() -> None:
    doctor = _load_script("doctor")

    output = doctor.render_results(
        [
            doctor.CheckResult("python", True, "3.12.0"),
            doctor.CheckResult(".env", False, "missing"),
        ]
    )

    assert "[OK] python: 3.12.0" in output
    assert "[FAIL] .env: missing" in output


def test_doctor_collects_repository_checks(monkeypatch) -> None:
    doctor = _load_script("doctor")

    monkeypatch.setattr(
        doctor, "collect_tool_checks", lambda tools: [doctor.CheckResult("tools", True, str(tools))]
    )
    monkeypatch.setattr(
        doctor, "check_api_root", lambda: doctor.CheckResult("apps/api", True, "ok")
    )
    monkeypatch.setattr(
        doctor, "check_env_file", lambda: doctor.CheckResult("apps/api/.env", True, "ok")
    )
    monkeypatch.setattr(
        doctor, "check_env_var", lambda name: doctor.CheckResult(name, True, "optional")
    )

    results = doctor.collect_checks()

    assert [result.name for result in results] == [
        "tools",
        "apps/api",
        "apps/api/.env",
        "APP_DATABASE_URL",
        "APP_REDIS_URL",
        "APP_JWT_SECRET",
    ]
