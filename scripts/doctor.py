from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
TEMPLATES_ROOT = ROOT / "templates"


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class DoctorProfile:
    template_id: str
    required_tools: list[str]


def _run(command: Sequence[str], *, cwd: Path = ROOT) -> Optional[subprocess.CompletedProcess[str]]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def check_python() -> CheckResult:
    if shutil.which("uv") and API_ROOT.exists():
        result = _run(
            [
                "uv",
                "run",
                "python",
                "-c",
                "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')",
            ],
            cwd=API_ROOT,
        )
        if result and result.returncode == 0:
            detail = result.stdout.strip()
            major, minor, *_ = [int(part) for part in detail.split(".")]
            ok = (major, minor) >= (3, 12)
            if not ok:
                detail = f"{detail}; requires Python >= 3.12"
            return CheckResult("python", ok, detail)

    version = sys.version_info
    ok = version >= (3, 12)
    detail = f"{version.major}.{version.minor}.{version.micro}"
    if not ok:
        detail = f"{detail}; requires Python >= 3.12"
    return CheckResult("python", ok, detail)


def check_command(command: str, version_args: Sequence[str] = ("--version",)) -> CheckResult:
    path = shutil.which(command)
    if not path:
        return CheckResult(command, False, "not found on PATH")

    result = _run([command, *version_args])
    if result is None:
        return CheckResult(command, True, f"found at {path}; version check unavailable")

    output = (result.stdout or result.stderr).strip().splitlines()
    detail = output[0] if output else f"found at {path}"
    return CheckResult(command, result.returncode == 0, detail)


def check_api_root() -> CheckResult:
    if API_ROOT.exists():
        return CheckResult("apps/api", True, "API workspace exists")
    return CheckResult("apps/api", False, "missing API workspace")


def check_env_file() -> CheckResult:
    env_file = API_ROOT / ".env"
    example = API_ROOT / ".env.example"
    if env_file.exists():
        return CheckResult("apps/api/.env", True, ".env exists")
    if example.exists():
        return CheckResult("apps/api/.env", False, "missing; copy apps/api/.env.example to apps/api/.env")
    return CheckResult("apps/api/.env", False, "missing; apps/api/.env.example also missing")


def check_env_var(name: str, *, required: bool = False) -> CheckResult:
    value = os.environ.get(name)
    if value:
        redacted = value
        if any(token in name for token in ("SECRET", "PASSWORD", "TOKEN", "KEY")):
            redacted = "<set>"
        return CheckResult(name, True, redacted)
    if required:
        return CheckResult(name, False, "not set")
    return CheckResult(name, True, "not set; optional")


def check_docker_compose() -> CheckResult:
    docker = shutil.which("docker")
    if not docker:
        return CheckResult("docker compose", False, "docker not found on PATH")

    result = _run(["docker", "compose", "version"])
    if result is None:
        return CheckResult("docker compose", False, "version check failed")

    output = (result.stdout or result.stderr).strip().splitlines()
    detail = output[0] if output else "docker compose available"
    return CheckResult("docker compose", result.returncode == 0, detail)


def list_template_ids(*, root: Path = TEMPLATES_ROOT) -> list[str]:
    if not root.exists():
        return []
    return sorted(path.name for path in root.iterdir() if (path / "template.json").exists())


def load_doctor_profile(template_id: str, *, root: Path = TEMPLATES_ROOT) -> DoctorProfile:
    manifest_path = root / template_id / "template.json"
    if not manifest_path.exists():
        raise ValueError(f"Unknown template: {template_id}")

    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid template manifest JSON: {manifest_path}") from exc

    return DoctorProfile(
        template_id=template_id,
        required_tools=[str(tool) for tool in raw.get("required_tools", [])],
    )


def collect_tool_checks(required_tools: Sequence[str]) -> list[CheckResult]:
    checks: list[CheckResult] = []
    for tool in required_tools:
        if tool.startswith("python"):
            checks.append(check_python())
        elif tool == "uv":
            checks.append(check_command("uv"))
        elif tool == "docker":
            checks.append(check_docker_compose())
        else:
            checks.append(check_command(tool))
    return checks


def collect_checks(template_id: str = "fastapi-api") -> list[CheckResult]:
    profile = load_doctor_profile(template_id)
    return [
        *collect_tool_checks(profile.required_tools),
        check_api_root(),
        check_env_file(),
        check_env_var("APP_DATABASE_URL"),
        check_env_var("APP_REDIS_URL"),
        check_env_var("APP_JWT_SECRET"),
    ]


def render_results(results: Sequence[CheckResult], *, template_id: Optional[str] = None) -> str:
    title = "Development environment check"
    if template_id:
        title = f"{title} ({template_id})"
    lines = [f"{title}:"]
    for result in results:
        marker = "OK" if result.ok else "FAIL"
        lines.append(f"- [{marker}] {result.name}: {result.detail}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check local development prerequisites.")
    parser.add_argument(
        "--template",
        default="fastapi-api",
        choices=list_template_ids() or ["fastapi-api"],
        help="Template profile to check.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when any recommended local setup check fails.",
    )
    args = parser.parse_args(argv)

    results = collect_checks(args.template)
    print(render_results(results, template_id=args.template))

    if args.strict and any(not result.ok for result in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
