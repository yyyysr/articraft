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

## Build A Working Set

After understanding the request and inspecting the existing `model.py`, read:

```text
docs/sdk/references/capability-index.md
```

Use the index to assemble the documentation working set for the next coherent
code change. A working set may include several strongly coupled capabilities;
geometry, articulation, and collision often need to be planned together.

Compare alternative approaches at the overview level, then read detailed API
references only for the approach you intend to implement. Do not load a page
only because it may become useful later. Once the working set resolves the
decisions needed for the next change, stop reading and edit `model.py`.
