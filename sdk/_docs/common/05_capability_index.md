# SDK Capability Index

Use this page to choose the smallest relevant reference set. It is a routing
index, not a modeling tutorial. Read exact API pages only when that capability
is needed.

## Geometry Modeling

For primitive geometry, mesh descriptors, transforms, and visual attachment,
read `docs/sdk/references/core-types.md`.

For procedural meshes, profiles, sweeps, extrusions, openings, and mesh
booleans, read `docs/sdk/references/geometry/mesh-geometry.md`. For
section-driven surfaces, read `docs/sdk/references/geometry/section-lofts.md`.
For CAD solids, shells, fillets, holes, and solid booleans, read
`docs/sdk/references/cadquery/overview.md`; consult
`docs/sdk/references/cadquery/api-ref.md` only for an exact CadQuery signature.
For managed or imported mesh assets, read `docs/sdk/references/assets.md`. For
mounting and coordinate placement, read `docs/sdk/references/placement.md`.

## Structure And Articulation

For parts, visuals, parent-child structure, joints, axes, motion limits, and
lookup helpers, read `docs/sdk/references/articulated-object.md`.

## Appearance And Materials

For basic colors, textures, visual material binding, and material types, read
`docs/sdk/references/core-types.md`. For searchable material catalogs and
renderer fallback behavior, read `docs/sdk/references/material-catalogs.md`.

## Collision

For automatic primitive and mesh collision generation, visual-only parts, and
articulation collision behavior, read
`docs/sdk/references/articulated-object.md`. For collision assertions and model
quality checks, read `docs/sdk/references/testing.md`.

## Physical Properties

For density, friction, restitution, mass, inertia, passive joint dynamics, and
gravity-sensitive joints, read `docs/sdk/references/physics-parameters.md`.

## Workflow, Validation, And Debugging

For compile or authoring failures, read `docs/sdk/references/errors.md`. For
model-state inspection, read `docs/sdk/references/probe-tooling.md`. For
`TestContext`, assertions, pose checks, and QC allowances, read
`docs/sdk/references/testing.md`.
