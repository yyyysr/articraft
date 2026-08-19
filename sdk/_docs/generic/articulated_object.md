# Articulated Objects

## Purpose

`ArticulatedObject` owns parts, visuals, materials, and articulations. This page
documents the generic assembly contract without prescribing a product topology.

Part structure, joint frames, geometry, and collision are often coupled. Read
the selected geometry reference with this page when the moving shape must be
designed around its articulation. Add
`docs/sdk/references/physics-parameters.md` to the same working set only when
the current edit also authors passive behavior or mass.

## Construction

```python
ArticulatedObject(
    name: str,
    parts: list[Part] = [],
    articulations: list[Articulation] = [],
    materials: list[Material] = [],
    meta: dict[str, object] = {},
    assets=None,
)
```

Normal authoring starts with an empty object and uses the helper methods below.
Mesh-backed visuals should come from managed helpers rather than manually
constructed output paths.

## Parts

```python
model.part(
    name: str,
    *,
    visuals: Iterable[Visual] | None = None,
    collision_enabled: bool = True,
    inertial: Inertial | None = None,
    physics_material: PhysicsMaterial | None = None,
    meta: dict[str, object] | None = None,
) -> Part
```

- Part names must be unique.
- A part is a rigid body. Geometry that must move independently belongs on a
  separate part.
- `collision_enabled=True` derives collision from visuals. Set it to `False`
  only when the entire part is visual-only.
- Attach geometry with `part.visual(...)`; material binding is per visual.

## Articulations

```python
model.articulation(
    name: str,
    articulation_type: ArticulationType | str,
    parent: str | Part,
    child: str | Part,
    *,
    origin: Origin | None = None,
    axis: tuple[float, float, float] | None = None,
    motion_limits: MotionLimits | None = None,
    motion_properties: MotionProperties | None = None,
    mimic: Mimic | None = None,
    meta: dict[str, object] | None = None,
) -> Articulation
```

- `origin` places the articulation frame relative to the parent part frame.
- At joint position zero, the child part frame coincides with the articulation
  frame.
- `axis` is expressed in the articulation frame, not world space. It defaults
  to local `+Z`.
- Positive angular motion follows the right-hand rule. Positive prismatic
  motion translates the child along `+axis`.
- Choose the axis sign so increasing position has the intended semantic motion.
  Do not compensate for a reversed axis by swapping lower and upper limits.
- A movable child has exactly one incoming articulation in the exported tree.

Use `FIXED` for rigid relationships, `REVOLUTE` for bounded rotation,
`CONTINUOUS` for unbounded rotation, and `PRISMATIC` for bounded translation.
`FLOATING` represents an unconstrained six-degree-of-freedom relationship and
should be used only when that behavior is intentional and supported downstream.

For a deliberately free movable joint, set explicit zero damping and friction.
Add nonzero passive dynamics only when the mechanism semantics justify them.
Read `docs/sdk/references/physics-parameters.md` for mass, contact, damping,
friction, preload, and export behavior.

## Joint Frames And Geometry

Author child visuals in the child part frame. If a pivot or slide origin matters,
either construct the child geometry in that frame or attach it with a visual
`Origin` that makes the relationship explicit.

For prismatic or telescoping mechanisms, preserve hidden retained insertion at
maximum travel. The visible member length, joint travel, and attachment geometry
must remain mechanically consistent across tested poses.

Use `Mimic` for a simple linear follower relationship only. It does not model a
nonlinear linkage or a closed kinematic loop.

## Materials

```python
model.material(material: Material) -> Material
```

Registered material names may be used by visuals. Use unique names and bind
materials to the visual regions they describe. Read
`docs/sdk/references/material-catalogs.md` for optional catalog materials.

## Lookup And Validation

```python
model.get_part(name: str) -> Part
model.get_articulation(name: str) -> Articulation
model.root_parts() -> list[Part]
model.validate(strict: bool = True) -> None
```

Validation checks names, references, joint requirements, tree structure,
geometry descriptors, physical values, and other authoring invariants. A normal
exportable object has exactly one root part. Do not silence failures by adding
arbitrary fixed joints or disconnected support geometry.

## Modeling Boundaries

- A visual describes appearance; generated collision describes contact; an
  inertial describes mass distribution. Do not assume one substitutes for all
  three purposes.
- Avoid disconnected visual islands within one rigid part unless the real
  construction supports them. Add a real connecting feature or use a separate
  part when appropriate.
- Visible openings and hollow regions require actual geometry; a dark material
  on a capped solid is not an opening.
- Use placement helpers for semantic mounting and local surface alignment when
  raw offsets would obscure the intended relationship.

Read `docs/sdk/references/testing.md` for pose-aware structural and clearance
assertions.

Stop reading when the affected rigid-part boundaries, parent-child relations,
joint frames, axes, and limits are clear enough to implement the current
mechanism pass.
