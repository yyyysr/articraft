# Core Types

## Purpose

This page documents the generic data types shared by geometry, appearance,
physics, and articulation authoring. Import public APIs from `sdk`.

Use this reference with `docs/sdk/references/articulated-object.md` when
rigid-part frames and geometry are being designed together. For a non-primitive
primary shape, choose the CadQuery, procedural mesh, or section-loft path in
`docs/sdk/references/modeling-strategy.md` rather than preloading every geometry
reference.

## Units And Transforms

- Distances are meters.
- Angles are radians.
- Revolute and continuous joint positions are radians; prismatic positions are
  meters along the configured axis.
- URDF cylinders extend along local `+Z`.

```python
Origin(
    xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rpy: tuple[float, float, float] = (0.0, 0.0, 0.0),
)
```

`rpy` is `(roll, pitch, yaw)` with URDF-compatible composition
`R = Rz(yaw) * Ry(pitch) * Rx(roll)`. Put local transforms on the containing
visual or collision rather than baking them into a primitive descriptor.

## Geometry Descriptors

```python
Box(size: tuple[float, float, float])
Cylinder(radius: float, length: float)
Sphere(radius: float)
Mesh(
    filename: str | os.PathLike[str] | None = None,
    name: str | None = None,
    scale: tuple[float, float, float] | None = None,
    source_geometry: Box | Cylinder | Sphere | None = None,
    source_transform: Mat4 | None = None,
)
```

- `Box.size` contains full extents.
- `Cylinder.length` is the full local-Z length. `height` remains a compatibility
  alias, but new code should use `length`.
- A mesh requires a non-empty `filename` or logical `name`. Normal authoring
  should obtain managed meshes from `mesh_from_geometry`,
  `mesh_from_cadquery`, or `mesh_from_input` rather than constructing one.
- `source_geometry` and `source_transform` preserve optional primitive
  provenance. Do not author them unless the mesh was actually derived from that
  primitive.

Use `Box`, `Cylinder`, or `Sphere` when the visible object is exactly that
shape. Use a mesh or CAD solid when the geometry requires holes, shells,
fillets, variable sections, or other features a primitive cannot represent.

## Materials And Visuals

```python
Material(
    name: str,
    rgba: tuple[float, float, float, float] | None = None,
    texture: str | None = None,
    *,
    color: tuple[float, ...] | None = None,
    catalog: str | None = None,
    catalog_material: str | None = None,
    parameters: Mapping[str, object] | None = None,
)

Visual(
    geometry: Box | Cylinder | Sphere | Mesh,
    origin: Origin = Origin(),
    material: Material | str | None = None,
    name: str | None = None,
)
```

- `color` is a compatibility alias for `rgba`; do not pass both.
- Catalog materials require both `catalog` and `catalog_material`. Use exact
  identifiers returned by `find_materials`; do not invent identifiers or
  parameter keys.
- Material assignment is per visual. Split geometry into separate visuals when
  regions require different materials.
- Name visuals that tests or probes need to identify.

Read `docs/sdk/references/material-catalogs.md` only when catalog materials or
their renderer fallbacks are relevant.

## Collision Generation

Parts derive collision geometry from visuals by default. Primitive visuals
produce primitive collisions; mesh visuals produce mesh collisions. USD marks
mesh collision with the standard `convexDecomposition` approximation.

Set `collision_enabled=False` on a part whose geometry is visual-only. This
removes its generated USD and URDF collision geometry but keeps visuals and any
explicit inertial.

## Mass And Contact Types

```python
Inertia(ixx, ixy, ixz, iyy, iyz, izz)
Inertial(mass: float, inertia: Inertia, origin: Origin = Origin())
Inertial.from_geometry(
    geometry: Box | Cylinder | Sphere | Mesh,
    mass: float,
    *,
    origin: Origin | None = None,
) -> Inertial

PhysicsMaterial(
    name: str,
    density: float,
    static_friction: float,
    dynamic_friction: float,
    restitution: float,
)
```

Use `Inertial.from_geometry` when a geometry is a reasonable proxy and its mass
is known. Complex hollow or composite parts usually need a plausible assembled
mass rather than a solid bounding-volume estimate. Read
`docs/sdk/references/physics-parameters.md` before choosing physical values.

## Motion Types

```python
MotionLimits(
    effort: float = 1.0,
    velocity: float = 1.0,
    lower: float | None = None,
    upper: float | None = None,
)

MotionProperties(
    damping: float | None = None,
    friction: float | None = None,
    stiffness: float | None = None,
    equilibrium: float | None = None,
)

Mimic(
    articulation: str,
    multiplier: float = 1.0,
    offset: float = 0.0,
)
```

`MotionLimits.effort` is the actuator/drive force limit, not a friction model.
Use `Mimic` only for linear scalar coupling:
`q_follower = multiplier * q_source + offset`.

`ArticulationType` values are `FIXED`, `REVOLUTE`, `CONTINUOUS`, `PRISMATIC`,
and `FLOATING`. Revolute and prismatic joints require meaningful axes and
limits; continuous joints have no lower/upper position bounds.

## Resolved Objects

`Part` exposes `name`, `visuals`, `collisions`, `collision_enabled`, `inertial`,
`physics_material`, and `meta`. Add a visual with:

```python
part.visual(
    geometry,
    origin: Origin | None = None,
    material: Material | str | None = None,
    *,
    name: str | None = None,
) -> Visual
```

Retrieve a named visual with `part.get_visual(name)`.

`Articulation` exposes `name`, `articulation_type`, `parent`, `child`, `origin`,
`axis`, `motion_limits`, `motion_properties`, `mimic`, and `meta`.

## Geometry Resizing

```python
scale_geometry_to_size(
    geometry,
    size: tuple[float, float, float],
    *,
    filename: str | Path | None = None,
)
```

Resizing keeps a primitive only when the result is still representable by that
primitive. Nonuniformly scaling a sphere or scaling a cylinder differently in
its two radial axes requires a mesh output and therefore `filename`.

Stop reading when the descriptors and signatures required by the current edit
are resolved. Material catalogs, physical estimates, and test assertions belong
to their own working sets unless they affect this same edit.
