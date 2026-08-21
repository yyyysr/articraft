# Procedural Mesh Geometry

## Purpose

Use this reference for low-level procedural meshes: tessellated builders,
profiles, extrusions, sweeps, openings, booleans, transforms, and managed mesh
export. Use native `Box`, `Cylinder`, or `Sphere` instead when the visible shape
is exactly representable by a primitive.

Procedural mesh is commonly an alternative to CadQuery or section-driven loft
authoring for a primary part. Use
`docs/sdk/references/modeling-strategy.md` to select the path, then read this
page when procedural mesh is the intended implementation.

This page is the overview and minimum authoring contract. Read
`docs/sdk/references/geometry/mesh-api.md` only when the current patch needs a
helper signature or behavior not resolved here, such as advanced profile and
spline helpers, side-shell construction, face openings, or explicit mesh
export. Use `read_file(section="Profile and Shell Helpers")` when only one detail
topic is needed. Do not load the detail page merely because procedural mesh
was chosen.

## Core Mesh Type

```python
MeshGeometry(vertices=[], faces=[])
geom.add_vertex(x, y, z) -> int
geom.add_face(a, b, c) -> None
geom.copy() -> MeshGeometry
geom.merge(other) -> MeshGeometry
geom.translate(dx, dy, dz) -> MeshGeometry
geom.scale(sx, sy=None, sz=None) -> MeshGeometry
geom.rotate(axis, angle, origin=(0.0, 0.0, 0.0)) -> MeshGeometry
```

Vertices are meters and faces contain zero-based triangle indices. Transforms
and `merge` mutate the object and return `self`; copy or clone before reusing a
source in multiple variants. Axis-specific rotation helpers are also available.

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
LoftGeometry(profiles, *, cap=True, closed=True)
ExtrudeGeometry(profile, height, *, cap=True, center=True, closed=True)
ExtrudeWithHolesGeometry(outer_profile, hole_profiles, height, ...)
SweepGeometry(profile, path, *, cap=False, closed=True)
```

- Lathe profiles contain `(radius, z)` points with nonnegative radii.
- `LoftGeometry` is a low-level helper whose profile loops must have matching
  point counts. Prefer `section_loft(...)` for new section-driven surfaces.
- Extrude profiles are closed XY loops and extend along Z.
- `ExtrudeWithHolesGeometry` creates actual through-cut loops inside an outer
  profile.
- `LatheGeometry.from_shell_profiles(...)` creates an outer/inner revolved
  shell. `ExtrudeGeometry.centered(...)` and `.from_z0(...)` make the intended
  Z span explicit.
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

For appliance-like side shells, `superellipse_side_loft(...)`,
`split_superellipse_side_loft(...)`, and `resample_side_sections(...)` use
sections of `(y, z_min, z_max, width)` and loft along Y. Read the detail
`Profile and Shell Helpers` section for their full controls.

For continuously bent wire, tube, frame, rail, loop, or guard geometry, read
`docs/sdk/references/geometry/wires-and-frames.md`. It is the focused Detail
page for spline tubes, swept non-circular profiles, and readable authored paths;
it does not define articulation or rigid-part structure.

Use these builders for common rounded forms instead of native sharp primitives:

```python
seat_profile = rounded_rect_profile(0.42, 0.42, 0.06, corner_segments=8)
seat = ExtrudeGeometry(seat_profile, 0.10, cap=True, center=True)

soft_base = LatheGeometry(
    [(0.00, 0.00), (0.20, 0.015), (0.23, 0.045), (0.18, 0.075)],
    segments=48,
)

footrest = TorusGeometry(0.17, 0.012, radial_segments=24, tubular_segments=48)
```

`rounded_rect_profile` is suitable for appliance doors and padded square
panels; `superellipse_profile` or side lofts suit softened appliance shells;
`LatheGeometry` suits rotational bases; `DomeGeometry`, `CapsuleGeometry`, or
section lofts suit cushions. Increase sampling only where the silhouette needs
it, and verify that the generated mesh remains closed and collision-suitable.

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

Stop reading when the current mesh operation, topology requirements, and
managed export call are resolved. Use the detail API page only for a remaining
implementation question. Do not continue into CadQuery details unless evidence
shows the chosen mesh path cannot represent the required solid.
