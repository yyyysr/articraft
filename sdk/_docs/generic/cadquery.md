# CadQuery Geometry

## Purpose

Use CadQuery to author feature-based solids when primitive descriptors or
procedural meshes are a poor fit: shells, fillets, chamfers, holes, grooves,
repeated cuts, and solid booleans. Keep parts, joints, materials, physics, tests,
and final export in the Articraft SDK.

CadQuery is an alternative primary geometry path to procedural mesh or section
lofting for many parts. Read this page after choosing feature-based solid
modeling; do not preload every alternative's detailed reference.

CadQuery is unitless. Articraft output must be meters. Author directly in meters
with `unit_scale=1.0`, or author in another consistent unit and convert exactly
once during export.

## Managed Helpers

```python
tessellate_cadquery(
    model,
    *,
    tolerance=0.001,
    angular_tolerance=0.1,
    unit_scale=1.0,
) -> tuple[list[Vec3], list[Face]]

cadquery_local_aabb(
    model,
    *,
    tolerance=0.001,
    angular_tolerance=0.1,
    unit_scale=1.0,
) -> tuple[Vec3, Vec3]

mesh_from_cadquery(
    model,
    name: str,
    *,
    assets=None,
    tolerance=0.001,
    angular_tolerance=0.1,
    unit_scale=1.0,
) -> Mesh

mesh_components_from_cadquery(
    model,
    name: str,
    *,
    assets=None,
    tolerance=0.001,
    angular_tolerance=0.1,
    unit_scale=1.0,
) -> list[Mesh]
```

Use stable logical names with managed mesh helpers. Do not pass output paths or
reconstruct filenames from `materialized_path`.

For bounds plus a managed mesh, use:

```python
export_cadquery_mesh(...) -> CadQueryMeshExport
export_cadquery_components(...) -> list[CadQueryMeshExport]
```

`CadQueryMeshExport` contains `mesh`, `local_aabb`, `center_xyz`, and
`size_xyz`. Use `save_cadquery_obj(model, path, ...)` only when an external tool
requires an exact OBJ path.

For the complete Articraft integration contract, read
`docs/sdk/references/cadquery/helpers.md` when the current change
depends on managed export results, component splitting, unit conversion,
material regions, or local-frame behavior. Use `read_file(section="Units")`
or another matching heading when only one integration topic is needed. For full CadQuery call signatures,
read `docs/sdk/references/cadquery/api-ref.md` only when a specific CadQuery
operation remains unresolved.

## Representation Boundaries

- `mesh_from_cadquery` accepts CadQuery `Shape`, `Workplane`, and `Assembly`
  inputs and tessellates them to a managed mesh.
- Solve constrained assemblies before export; the SDK does not call `solve()`.
- Export preserves the authored local frame. It does not recenter geometry or
  infer articulation pivots.
- Keep kinematic joints in `ArticulatedObject`; a CadQuery assembly does not
  become a URDF joint tree automatically.
- SDK materials bind per exported visual. CadQuery face colors, per-face
  materials, UVs, and texture coordinates are not preserved. Split regions or
  components when different SDK materials are required.
- Keep one unit convention per CadQuery model. `unit_scale` also affects
  assembly/component locations.

## Solid Modeling Guidance

- Build a coherent solid before applying holes, shells, fillets, or chamfers.
- Select edges and faces from stable construction references when later
  operations depend on them.
- Use actual cuts for visible holes, slots, and cavities; overlapping dark
  geometry is not a substitute.
- Check wall thickness and opening topology after shell or boolean operations.
- Tessellation tolerance controls the exported mesh, not the underlying CAD
  solid. Tighten it only where visible curvature requires it.

## Common Edge And Form Patterns

Apply edge finishing after the primary solid is coherent and before managed
mesh export. Select only the intended edges; broad unscoped selectors can round
mounting edges or change clearances.

```python
rounded_panel = (
    cq.Workplane("XY")
    .box(0.60, 0.04, 0.80)
    .edges("|Z")
    .fillet(0.018)
)

beveled_base = (
    cq.Workplane("XY")
    .cylinder(0.06, 0.24)
    .edges(">Z")
    .chamfer(0.008)
)
```

For padded or curved forms, use a rounded profile or sections rather than
stacking thin cylinders. For a shell, create the outer solid, apply the visible
fillets, then shell or cut the opening while preserving wall thickness. Keep
the joint pivot and child local frame independent from the CAD workplane, and
export with `mesh_from_cadquery(...)` only after checking the resulting bounds.

Stop reading when the current solid operations and managed export path are
clear. Do not read both integration and API details unless the current patch
actually depends on both.
