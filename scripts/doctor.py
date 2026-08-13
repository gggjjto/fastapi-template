from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
REQUIRED_TOOLS = ("python>=3.12", "uv", "docker")


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def _run(command: Sequence[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str] | None:
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
                "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}.{v.micro}')",
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
        return CheckResult(
            "apps/api/.env", False, "missing; copy apps/api/.env.example to apps/api/.env"
        )
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


def collect_checks() -> list[CheckResult]:
    return [
        *collect_tool_checks(REQUIRED_TOOLS),
        check_api_root(),
        check_env_file(),
        check_env_var("APP_DATABASE_URL"),
        check_env_var("APP_REDIS_URL"),
        check_env_var("APP_JWT_SECRET"),
    ]


def render_results(results: Sequence[CheckResult]) -> str:
    lines = ["Development environment check:"]
    for result in results:
        marker = "OK" if result.ok else "FAIL"
        lines.append(f"- [{marker}] {result.name}: {result.detail}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check local development prerequisites.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when any recommended local setup check fails.",
    )
    args = parser.parse_args(argv)

    results = collect_checks()
    print(render_results(results))

    if args.strict and any(not result.ok for result in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
