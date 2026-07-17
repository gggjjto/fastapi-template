from __future__ import annotations

import importlib.util
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


def test_template_copy_excludes_runtime_directories(tmp_path: Path) -> None:
    create_project = _load_script("create_project")

    names = create_project.build_project_names("Demo API")
    target = tmp_path / "demo-api"

    create_project.copy_template(target, names)

    assert (target / "apps/api/pyproject.toml").exists()
    assert (target / "README.md").read_text(encoding="utf-8").startswith("# Demo Api")
    assert "demo-api:local" in (target / "apps/api/Makefile").read_text(encoding="utf-8")
    assert not (target / ".git").exists()
    assert not (target / ".venv").exists()
    assert not (target / ".omx").exists()


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
