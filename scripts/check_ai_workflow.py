from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PATHS = (".claude", ".codex", "CLAUDE.md")
FORBIDDEN_REFERENCES = (".claude/", ".codex/", ".Codex/", "CLAUDE.md")
REFERENCE_ALLOWLIST = {
    "docs/adr/0001-use-agents-as-ai-workflow-source.md",
    ".agents/requirements.md",
}
SKIP_REFERENCE_FILES = {
    "scripts/check_ai_workflow.py",
    "scripts/eval_ai_workflow.py",
}
DISCOVERY_EXCLUDES = {
    ".git",
    ".mypy_cache",
    ".next",
    ".omx",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
PORTABLE_HARNESS_PATHS = {
    "AGENTS.md",
    "Makefile",
    ".agents/README.md",
    ".agents/rules/INDEX.md",
    ".agents/requirements.md",
    ".agents/requirements/INDEX.md",
    ".agents/evals/cases.json",
    ".agents/evals/live-cases.json",
    ".agents/skills/feature/SKILL.md",
    ".agents/skills/fix-bug/SKILL.md",
    ".agents/skills/ship-change/SKILL.md",
    "skills-lock.json",
    "docs/harness-engineering.md",
    "scripts/check_ai_workflow.py",
    "scripts/eval_ai_workflow.py",
    "scripts/run_harness_evals.py",
    "scripts/validate_live_eval.py",
}
REQUIRED_PATHS = tuple(sorted(PORTABLE_HARNESS_PATHS))
TERMINAL_REQUIREMENT_STATUSES = re.compile(
    r"\*\*Status:\*\*.*\b(?:complete(?:d)?|merged|superseded|abandoned)\b",
    re.IGNORECASE,
)
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def _failure(file_name: str, problem: str, remediation: str) -> str:
    return f"{file_name}: {problem}. {remediation}"


def discover_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.splitlines()

    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not DISCOVERY_EXCLUDES.intersection(path.relative_to(root).parts)
    )


def check_forbidden_paths(root: Path = ROOT) -> list[str]:
    return [
        _failure(path, "forbidden AI workflow path exists", "Move its authority into .agents")
        for path in FORBIDDEN_PATHS
        if (root / path).exists()
    ]


def check_forbidden_references(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    for file_name in discover_files(root):
        if file_name in REFERENCE_ALLOWLIST or file_name in SKIP_REFERENCE_FILES:
            continue
        path = root / file_name
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in FORBIDDEN_REFERENCES:
            if pattern in content:
                failures.append(
                    _failure(
                        file_name,
                        f"contains forbidden reference {pattern!r}",
                        "Link to .agents instead",
                    )
                )
    return failures


def check_required_paths(root: Path = ROOT) -> list[str]:
    return [
        _failure(path, "required Harness path is missing", "Restore it or update the contract")
        for path in REQUIRED_PATHS
        if not (root / path).exists()
    ]


def _harness_markdown_files(root: Path) -> list[Path]:
    candidates = [root / "AGENTS.md", root / ".agents/README.md", root / ".agents/requirements.md"]
    agents_root = root / ".agents"
    if agents_root.exists():
        candidates.extend((agents_root / "rules").glob("*.md"))
        candidates.extend((agents_root / "requirements").glob("*.md"))
    return sorted(path for path in candidates if path.is_file())


def check_internal_links(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    for path in _harness_markdown_files(root):
        content = path.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(content):
            target = raw_target.strip().strip("<>").split("#", 1)[0]
            if not target or "://" in target or target.startswith(("#", "/", "mailto:")):
                continue
            target = unquote(target.split(" ", 1)[0])
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                file_name = path.relative_to(root).as_posix()
                failures.append(
                    _failure(
                        file_name,
                        f"broken relative link {raw_target!r}",
                        "Fix the target or remove the link",
                    )
                )
    return failures


def _check_index(directory: Path, index_path: Path, root: Path) -> list[str]:
    if not directory.exists() or not index_path.exists():
        return []
    index = index_path.read_text(encoding="utf-8")
    failures: list[str] = []
    for path in sorted(directory.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        if path.name not in index:
            failures.append(
                _failure(
                    path.relative_to(root).as_posix(),
                    f"is not listed in {index_path.relative_to(root).as_posix()}",
                    "Add one index entry",
                )
            )
    return failures


def check_index_coverage(root: Path = ROOT) -> list[str]:
    return _check_index(
        root / ".agents/rules", root / ".agents/rules/INDEX.md", root
    ) + _check_index(
        root / ".agents/requirements",
        root / ".agents/requirements/INDEX.md",
        root,
    )


def check_active_requirements(root: Path = ROOT) -> list[str]:
    path = root / ".agents/requirements.md"
    if not path.exists():
        return []
    failures: list[str] = []
    heading = "active requirements"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            heading = line.removeprefix("### ").strip()
        if TERMINAL_REQUIREMENT_STATUSES.search(line):
            failures.append(
                _failure(
                    path.relative_to(root).as_posix(),
                    f"terminal item remains active under {heading!r}",
                    "Remove it; Git history is the archive",
                )
            )
    return failures


def _frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return values
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip("'\"")
    return {}


def check_skill_shape(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    skills_root = root / ".agents/skills"
    if not skills_root.exists():
        return failures
    for path in sorted(skills_root.glob("*/SKILL.md")):
        metadata = _frontmatter(path)
        relative = path.relative_to(root).as_posix()
        for field in ("name", "description"):
            if not metadata.get(field):
                failures.append(
                    _failure(relative, f"frontmatter field {field!r} is missing", "Add the field")
                )
        if metadata.get("name") and metadata["name"] != path.parent.name:
            failures.append(
                _failure(
                    relative,
                    "frontmatter name "
                    f"{metadata['name']!r} does not match directory {path.parent.name!r}",
                    "Make both names identical",
                )
            )
    for path in sorted(skills_root.glob("*/test-cases.json")):
        relative = path.relative_to(root).as_posix()
        try:
            catalog = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(
                _failure(relative, f"invalid JSON: {exc.msg}", "Repair or remove the catalog")
            )
            continue
        cases = catalog.get("testCases")
        if not isinstance(cases, list) or not cases:
            failures.append(
                _failure(
                    relative, "testCases must be a non-empty list", "Add executable case metadata"
                )
            )
            continue
        for index, case in enumerate(cases):
            if not isinstance(case, dict) or not all(
                case.get(field) for field in ("id", "query", "expectedBehavior")
            ):
                failures.append(
                    _failure(
                        relative,
                        f"testCases[{index}] lacks id, query, or expectedBehavior",
                        "Complete the case metadata",
                    )
                )
    return failures


def _import_names(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    # Keep the guard runnable with the system Python on macOS while the project
    # itself uses Python 3.12 PEP 695 generic class syntax.
    source = re.sub(r"^(class\s+\w+)\[[^]]+\](\s*\()", r"\1\2", source, flags=re.MULTILINE)
    tree = ast.parse(source, filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def check_import_boundaries(root: Path = ROOT) -> list[str]:
    app_root = root / "apps/api/app"
    if not app_root.exists():
        return []
    failures: list[str] = []
    infrastructure = {"core", "db"}
    business_domains = {
        path.name
        for path in app_root.iterdir()
        if path.is_dir() and path.name not in infrastructure and not path.name.startswith("__")
    }
    for path in sorted(app_root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        for imported in _import_names(path):
            parts = imported.split(".")
            is_http_layer = (
                imported == "fastapi"
                or imported.startswith("fastapi.")
                or bool({"router", "dependencies"}.intersection(parts))
            )
            if path.name == "repository.py" and is_http_layer:
                failures.append(
                    _failure(
                        relative,
                        f"repository imports HTTP layer {imported!r}",
                        "Move the dependency outward",
                    )
                )
            if path.name == "service.py" and is_http_layer:
                failures.append(
                    _failure(
                        relative,
                        f"service imports HTTP layer {imported!r}",
                        "Pass plain values or domain types",
                    )
                )
            if (
                "core" in path.relative_to(app_root).parts
                and len(parts) > 1
                and parts[0] == "app"
                and parts[1] in business_domains
            ):
                failures.append(
                    _failure(
                        relative,
                        f"core imports business domain {imported!r}",
                        "Reverse the dependency or document a narrow allowlist",
                    )
                )
    return failures


def run_checks(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    for check in (
        check_forbidden_paths,
        check_forbidden_references,
        check_required_paths,
        check_internal_links,
        check_index_coverage,
        check_active_requirements,
        check_skill_shape,
        check_import_boundaries,
    ):
        failures.extend(check(root))
    return failures


def main() -> int:
    failures = run_checks()
    if failures:
        print("AI workflow guard failed. Keep the repository-local Harness portable and truthful.")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("AI workflow guard passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
