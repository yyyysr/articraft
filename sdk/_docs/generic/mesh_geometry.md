# Procedural Mesh Geometry

## Purpose

Use this reference for low-level procedural meshes: tessellated builders,
profiles, extrusions, sweeps, openings, booleans, transforms, and managed mesh
export. Use native `Box`, `Cylinder`, or `Sphere` instead when the visible shape
is exactly representable by a primitive.

## Core Mesh Type

```python
MeshGeometry(
    vertices: list[tuple[float, float, float]] = [],
    faces: list[tuple[int, int, int]] = [],
)
```

```python
geom.add_vertex(x, y, z) -> int
geom.add_face(a, b, c) -> None
geom.copy() -> MeshGeometry
geom.clone() -> MeshGeometry
geom.merge(other) -> MeshGeometry
geom.translate(dx, dy, dz) -> MeshGeometry
geom.scale(sx, sy=None, sz=None) -> MeshGeometry
geom.rotate(axis, angle, origin=(0.0, 0.0, 0.0)) -> MeshGeometry
geom.rotate_x(angle) -> MeshGeometry
geom.rotate_y(angle) -> MeshGeometry
geom.rotate_z(angle) -> MeshGeometry
```

Vertices are meters and faces contain zero-based triangle indices. Transforms
and `merge` mutate the object and return `self`; copy before reusing a source in
multiple variants.

## Tessellated Builders

```python
BoxGeometry(size)
CylinderGeometry(radius, height, *, radial_segments=24, closed=True)
ConeGeometry(radius, height, *, radial_segments=24, closed=True)
SphereGeometry(radius, *, width_segments=24, height_segments=16)
DomeGeometry(radius, *, radial_segments=24, height_segments=12, closed=True)
CapsuleGeometry(radius, length, *, radial_segments=24, height_segments=8)
TorusGeometry(radius, tube, *, radial_segments=16, tubular_segments=32)
```

These classes immediately create tessellated meshes. They are not equivalent
to native SDK primitives even when their shape is geometrically similar.
Cylinders, cones, and capsules extend along local Z.

## Revolve, Loft, Extrude, And Sweep

```python
LatheGeometry(profile, *, segments=32, closed=True)
LatheGeometry.from_shell_profiles(
    outer_profile,
    inner_profile,
    *,
    segments=32,
    start_cap="flat",
    end_cap="flat",
    lip_samples=6,
)

LoftGeometry(profiles, *, cap=True, closed=True)

ExtrudeGeometry(profile, height, *, cap=True, center=True, closed=True)
ExtrudeGeometry.centered(profile, height, *, cap=True, closed=True)
ExtrudeGeometry.from_z0(profile, height, *, cap=True, closed=True)

ExtrudeWithHolesGeometry(
    outer_profile,
    hole_profiles,
    height,
    *,
    cap=True,
    center=True,
    closed=True,
)

SweepGeometry(profile, path, *, cap=False, closed=True)
```

- Lathe profiles contain `(radius, z)` points with nonnegative radii.
- `LoftGeometry` is a low-level helper whose profile loops must have matching
  point counts. Prefer `section_loft(...)` for new section-driven surfaces.
- Extrude profiles are closed XY loops and extend along Z.
- `ExtrudeWithHolesGeometry` creates actual through-cut loops inside an outer
  profile.
- Basic `SweepGeometry` follows path points but does not replace a CAD kernel
  for complex solid features.

## Profiles And Curves

```python
rounded_rect_profile(width, height, radius, *, corner_segments=6)
superellipse_profile(width, height, exponent=2.6, *, segments=48)
sample_catmull_rom_spline_2d(
    points, *, samples_per_segment=12, closed=False, alpha=0.5
)
sample_cubic_bezier_spline_2d(
    control_points, *, samples_per_segment=12
)
```

Profiles return centered counter-clockwise XY loops. Sampling is explicit;
choose resolution from visible curvature and required output cost rather than
raising it uniformly.

Side-loft helpers use sections of `(y, z_min, z_max, width)` and loft along Y:

```python
superellipse_side_loft(
    sections, *, exponents=2.8, segments=56, cap=True, closed=True,
    min_height=0.0001, min_width=0.0001,
) -> MeshGeometry

split_superellipse_side_loft(
    sections, *, split_y, exponents=2.8, segments=56, cap=True, closed=True,
    min_height=0.0001, min_width=0.0001,
) -> tuple[MeshGeometry, MeshGeometry, tuple[float, float, float, float]]

resample_side_sections(
    sections, *, samples_per_span=2, smooth_passes=0,
    min_height=0.0001, min_width=0.0001,
) -> list[tuple[float, float, float, float]]
```

## Openings And Booleans

```python
cut_opening_on_face(
    shell_geometry: MeshGeometry,
    *,
    face: str,
    opening_profile,
    depth: float,
    offset=(0.0, 0.0),
    taper: float = 0.0,
) -> MeshGeometry

boolean_union(a: MeshGeometry, b: MeshGeometry) -> MeshGeometry
boolean_difference(a: MeshGeometry, b: MeshGeometry) -> MeshGeometry
boolean_intersection(a: MeshGeometry, b: MeshGeometry) -> MeshGeometry
```

`cut_opening_on_face` adds an opening throat to an existing shell; it does not
subtract a cap from a closed solid. Boolean inputs must be valid closed manifold
solids. Prefer CadQuery for feature-heavy solids, fillets, shells, repeated
cuts, or operations where stable face/edge selection matters.

## Managed Export

```python
mesh_from_geometry(geometry: MeshGeometry, name: str) -> Mesh
save_mesh_geometry(geometry: MeshGeometry, path: str | Path) -> Path
```

`mesh_from_geometry` is the normal authoring path. Pass a stable logical name,
not a filesystem path; the active asset session owns the materialized OBJ.
`save_mesh_geometry` writes an explicit path for external tools and does not
register a managed SDK mesh.

Angles use radians and the right-hand rule unless a parameter explicitly names
degrees. Verify that intended solids are closed and that openings are actual
topology rather than dark surfaces or overlapping fragments.
