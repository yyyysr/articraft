# Section Lofts

## Purpose

Use `section_loft(...)` when a surface or solid can be described by a small
ordered set of cross-sections, optionally following a path. Use a primitive for
an exact primitive shape and CadQuery when the result needs downstream solid
features such as shells, fillets, or cuts.

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
    guide_curves: Mapping[str, tuple[tuple[float, float, float], ...]] | None = None,
    cap: bool = True,
    solid: bool = True,
    symmetry: str | None = None,
    ruled: bool = False,
    continuity: str = "C2",
    parametrization: str = "uniform",
    degree: int = 3,
    compat: bool = True,
    smoothing: bool = False,
    weights: tuple[float, float, float] = (1.0, 1.0, 1.0),
    repair: str = "auto",
    tessellation: LoftTessellation = LoftTessellation(),
)
```

Common controls are `sections`, optional `path`, `cap`, `solid`, `symmetry`,
`repair`, and `tessellation`. The supported symmetry value is `mirror_yz`.
Repair modes are `auto`, `mesh`, `kernel`, and `off`.

`guide_curves` supports only `spine`, `aux_spine`, and `binormal`. If no
explicit path is supplied, `spine` may become the sweep path. Backend tuning
fields are conditional and are not guaranteed to affect every loft branch.

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
