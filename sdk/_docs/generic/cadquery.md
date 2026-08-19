# CadQuery Geometry

## Purpose

Use CadQuery to author feature-based solids when primitive descriptors or
procedural meshes are a poor fit: shells, fillets, chamfers, holes, grooves,
repeated cuts, and solid booleans. Keep parts, joints, materials, physics, tests,
and final export in the Articraft SDK.

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

For full CadQuery call signatures, read
`docs/sdk/references/cadquery/api-ref.md` only after choosing the CadQuery path.

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
