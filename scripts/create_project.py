from __future__ import annotations

import argparse
import json
import re
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_ROOT = ROOT / "templates"

DEFAULT_EXCLUDES = {
    ".git",
    ".mypy_cache",
    ".omx",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "coverage.xml",
    ".coverage",
    "htmlcov",
    "dist",
    "build",
    "*.egg-info",
}

TEXT_SUFFIXES = {
    ".cfg",
    ".dockerignore",
    ".env",
    ".example",
    ".gitignore",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

WORKSPACE_SUPPORT_PATHS = [
    ".github",
    ".gitignore",
    ".pre-commit-config.yaml",
    "AGENTS.md",
    "LICENSE",
    "Makefile",
    "README.md",
    "docs/conventions",
    "docs/recipes",
    "scripts",
]


@dataclass(frozen=True)
class ProjectNames:
    display_name: str
    package_name: str
    slug: str


@dataclass(frozen=True)
class TemplateManifest:
    id: str
    name: str
    description: str
    source: Path
    default_target: str
    required_tools: list[str]
    generated_paths: list[str]
    post_create_steps: list[str]
    verification: list[str]


REQUIRED_MANIFEST_FIELDS = {
    "id",
    "name",
    "description",
    "source",
    "default_target",
    "required_tools",
    "generated_paths",
    "post_create_steps",
    "verification",
}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "new-project"


def package_name_from_slug(slug: str) -> str:
    package_name = slug.replace("-", "_")
    if package_name[0].isdigit():
        package_name = f"project_{package_name}"
    return package_name


def build_project_names(name: str) -> ProjectNames:
    slug = slugify(name)
    display_name = " ".join(part.capitalize() for part in slug.split("-"))
    return ProjectNames(
        display_name=display_name,
        package_name=package_name_from_slug(slug),
        slug=slug,
    )


def load_template_manifest(template_id: str, *, root: Path = TEMPLATES_ROOT) -> TemplateManifest:
    manifest_path = root / template_id / "template.json"
    if not manifest_path.exists():
        raise ValueError(f"Unknown template: {template_id}")

    try:
        raw: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid template manifest JSON: {manifest_path}") from exc

    missing = REQUIRED_MANIFEST_FIELDS - raw.keys()
    if missing:
        fields = ", ".join(sorted(missing))
        raise ValueError(f"Template manifest {manifest_path} is missing required fields: {fields}")

    source = (manifest_path.parent / str(raw["source"])).resolve()
    if not source.exists():
        raise ValueError(f"Template source does not exist: {source}")

    return TemplateManifest(
        id=str(raw["id"]),
        name=str(raw["name"]),
        description=str(raw["description"]),
        source=source,
        default_target=str(raw["default_target"]),
        required_tools=[str(item) for item in raw["required_tools"]],
        generated_paths=[str(item) for item in raw["generated_paths"]],
        post_create_steps=[str(item) for item in raw["post_create_steps"]],
        verification=[str(item) for item in raw["verification"]],
    )


def list_template_ids(*, root: Path = TEMPLATES_ROOT) -> list[str]:
    if not root.exists():
        return []
    return sorted(path.name for path in root.iterdir() if (path / "template.json").exists())


def _matches_exclude(path: Path, patterns: Iterable[str]) -> bool:
    parts = set(path.parts)
    for pattern in patterns:
        if pattern in parts or path.match(pattern):
            return True
    return False


def should_copy(path: Path, *, base: Path = ROOT, excludes: Iterable[str] = DEFAULT_EXCLUDES) -> bool:
    relative = path.relative_to(base)
    return not _matches_exclude(relative, excludes)


def is_text_file(path: Path) -> bool:
    if path.name in {".env.example", ".gitignore", ".dockerignore", "Dockerfile", "Makefile"}:
        return True
    return path.suffix in TEXT_SUFFIXES


def replacements(names: ProjectNames) -> dict[str, str]:
    return {
        "fastapi-template": names.slug,
        "Rapid Development Template": names.display_name,
        "FastAPI AI Template": names.display_name,
        (
            "A personal rapid-development template, starting with a production-minded FastAPI\n"
            "backend and designed to grow into a multi-project workspace when needed."
        ): f"{names.display_name} generated from the rapid development template.",
        "A compact FastAPI backend template optimized for AI-assisted development.": (
            f"{names.display_name} generated from the rapid development template."
        ),
    }


def rewrite_text(path: Path, names: ProjectNames) -> None:
    if not is_text_file(path):
        return

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return

    updated = content
    for old, new in replacements(names).items():
        updated = updated.replace(old, new)

    if updated != content:
        path.write_text(updated, encoding="utf-8")


def _copy_tree(source: Path, destination: Path, names: ProjectNames, *, base: Path) -> None:
    if source.is_file():
        if should_copy(source, base=base):
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            rewrite_text(destination, names)
        return

    for item in source.rglob("*"):
        if not should_copy(item, base=base):
            continue

        relative = item.relative_to(source)
        output = destination / relative

        if item.is_dir():
            output.mkdir(parents=True, exist_ok=True)
            continue

        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, output)
        rewrite_text(output, names)


def copy_template(
    target: Path,
    names: ProjectNames,
    *,
    manifest: Optional[TemplateManifest] = None,
    force: bool = False,
) -> None:
    manifest = manifest or load_template_manifest("fastapi-api")

    if target.exists():
        if not force:
            raise FileExistsError(f"Target already exists: {target}")
        if not target.is_dir():
            raise NotADirectoryError(f"Target exists and is not a directory: {target}")
    else:
        target.mkdir(parents=True)

    for path_name in WORKSPACE_SUPPORT_PATHS:
        source = ROOT / path_name
        if not source.exists():
            continue
        _copy_tree(source, target / path_name, names, base=ROOT)

    _copy_tree(manifest.source, target / manifest.default_target, names, base=manifest.source)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Create a project from this template.")
    parser.add_argument("name", help="New project name, for example my-saas-api.")
    parser.add_argument("target", type=Path, help="Directory to create or populate.")
    parser.add_argument(
        "--template",
        default="fastapi-api",
        choices=list_template_ids() or ["fastapi-api"],
        help="Template id to generate.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow copying into an existing directory.",
    )
    args = parser.parse_args(argv)

    names = build_project_names(args.name)
    manifest = load_template_manifest(args.template)
    target = args.target.expanduser().resolve()
    copy_template(target, names, manifest=manifest, force=args.force)

    print(f"Created {names.display_name} from {manifest.id} at {target}")
    print("Next steps:")
    print(f"  cd {target}")
    for step in manifest.post_create_steps:
        print(f"  {step}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
