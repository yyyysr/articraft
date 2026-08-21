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

## Sketch Asset Coverage

Before choosing geometry APIs, form a short asset plan from the prompt and the
recognizable construction of the object. This is planning guidance, not a
required checklist or a compiler contract. Its purpose is to avoid spending a
complete pass on the outer shell while omitting internal or functional
structures that make the asset credible.

Group candidate features by value:

- **Core structure**: the body, enclosure, cavity, support, and primary moving
  parts without which the object is structurally or visually incomplete.
- **Important function**: racks, shelves, rails, mechanisms, work surfaces, or
  other features that strongly communicate how the object is used.
- **Optional detail**: small trim, fasteners, secondary organizers, labels, and
  close-up details that can be omitted when they do not affect the requested
  view, interaction, or recognition.

Also distinguish exterior, interior, interactive, and moving features. If an
opening door, drawer, lid, or removable panel reveals a functional interior,
plan the major visible contents and their support relationships before
detailing the exterior. For example, an appliance with an opening wash cavity
may need its racks, rails, and principal internal mechanism to read as complete;
it does not automatically need every clip, tine, or fastener.

Use the prompt, expected visible poses, asset scale, and remaining complexity
to select a coherent scope. Prefer a smaller set of complete, connected,
recognizable features over many unfinished details. Do not add generic
components merely to satisfy these categories, and do not turn omissions into
hard test failures or extra repair loops.

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

## Compile The Structural Baseline Early

Make the first coherent implementation after asset coverage, representation,
part boundaries, and primary motion are resolved. It should include the body,
visible interior required by openings, important functional structures,
supports, primary articulations, and working clearances. Compile this baseline
before searching finishes or tuning ordinary physical values.

Keep material regions separable in the geometry, but defer catalog selection,
ordinary `PhysicsMaterial`, final assembled masses, and non-critical passive
dynamics until blocking geometry, connection, articulation, and collision
defects are repaired. Gravity-sensitive joints, stability-critical bases, and
mechanisms whose layout depends on load or preload are exceptions: plan the
behavior early, while still deferring unsupported numerical tuning.

After the structural compile succeeds, read material and physics references
together, complete those attributes in one focused patch, and run the final
compile. A structural compile warning about deferred appearance or physics is a
reminder for that enrichment pass, not a reason to abandon a named blocking
geometry repair.

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

## Finish Exposed Surfaces

Treat edge treatment as a required modeling pass for manufactured or
upholstered objects, not as optional decoration. After the primary volume is
chosen, identify the silhouette edges, touch surfaces, and assembly transitions
that a viewer can inspect.

| Visible intent | Preferred representation |
| --- | --- |
| Exact sharp internal support | Native primitive |
| Appliance shell or rounded panel | CadQuery fillet/chamfer or `rounded_rect_profile` |
| Upholstered seat or padded cap | Dome/capsule, rounded profile, or lofted sections |
| Tapered pedestal or formed base | Cone/lathe/section loft, then edge treatment |
| Tubular rail or footrest | Sweep or `TorusGeometry`, not a flat box ring |

Use a small radius that matches the part scale; do not round every edge
indiscriminately. Large exposed boxes, cylinders, or flat extrusions should be
treated as unfinished when the real object has a soft, rolled, bent, or
manufactured transition. Keep hidden mounting faces simple when they do not
affect the silhouette or contact behavior.

For a new asset, finish one representative exterior part before duplicating its
construction across doors, drawers, cushions, or panels. Confirm that the
rounded geometry still has valid openings, wall thickness, clearances, and
collision before adding decorative details.

## Close The Part Attributes

After the structural baseline compiles, review every
collision-bearing part as one attribute bundle:

- bind visual materials to its major visible regions; search the installed
  material catalog first when a plausible catalog finish may exist, and use an
  inline material only when no suitable match is returned;
- assign an explicit `PhysicsMaterial` when the bulk/contact class is known;
- choose a mass strategy: collision-derived mass only for a reasonably uniform
  solid, or explicit assembled-part mass for hollow, thin-wall, or composite
  construction;
- for each movable articulation, make an explicit passive-dynamics decision,
  including zero damping/friction when intentionally free.

Visual material, contact material, and mass strategy are separate decisions.
Do not infer density or friction from a catalog appearance, and do not treat a
colored visual as completed physics authoring. Read
`docs/sdk/references/material-catalogs.md` for catalog binding and
`docs/sdk/references/physics-parameters.md` for physical values.

## Stop Reading And Edit

Begin editing once the current pass has resolved:

- the selected core, important, and optional asset coverage for this pass;
- the visible interior required by openings or decisive articulated poses;
- the rigid parts it creates or changes;
- the coupled articulations and important local frames;
- the primary geometry representation for each affected part;
- the visible openings, cavities, seams, and clearances that matter now;
- the visual-material, contact-material, mass, and movable-joint decisions for
  the affected parts;
- the boundary of the next coherent patch.

Return to capability routing when a later pass introduces materials, physical
parameters, tests, diagnostics, or a different geometry problem.
