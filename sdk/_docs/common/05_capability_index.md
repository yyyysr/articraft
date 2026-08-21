# SDK Capability Index

This index helps form a task-scoped documentation working set. It is not a
checklist of pages to read before editing.

## Relationship Types

- **Coupled**: capabilities whose decisions affect one another and may be read
  and planned together.
- **Alternative**: competing implementation paths. Compare their summaries,
  choose a path, and avoid loading detailed references for every alternative.
- **Detail**: exact signatures or advanced controls needed only after choosing
  an implementation path.
- **Diagnostic**: references used after a compile, geometry, or test failure
  provides a concrete question.

For a new object or a major structural redesign, start with
`docs/sdk/references/modeling-strategy.md`. Its asset-coverage guidance helps
select core structure, important functional features, visible interior, and
optional detail before geometry implementation begins. It is planning advice,
not a mandatory component list or validation rule. For a targeted change to an
existing model, go directly to the relevant capability below and include
coupled pages when they affect the same code change.

## Geometry Modeling

Geometry is commonly coupled with part boundaries, articulation frames,
collision, placement, and visible materials.

- Exact `Box`, `Cylinder`, or `Sphere` visuals and shared descriptors:
  `docs/sdk/references/core-types.md`.
- Feature-based solids, shells, fillets, holes, grooves, and solid booleans:
  `docs/sdk/references/cadquery/overview.md`.
- Procedural profiles, sweeps, extrusions, mesh openings, and mesh booleans:
  `docs/sdk/references/geometry/mesh-geometry.md`.
- Section-driven continuous forms:
  `docs/sdk/references/geometry/section-lofts.md`.

For visible rounded or manufactured forms, use the selected overview together
with its edge-treatment guidance:

- rounded appliance shell, softened door, or radiused panel:
  `docs/sdk/references/geometry/mesh-geometry.md` for rounded profiles and
  `docs/sdk/references/cadquery/overview.md` for fillets/chamfers;
- upholstered seat, cushion, or dome:
  `docs/sdk/references/geometry/mesh-geometry.md` for dome/capsule/loft forms;
- tapered pedestal, lathed base, or tubular footrest:
  `docs/sdk/references/geometry/mesh-geometry.md` for lathe/torus/sweep forms;
- exact CadQuery edge selection or a failed fillet/chamfer call:
  `docs/sdk/references/cadquery/api-ref.md` as a detail lookup.

CadQuery, procedural mesh, and section lofts are alternative primary
representations for many parts. Read their overview guidance to choose; do not
load every detailed path. After choosing CadQuery, read
`docs/sdk/references/cadquery/helpers.md` when the current change
needs managed mesh export, component splitting, unit conversion, material
region splitting, or coordination between mesh-local and articulation frames.
The CadQuery API reference is a separate detail page for an exact unresolved
CadQuery call: `docs/sdk/references/cadquery/api-ref.md`.

After choosing procedural mesh, use
`docs/sdk/references/geometry/mesh-api.md` only when the overview does not
resolve a helper signature, profile/spline operation, shell helper, opening,
or export detail. Use `read_file(section="Profile and Shell Helpers")` or the
corresponding detail heading when only one topic is needed. After choosing section lofting, use
`docs/sdk/references/geometry/section-lofts-api.md` only for the complete loft
specification, repair behavior, or a concrete advanced control. These are
Detail pages for the selected path, not additional geometry alternatives.

For managed/imported mesh ownership read `docs/sdk/references/assets.md`. For
semantic mounting and coordinate placement read
`docs/sdk/references/placement.md`.

## Structure And Articulation

Part decomposition and joint design are strongly coupled with geometry and
collision. Read `docs/sdk/references/articulated-object.md` when the next change
creates or modifies rigid parts, parent-child structure, joint frames, axes,
limits, or motion properties.

Include the selected geometry reference in the same working set when a moving
part's local frame, retained insertion, clearance, or shape must be designed
around its joint.

For a common door, drawer, fixed attachment, or swivel assembly, start with
`docs/sdk/references/components/assembly-patterns.md`. It contains minimal
copyable templates for visual binding, enum-safe articulation calls, bounded
revolute/prismatic joints, and continuous swivels. For exposed hinge leaves,
knuckles, or pin detail, add
`docs/sdk/references/components/hinges.md` as a focused component reference.

## Appearance And Materials

Basic visual material binding is documented in
`docs/sdk/references/core-types.md`. Read
`docs/sdk/references/material-catalogs.md` only when the current change selects
catalog materials, textures, or renderer fallbacks. Appearance can be planned
with geometry when material regions affect how visuals are split.

For a new asset, search installed catalog materials before settling for inline
colors when named finishes such as wood, metal, stone, fabric, glass, or coated
appliance surfaces may be represented. Catalog appearance does not determine
physical density or contact behavior.

Unless material regions change the geometry split, defer catalog search until
the structural baseline has compiled without blocking geometry, articulation,
connection, or collision defects. Then resolve appearance and physics together
as a focused enrichment pass.

## Collision

Primitive and mesh visuals generate collision by default. Read
`docs/sdk/references/articulated-object.md` when changing collision-bearing part
boundaries or making a part visual-only. Read
`docs/sdk/references/testing.md` when the current change checks contact,
clearance, overlap, or containment.

Collision is usually coupled with geometry and articulation; it does not
normally require a separate initial reading pass when the default generated
collision is sufficient.

## Physical Properties

Read `docs/sdk/references/physics-parameters.md` when the next change authors or
reviews density, friction, restitution, mass, inertia, passive joint dynamics,
or gravity-sensitive behavior. Physics may be planned with articulation when
joint behavior changes the geometry or mechanism, but it need not block an
earlier structural pass that does not yet assign physical values.

## Validation And Diagnostics

- Authoring or compile failure: `docs/sdk/references/errors.md`.
- Ambiguous model state or spatial relationship:
  `docs/sdk/references/probe-tooling.md`.
- Assertions, decisive poses, collision checks, and QC allowances:
  `docs/sdk/references/testing.md`.

These are diagnostic references unless validation is part of the next code
change. Do not preload them merely because every finished model eventually
needs tests.

## Stop Condition

The working set is sufficient when it resolves the coupled decisions needed by
the next coherent edit. At that point, edit `model.py`. Return to this index
only when the task enters a new capability area or evidence from compilation
changes the plan.
