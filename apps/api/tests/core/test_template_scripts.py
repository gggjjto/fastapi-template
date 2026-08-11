from __future__ import annotations

import importlib.util
import json
import os
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
        if relative.endswith("/SKILL.md"):
            name = Path(relative).parent.name
            content = f"---\nname: {name}\ndescription: test workflow\n---\n"
        _write(root / relative, content)
    return guard


def test_project_name_normalization() -> None:
    create_project = _load_script("create_project")

    names = create_project.build_project_names("My SaaS API")

    assert names.slug == "my-saas-api"
    assert names.package_name == "my_saas_api"
    assert names.display_name == "My Saas Api"


def test_project_name_package_is_prefixed_when_slug_starts_with_number() -> None:
    create_project = _load_script("create_project")

    names = create_project.build_project_names("2026 Reports")

    assert names.slug == "2026-reports"
    assert names.package_name == "project_2026_reports"


def test_load_template_manifest() -> None:
    create_project = _load_script("create_project")

    manifest = create_project.load_template_manifest("fastapi-api")

    assert manifest.id == "fastapi-api"
    assert manifest.version == "0.1.0"
    assert manifest.source.name == "api"
    assert "make api-ci" in manifest.post_create_steps
    assert {option.id for option in manifest.options} == {
        "ai",
        "auth",
        "rbac",
        "redis",
        "sentry",
        "worker",
    }
    assert "fastapi-api" in create_project.list_template_ids()


def test_load_template_manifest_rejects_missing_fields(tmp_path: Path) -> None:
    create_project = _load_script("create_project")
    template_dir = tmp_path / "broken"
    template_dir.mkdir()
    (template_dir / "template.json").write_text('{"id": "broken"}', encoding="utf-8")

    try:
        create_project.load_template_manifest("broken", root=tmp_path)
    except ValueError as exc:
        assert "missing required fields" in str(exc)
        assert "version" in str(exc)
    else:
        raise AssertionError("Expected invalid template manifest to fail")


def test_load_template_manifest_rejects_unknown_template() -> None:
    create_project = _load_script("create_project")

    try:
        create_project.load_template_manifest("missing-template")
    except ValueError as exc:
        assert "Unknown template" in str(exc)
    else:
        raise AssertionError("Expected unknown template to fail")


def test_template_options_validate_dependencies() -> None:
    create_project = _load_script("create_project")

    manifest = create_project.load_template_manifest("fastapi-api")
    selected = create_project.validate_template_options(manifest, ["auth", "rbac"])

    assert [option.id for option in selected] == ["auth", "rbac"]

    try:
        create_project.validate_template_options(manifest, ["rbac"])
    except ValueError as exc:
        assert "--with-rbac requires --with-auth" in str(exc)
    else:
        raise AssertionError("Expected rbac without auth to fail")


def test_template_options_reject_unsupported_option() -> None:
    create_project = _load_script("create_project")

    manifest = create_project.load_template_manifest("fastapi-api")

    try:
        create_project.validate_template_options(manifest, ["mobile"])
    except ValueError as exc:
        assert "does not support option(s): mobile" in str(exc)
    else:
        raise AssertionError("Expected unsupported option to fail")


def test_template_copy_excludes_runtime_directories(tmp_path: Path) -> None:
    create_project = _load_script("create_project")

    names = create_project.build_project_names("Demo API")
    target = tmp_path / "demo-api"

    create_project.copy_template(target, names)

    assert (target / "apps/api/pyproject.toml").exists()
    assert (target / "README.md").read_text(encoding="utf-8").startswith("# Demo Api")
    assert "Next.js" not in (target / "README.md").read_text(encoding="utf-8")
    api_makefile = (target / "apps/api/Makefile").read_text(encoding="utf-8")
    root_makefile = (target / "Makefile").read_text(encoding="utf-8")
    pyproject = (target / "apps/api/pyproject.toml").read_text(encoding="utf-8")
    env_example = (target / "apps/api/.env.example").read_text(encoding="utf-8")
    assert "demo-api:local" in api_makefile
    assert "hatchet-sdk" in pyproject
    assert '"arq' not in pyproject
    assert "HATCHET_CLIENT_TOKEN" in env_example
    assert "api-worker:" in root_makefile
    assert "uv run python -m app.worker" in api_makefile
    assert "pnpm" not in root_makefile
    assert "scripts/run_harness_evals.py" in root_makefile
    assert "create-project:" not in root_makefile
    generated_ci = (target / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "pnpm" not in generated_ci
    assert "make harness-check" in generated_ci
    assert "migrations:" in generated_ci
    assert "docker-build:" in generated_ci
    assert ".omx/" in (target / ".gitignore").read_text(encoding="utf-8")
    harness_doc = (target / "docs/harness-engineering.md").read_text(encoding="utf-8")
    assert "no inherited live-evaluation status" in harness_doc
    assert (target / "scripts/create_project.py").exists()
    assert (target / "AGENTS.md").exists()
    assert (target / ".agents/README.md").exists()
    assert (target / ".agents/evals/cases.json").exists()
    assert (target / ".agents/rules/INDEX.md").exists()
    assert (target / ".agents/skills/feature/SKILL.md").exists()
    assert (target / ".agents/skills/fix-bug/SKILL.md").exists()
    assert (target / ".agents/skills/ship-change/SKILL.md").exists()
    assert (target / "skills-lock.json").exists()
    assert not (target / ".git").exists()
    assert not (target / ".codex").exists()
    assert not (target / ".venv").exists()
    assert not (target / ".omx").exists()
    assert not (target / "templates").exists()


def test_template_copy_uses_selected_manifest(tmp_path: Path) -> None:
    create_project = _load_script("create_project")

    names = create_project.build_project_names("Selected API")
    manifest = create_project.load_template_manifest("fastapi-api")
    target = tmp_path / "selected-api"

    create_project.copy_template(target, names, manifest=manifest)

    for generated_path in manifest.generated_paths:
        assert (target / generated_path).exists(), generated_path


def test_generated_fastapi_template_static_checks(tmp_path: Path) -> None:
    create_project = _load_script("create_project")

    names = create_project.build_project_names("Generated API")
    target = tmp_path / "generated-api"

    create_project.copy_template(target, names)

    env = {**os.environ, "UV_NO_PROGRESS": "1"}
    for command in (
        "api-lint",
        "api-format-check",
        "api-typecheck",
        "api-check-ai",
        "harness-check",
    ):
        result = subprocess.run(
            ["make", command],
            cwd=target,
            env=env,
            capture_output=True,
            check=False,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr


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


def test_harness_guard_generator_contract(tmp_path: Path) -> None:
    guard = _minimal_harness(tmp_path)
    generated_paths = sorted(guard.PORTABLE_HARNESS_PATHS)
    _write(
        tmp_path / "templates/fastapi-api/template.json",
        '{"generated_paths": ' + json.dumps(generated_paths) + "}",
    )
    _write(
        tmp_path / "scripts/create_project.py",
        "WORKSPACE_SUPPORT_PATHS = [\n"
        '    ".agents",\n'
        '    "skills-lock.json",\n'
        '    "docs/harness-engineering.md",\n'
        "]\n",
    )

    assert guard.check_generator_contract(tmp_path) == []
    _write(tmp_path / "templates/fastapi-api/template.json", '{"generated_paths": []}')

    failures = guard.check_generator_contract(tmp_path)
    assert any("generated_paths omits" in failure for failure in failures)


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

    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"schema_version": 2, "cases": []}', encoding="utf-8")
    try:
        evaluator.load_catalog(invalid)
    except ValueError as exc:
        assert "schema_version" in str(exc)
    else:
        raise AssertionError("Expected invalid Harness eval schema to fail")

    unsafe = json.loads((root / ".agents/evals/cases.json").read_text(encoding="utf-8"))
    unsafe["cases"][0]["assertions"][0]["path"] = "../outside"
    unsafe_path = tmp_path / "unsafe.json"
    unsafe_path.write_text(json.dumps(unsafe), encoding="utf-8")
    try:
        evaluator.load_catalog(unsafe_path)
    except ValueError as exc:
        assert "inside the workspace" in str(exc)
    else:
        raise AssertionError("Expected a path traversal case to fail")

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


def test_generator_prints_selected_template_options(tmp_path: Path) -> None:
    target = tmp_path / "selected-options-api"

    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[4] / "scripts" / "create_project.py"),
            "Selected Options API",
            str(target),
            "--with-auth",
            "--with-rbac",
            "--with-redis",
            "--with-worker",
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "from fastapi-api@0.1.0" in result.stdout
    assert "Selected capabilities:" in result.stdout
    assert "--with-auth" in result.stdout
    assert "--with-worker" in result.stdout
    assert (target / "apps/api/app").exists()


def test_generator_prints_template_version(tmp_path: Path) -> None:
    target = tmp_path / "versioned-api"

    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[4] / "scripts" / "create_project.py"),
            "Versioned API",
            str(target),
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Created Versioned Api from fastapi-api@0.1.0" in result.stdout


def test_generator_rejects_invalid_template_option_combination(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[4] / "scripts" / "create_project.py"),
            "Invalid Options API",
            str(tmp_path / "invalid-options-api"),
            "--with-rbac",
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=60,
    )

    assert result.returncode == 2
    assert "--with-rbac requires --with-auth" in result.stderr


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


def test_doctor_loads_template_profile() -> None:
    doctor = _load_script("doctor")

    profile = doctor.load_doctor_profile("fastapi-api")

    assert profile.template_id == "fastapi-api"
    assert profile.required_tools == ["python>=3.12", "uv", "docker"]


def test_doctor_collects_checks_for_template(monkeypatch) -> None:
    doctor = _load_script("doctor")

    monkeypatch.setattr(
        doctor, "check_python", lambda: doctor.CheckResult("python", True, "3.12.0")
    )
    monkeypatch.setattr(
        doctor, "check_command", lambda command: doctor.CheckResult(command, True, "ok")
    )
    monkeypatch.setattr(
        doctor,
        "check_docker_compose",
        lambda: doctor.CheckResult("docker compose", True, "ok"),
    )
    monkeypatch.setattr(
        doctor, "check_api_root", lambda: doctor.CheckResult("apps/api", True, "ok")
    )
    monkeypatch.setattr(
        doctor, "check_env_file", lambda: doctor.CheckResult("apps/api/.env", True, "ok")
    )
    monkeypatch.setattr(
        doctor,
        "check_env_var",
        lambda name: doctor.CheckResult(name, True, "optional"),
    )

    results = doctor.collect_checks("fastapi-api")

    assert [result.name for result in results] == [
        "python",
        "uv",
        "docker compose",
        "apps/api",
        "apps/api/.env",
        "APP_DATABASE_URL",
        "APP_REDIS_URL",
        "APP_JWT_SECRET",
    ]
    assert "node" not in {result.name for result in results}
    assert "pnpm" not in {result.name for result in results}


def test_doctor_rejects_unknown_template() -> None:
    doctor = _load_script("doctor")

    try:
        doctor.load_doctor_profile("missing-template")
    except ValueError as exc:
        assert "Unknown template: missing-template" in str(exc)
    else:
        raise AssertionError("Expected unknown doctor template to fail")
