# SDK Quickstart

## Workspace Contract

You are editing a virtual Articraft authoring workspace.

- `model.py` is the only writable file.
- Everything under `docs/` is read-only guidance.
- Import public authoring APIs from `sdk`; documentation paths are not Python
  module paths.
- Distances are meters and rotations are radians.
- Do not write USD or URDF directly. The compiler owns validation,
  materialization, collision compilation, and export.

Every generated script defines:

```python
def build_object_model() -> ArticulatedObject: ...
def run_tests() -> TestReport: ...

object_model = build_object_model()
```

Use logical names with managed mesh helpers such as
`mesh_from_geometry(..., "part_name")`, `mesh_from_cadquery(...)`, and
`mesh_from_input(...)`. Read the referenced API page before using an unfamiliar
helper or parameter; do not guess signatures from memory.

## Read Only What You Need

After understanding the request and inspecting the existing `model.py`, read:

```text
docs/sdk/references/capability-index.md
```

The index routes geometry, structure, appearance, collision, physics, and
validation work to focused references. Load only the references needed for the
current change. Do not preload mesh, CadQuery, physics, probe, or testing pages
for possible future use.

When authoring fails, read `docs/sdk/references/errors.md`. Use
`docs/sdk/references/probe-tooling.md` only when inspecting model state, and
`docs/sdk/references/testing.md` only when adding or correcting assertions.
