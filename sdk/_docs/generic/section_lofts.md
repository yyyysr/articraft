# Section Lofts

## Purpose

Use `section_loft(...)` when a surface or solid can be described by a small
ordered set of cross-sections, optionally following a path. Use a primitive for
an exact primitive shape and CadQuery when the result needs downstream solid
features such as shells, fillets, or cuts.

Section lofting is a selected geometry path, not a prerequisite for all curved
models. Read this page with the part/articulation reference only when section
placement and moving-part frames are coupled in the current edit.

This page is the overview and minimum authoring contract. Read
`docs/sdk/references/geometry/section-lofts-api.md` only when the current patch
needs the complete `SectionLoftSpec`, exact repair behavior, or a concrete
advanced control that is not resolved here. Use `read_file(section="Repair")`
or another matching detail heading when only one topic is needed.

## Entry Point

```python
section_loft(
    spec: SectionLoftSpec | Sequence[LoftSection | Sequence[Sequence[float]]],
    **overrides,
) -> MeshGeometry
```

At least two ordered closed section loops are required.

```python
LoftTessellation(
    tolerance: float = 0.001,
    angular_tolerance: float = 0.1,
)

LoftSection(points: tuple[tuple[float, float, float], ...])

SectionLoftSpec(
    sections: tuple[LoftSection, ...],
    path: tuple[tuple[float, float, float], ...] | None = None,
    cap: bool = True,
    solid: bool = True,
    symmetry: str | None = None,
    ruled: bool = False,
    repair: str = "auto",
    tessellation: LoftTessellation = LoftTessellation(),
    ...,
)
```

Common controls are `sections`, optional `path`, `cap`, `solid`, `symmetry`,
`repair`, and `tessellation`. The supported symmetry value is `mirror_yz`.
Repair modes are `auto`, `mesh`, `kernel`, and `off`.

Advanced guide curves and backend tuning fields are documented in the detail
page. They are conditional controls and are not required for ordinary ordered
section lofts.

## Repair

```python
repair_loft(
    geometry_or_spec: MeshGeometry | SectionLoftSpec | Sequence,
    *,
    repair: str = "auto",
) -> MeshGeometry
```

For a `MeshGeometry`, this performs mesh-side repair. For a spec or raw
sections, it rebuilds with the selected repair mode.

## Authoring Rules

- Keep section ordering and winding consistent.
- Use corresponding perimeter points where possible.
- Add a path only when the form must follow a centerline; ordinary ordered
  sections do not require one.
- Choose tessellation from the output scale and curvature.
- Use repair for broken topology, not as a substitute for coherent sections.
- Inspect closedness and caps when the result is intended to have mass or
  collision as a solid.

Stop reading when section correspondence, path use, tessellation, and repair
choices are sufficient for the current loft. Do not load the detail page or an
alternative geometry path without a remaining implementation question. Use
diagnostic tooling after a concrete topology failure.
