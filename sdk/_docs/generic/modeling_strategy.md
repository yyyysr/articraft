# Modeling Strategy

Use this page for a new object or a major redesign. Its purpose is to coordinate
geometry, rigid-part structure, articulation, and collision before the first
coherent edit; it is not a complete API reference.

## Form The Current Modeling Pass

Choose a pass that produces one mechanically and visually coherent result. A
pass may combine several coupled concerns:

- static form: geometry, placement, and visible material regions;
- articulated form: geometry, part boundaries, joint frames, clearances, and
  collision-bearing regions;
- behavior-sensitive mechanism: articulation, collision, mass distribution,
  and passive dynamics.

Do not split coupled decisions merely to minimize the number of pages read. Do
not include a capability that will not affect the next edit.

## Co-design Parts And Motion

Decide which visible features belong to one rigid body and which must move as
separate parts. For each moving part, settle its parent, local part frame,
articulation origin, axis direction, useful range, and the geometry needed to
remain attached and clear throughout that range.

Read `docs/sdk/references/articulated-object.md` together with the selected
geometry reference when these choices affect one another. Include
`docs/sdk/references/physics-parameters.md` in the same working set only when
the current pass also authors mass, contact behavior, damping, friction, or a
gravity-sensitive preload.

## Choose A Primary Geometry Representation

- Use native primitives from `docs/sdk/references/core-types.md` when the final
  visible shape is exactly a box, cylinder, or sphere.
- Use `docs/sdk/references/cadquery/overview.md` for feature-based solids that
  need shells, wall thickness, fillets, chamfers, holes, grooves, or stable
  solid booleans.
- Use `docs/sdk/references/geometry/mesh-geometry.md` for procedural profiles,
  sweeps, mesh booleans, or custom topology.
- Use `docs/sdk/references/geometry/section-lofts.md` when ordered
  cross-sections define the continuous form.

These paths can be compared at this level, but avoid reading detailed
references for multiple alternatives. After choosing CadQuery, consult
`docs/sdk/references/cadquery/api-ref.md` only for a specific unresolved API
signature.

## Preserve Construction Logic

Plan visible openings as actual openings, hollow bodies with real wall and
interior geometry, and separate panels with plausible seams or clearances.
Use native primitives for genuinely primitive subparts; do not tessellate them
only to match the representation used by a neighboring detailed part.

Default collision follows authored visuals. Consider collision explicitly when
a visual-only detail should not collide, a moving part needs clearance, or the
visual representation is not an appropriate collision shape.

## Stop Reading And Edit

Begin editing once the current pass has resolved:

- the rigid parts it creates or changes;
- the coupled articulations and important local frames;
- the primary geometry representation for each affected part;
- the visible openings, cavities, seams, and clearances that matter now;
- the boundary of the next coherent patch.

Return to capability routing when a later pass introduces materials, physical
parameters, tests, diagnostics, or a different geometry problem.
