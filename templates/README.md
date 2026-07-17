# Templates

Templates describe project shapes that can be generated from this repository.
The first maintained template is `fastapi-api`, which points at the working API
source under `apps/api`.

## Manifest Fields

Each template lives under `templates/<id>/template.json` and defines:

- `id`: stable template identifier used by the generator.
- `name`: human-readable template name.
- `description`: short summary shown in docs and future CLI output.
- `source`: path to the maintained source directory, relative to the manifest.
- `default_target`: suggested target directory name pattern.
- `required_tools`: local tools required after generation.
- `generated_paths`: paths expected to exist in generated projects.
- `post_create_steps`: setup steps printed after generation.
- `verification`: commands used to verify generated projects.

Template manifests should point to maintained sources whenever practical. Avoid
copying large duplicate template trees unless the source needs to diverge.
