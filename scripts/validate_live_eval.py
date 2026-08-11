from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(case_id: str) -> list[str]:
    if case_id == "health-endpoint":
        router = (ROOT / "apps/api/app/health/router.py").read_text(encoding="utf-8")
        tests = (ROOT / "apps/api/tests/health/test_health.py").read_text(encoding="utf-8")
        failures = []
        if '"/ping"' not in router and "'/ping'" not in router:
            failures.append("health router does not declare /ping")
        has_ok_status = '"status": "ok"' in router or "'status': 'ok'" in router
        if "ApiResponse" not in router or not has_ok_status:
            failures.append("ping endpoint does not use the standard status response")
        if "/api/v1/health/ping" not in tests:
            failures.append("health integration tests do not exercise /ping")
        return failures
    if case_id == "request-id-regression":
        middleware = (ROOT / "apps/api/app/core/middleware.py").read_text(encoding="utf-8")
        expected = "0 < len(request_id) <= _REQUEST_ID_MAX_LENGTH"
        return [] if expected in middleware else ["request-ID length validation was not restored"]
    if case_id == "config-field":
        config = (ROOT / "apps/api/app/core/config.py").read_text(encoding="utf-8")
        env_example = (ROOT / "apps/api/.env.example").read_text(encoding="utf-8")
        tests = (ROOT / "apps/api/tests/core/test_config.py").read_text(encoding="utf-8")
        failures = []
        if not re.search(
            r"request_timeout_seconds\s*:\s*int\s*=\s*Field\([^)]*(?:gt=0|ge=1)[^)]*le=300", config
        ):
            failures.append("request_timeout_seconds lacks bounded positive validation")
        if "APP_REQUEST_TIMEOUT_SECONDS" not in env_example:
            failures.append("API environment example omits APP_REQUEST_TIMEOUT_SECONDS")
        if "request_timeout_seconds" not in tests:
            failures.append("configuration tests do not cover request_timeout_seconds")
        return failures
    if case_id == "docs-command":
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        return (
            []
            if "make harness-check" in readme
            else ["README does not document make harness-check"]
        )
    return [f"unknown live eval case: {case_id}"]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_live_eval.py CASE_ID")
        return 2
    failures = validate(sys.argv[1])
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"Live eval validator passed: {sys.argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
