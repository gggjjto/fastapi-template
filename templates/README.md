# Templates

Templates describe project shapes that can be generated from this repository.
The first maintained template is `fastapi-api`, which points at the working API
source under `apps/api`.

## Manifest Fields

Each template lives under `templates/<id>/template.json` and defines:

- `id`: stable template identifier used by the generator.
- `version`: semver-like template version printed during generation.
- `name`: human-readable template name.
- `description`: short summary shown in docs and future CLI output.
- `source`: path to the maintained source directory, relative to the manifest.
- `default_target`: suggested target directory name pattern.
- `required_tools`: local tools required after generation.
- `generated_paths`: paths expected to exist in generated projects.
- `post_create_steps`: setup steps printed after generation.
- `verification`: commands used to verify generated projects.
- `options`: supported `--with-*` capability flags, including their affected
  files, environment variables, dependencies, and incompatible combinations.

Template manifests should point to maintained sources whenever practical. Avoid
copying large duplicate template trees unless the source needs to diverge.
The same manifest also drives `scripts/doctor.py --template <id>`, so keep
`required_tools` scoped to tools the generated template actually needs.
Track user-facing template changes in [`CHANGELOG.md`](./CHANGELOG.md).

## Template Options

Template-specific option docs live next to the manifest. See
[`fastapi-api/OPTIONS.md`](./fastapi-api/OPTIONS.md) for the currently supported
capability flags.
