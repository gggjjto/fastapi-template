from __future__ import annotations

import importlib.util
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
    assert "demo-api:local" in (target / "apps/api/Makefile").read_text(encoding="utf-8")
    assert "pnpm" not in (target / "Makefile").read_text(encoding="utf-8")
    assert (target / "scripts/create_project.py").exists()
    assert not (target / ".git").exists()
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
    for command in ("api-lint", "api-format-check", "api-typecheck"):
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
            "--with-worker",
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=60,
    )

    assert result.returncode == 2
    assert "--with-worker requires --with-redis" in result.stderr


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
