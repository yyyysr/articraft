from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdPhysics, UsdShade, Vt

from ._physics_properties import resolve_part_inertial
from .articulated_object import ArticulatedObject
from .assets import resolve_mesh_path
from .errors import ValidationError
from .exact_collisions import compile_object_model_with_exact_collisions
from .geometry_qc import (
    _mat4_mul,
    _origin_to_mat4,
    compute_part_world_transforms,
)
from .material_catalog import (
    copy_catalog_material,
    resolve_material_entry,
    validate_material_parameters,
)
from .types import (
    Articulation,
    ArticulationType,
    Box,
    Cylinder,
    Geometry,
    Inertial,
    Material,
    Mesh,
    MotionLimits,
    Origin,
    Part,
    PhysicsMaterial,
    Sphere,
    Visual,
)
from .viewer_assets import load_obj_triangles

Mat4 = tuple[tuple[float, float, float, float], ...]
Vec3 = tuple[float, float, float]

USD_ROOT_PATH = "/root"
USD_LOOKS_SCOPE = "Looks"
USD_PHYSICS_SCOPE = "Physics"
USD_PHYSICS_MATERIALS_SCOPE = "Materials"
USD_VISUALS_SCOPE = "Visuals"
USD_COLLISIONS_SCOPE = "Collisions"
USD_JOINTS_SCOPE = "Joints"


def compile_object_to_usd_file(
    object_model: ArticulatedObject,
    output_path: str | os.PathLike[str] | Path,
    *,
    asset_root: object = None,
    include_physical_collisions: bool = True,
    validate: bool = True,
    binary: bool = True,
) -> Path:
    """Compile an Articraft object model into a self-contained OpenUSD layer."""
    if validate:
        object_model.validate(strict=True)

    resolved_assets = asset_root if asset_root is not None else object_model.assets
    compiled_model = (
        compile_object_model_with_exact_collisions(
            object_model,
            asset_root=resolved_assets,
            validate=False,
        )
        if include_physical_collisions
        else object_model
    )

    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    author_path = output
    temporary_ascii: Path | None = None
    if binary and output.suffix.lower() == ".usd":
        fd, tmp_name = tempfile.mkstemp(
            prefix=f"{output.stem}-",
            suffix=".usda",
            dir=output.parent,
        )
        os.close(fd)
        temporary_ascii = Path(tmp_name)
        author_path = temporary_ascii

    stage = Usd.Stage.CreateNew(str(author_path))
    if stage is None:
        raise ValidationError(f"Failed to create USD stage: {author_path}")
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

    root = UsdGeom.Xform.Define(stage, USD_ROOT_PATH)
    stage.SetDefaultPrim(root.GetPrim())
    UsdPhysics.ArticulationRootAPI.Apply(root.GetPrim())
    root.GetPrim().CreateAttribute("articraft:assetFormat", Sdf.ValueTypeNames.String).Set(
        "interactive_usd"
    )

    UsdGeom.Scope.Define(stage, f"{USD_ROOT_PATH}/{USD_LOOKS_SCOPE}")
    UsdGeom.Scope.Define(stage, f"{USD_ROOT_PATH}/{USD_PHYSICS_SCOPE}")
    UsdGeom.Scope.Define(
        stage,
        f"{USD_ROOT_PATH}/{USD_PHYSICS_SCOPE}/{USD_PHYSICS_MATERIALS_SCOPE}",
    )
    UsdGeom.Scope.Define(stage, f"{USD_ROOT_PATH}/{USD_JOINTS_SCOPE}")
    physics_scene = UsdPhysics.Scene.Define(
        stage,
        f"{USD_ROOT_PATH}/{USD_PHYSICS_SCOPE}/PhysicsScene",
    )
    physics_scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))
    physics_scene.CreateGravityMagnitudeAttr(9.81)

    material_paths = _define_materials(stage, compiled_model)
    physics_material_paths: dict[PhysicsMaterial, Sdf.Path] = {}
    used_physics_material_names: set[str] = set()
    world_transforms = compute_part_world_transforms(compiled_model, {})
    part_paths: dict[str, Sdf.Path] = {}
    used_part_names: set[str] = set()

    for part in compiled_model.parts:
        part_name = _unique_identifier(part.name, used_part_names)
        part_path = Sdf.Path(f"{USD_ROOT_PATH}/{part_name}")
        part_paths[part.name] = part_path
        body = UsdGeom.Xform.Define(stage, str(part_path))
        _set_transform(body, world_transforms[part.name])
        body.GetPrim().CreateAttribute("articraft:partName", Sdf.ValueTypeNames.String).Set(
            part.name
        )
        inertial, inertial_source = resolve_part_inertial(part, asset_root=resolved_assets)
        _apply_rigid_body(body, inertial=inertial, source=inertial_source)

        visuals = UsdGeom.Xform.Define(stage, str(part_path.AppendChild(USD_VISUALS_SCOPE)))
        collisions = UsdGeom.Xform.Define(
            stage,
            str(part_path.AppendChild(USD_COLLISIONS_SCOPE)),
        )
        collisions.CreatePurposeAttr(UsdGeom.Tokens.guide)

        used_visual_names: set[str] = set()
        for index, visual in enumerate(part.visuals):
            visual_name = _unique_identifier(
                visual.name or f"visual_{index:03d}",
                used_visual_names,
            )
            prim = _define_geometry_prim(
                stage,
                visuals.GetPath().AppendChild(visual_name),
                visual.geometry,
                visual.origin,
                asset_root=resolved_assets,
            )
            prim.CreateAttribute("articraft:partName", Sdf.ValueTypeNames.String).Set(part.name)
            if visual.name:
                prim.CreateAttribute("articraft:elementName", Sdf.ValueTypeNames.String).Set(
                    visual.name
                )
            material_path = _material_path_for_visual(visual, material_paths)
            if material_path is not None:
                UsdShade.MaterialBindingAPI.Apply(prim).Bind(
                    UsdShade.Material.Get(stage, material_path)
                )

        used_collision_names: set[str] = set()
        physics_material_path = _physics_material_path_for_part(
            stage,
            part,
            paths=physics_material_paths,
            used_names=used_physics_material_names,
        )
        for index, collision in enumerate(part.collisions):
            collision_name = _unique_identifier(
                collision.name or f"collision_{index:03d}",
                used_collision_names,
            )
            prim = _define_geometry_prim(
                stage,
                collisions.GetPath().AppendChild(collision_name),
                collision.geometry,
                collision.origin,
                asset_root=resolved_assets,
            )
            prim.CreateAttribute("articraft:partName", Sdf.ValueTypeNames.String).Set(part.name)
            if collision.name:
                prim.CreateAttribute("articraft:elementName", Sdf.ValueTypeNames.String).Set(
                    collision.name
                )
            _apply_collision(stage, prim, physics_material_path=physics_material_path)

    used_joint_names: set[str] = set()
    for articulation in compiled_model.articulations:
        _define_joint(
            stage,
            articulation,
            part_paths=part_paths,
            used_names=used_joint_names,
        )

    stage.GetRootLayer().Save()
    if temporary_ascii is not None:
        authored_stage = Usd.Stage.Open(str(temporary_ascii))
        if authored_stage is None:
            raise ValidationError(f"Failed to reopen temporary USD layer: {temporary_ascii}")
        if not authored_stage.GetRootLayer().Export(str(output)):
            raise ValidationError(f"Failed to export binary USD layer: {output}")
        temporary_ascii.unlink(missing_ok=True)

    return output


def compile_object_to_usd_bytes(
    object_model: ArticulatedObject,
    *,
    asset_root: object = None,
    include_physical_collisions: bool = True,
    validate: bool = True,
) -> bytes:
    """Compile an object model and return compact model.usd bytes."""
    with tempfile.TemporaryDirectory(prefix="articraft-usd-") as tmp:
        path = Path(tmp) / "model.usd"
        compile_object_to_usd_file(
            object_model,
            path,
            asset_root=asset_root,
            include_physical_collisions=include_physical_collisions,
            validate=validate,
        )
        return path.read_bytes()


def _define_materials(
    stage: Usd.Stage,
    model: ArticulatedObject,
) -> dict[str, Sdf.Path]:
    paths: dict[str, Sdf.Path] = {}
    used_names: set[str] = set()
    for material in _iter_materials(model):
        if material.name in paths:
            continue
        token = _unique_identifier(material.name, used_names)
        path = Sdf.Path(f"{USD_ROOT_PATH}/{USD_LOOKS_SCOPE}/{token}")
        if material.catalog:
            entry = resolve_material_entry(material.catalog, material.catalog_material or "")
            validate_material_parameters(entry, material.parameters)
            copy_catalog_material(stage, entry, path)
            paths[material.name] = path
            continue
        usd_material = UsdShade.Material.Define(stage, str(path))
        shader = UsdShade.Shader.Define(stage, str(path.AppendChild("Shader")))
        shader.CreateIdAttr("UsdPreviewSurface")
        rgba = material.rgba or (0.8, 0.8, 0.8, 1.0)
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(float(rgba[0]), float(rgba[1]), float(rgba[2]))
        )
        shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(rgba[3]))
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.55)
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        usd_material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        if material.texture:
            shader.GetPrim().CreateAttribute(
                "articraft:sourceTexture",
                Sdf.ValueTypeNames.String,
            ).Set(str(material.texture))
        paths[material.name] = path
    return paths


def _iter_materials(model: ArticulatedObject) -> Iterable[Material]:
    seen: set[str] = set()
    for material in model.materials:
        if material.name not in seen:
            seen.add(material.name)
            yield material
    for part in model.parts:
        for visual in part.visuals:
            material = visual.material
            if isinstance(material, Material) and material.name not in seen:
                seen.add(material.name)
                yield material


def _material_path_for_visual(
    visual: Visual,
    material_paths: dict[str, Sdf.Path],
) -> Sdf.Path | None:
    material = visual.material
    if material is None:
        return None
    return material_paths.get(material.name if isinstance(material, Material) else str(material))


def _define_geometry_prim(
    stage: Usd.Stage,
    path: Sdf.Path,
    geometry: Geometry,
    origin: Origin,
    *,
    asset_root: object,
) -> Usd.Prim:
    if isinstance(geometry, Box):
        prim = UsdGeom.Cube.Define(stage, str(path))
        prim.CreateSizeAttr(1.0)
        transform = _mat4_mul(
            _origin_to_mat4(origin),
            _scale_mat4(tuple(float(value) for value in geometry.size)),
        )
        _set_transform(prim, transform)
        return prim.GetPrim()

    if isinstance(geometry, Cylinder):
        prim = UsdGeom.Cylinder.Define(stage, str(path))
        prim.CreateAxisAttr(UsdGeom.Tokens.z)
        prim.CreateRadiusAttr(float(geometry.radius))
        prim.CreateHeightAttr(float(geometry.length))
        _set_transform(prim, _origin_to_mat4(origin))
        return prim.GetPrim()

    if isinstance(geometry, Sphere):
        prim = UsdGeom.Sphere.Define(stage, str(path))
        prim.CreateRadiusAttr(float(geometry.radius))
        _set_transform(prim, _origin_to_mat4(origin))
        return prim.GetPrim()

    if isinstance(geometry, Mesh):
        if not geometry.filename:
            raise ValidationError("Mesh geometry filename is missing during USD export")
        mesh_path = resolve_mesh_path(os.fspath(geometry.filename), assets=asset_root)
        vertices, faces, _normals, _normal_indices = load_obj_triangles(mesh_path)
        scaled_vertices = np.asarray(vertices, dtype=np.float64).copy()
        scale = geometry.scale or (1.0, 1.0, 1.0)
        scaled_vertices[:, 0] *= float(scale[0])
        scaled_vertices[:, 1] *= float(scale[1])
        scaled_vertices[:, 2] *= float(scale[2])

        prim = UsdGeom.Mesh.Define(stage, str(path))
        _set_transform(prim, _origin_to_mat4(origin))
        _author_mesh_arrays(prim, scaled_vertices, np.asarray(faces, dtype=np.int32))
        prim.GetPrim().CreateAttribute("articraft:sourceMesh", Sdf.ValueTypeNames.String).Set(
            os.fspath(geometry.filename)
        )
        return prim.GetPrim()

    raise ValidationError(f"Unsupported geometry type for USD export: {type(geometry).__name__}")


def _author_mesh_arrays(
    mesh: UsdGeom.Mesh,
    vertices: np.ndarray,
    faces: np.ndarray,
) -> None:
    points = [Gf.Vec3f(float(x), float(y), float(z)) for x, y, z in vertices.tolist()]
    counts = [int(len(face)) for face in faces]
    indices = [int(index) for face in faces.tolist() for index in face]
    mesh.CreatePointsAttr(Vt.Vec3fArray(points))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray(counts))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray(indices))
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)


def _apply_rigid_body(
    body: UsdGeom.Xform,
    *,
    inertial: Inertial,
    source: str,
) -> None:
    UsdPhysics.RigidBodyAPI.Apply(body.GetPrim()).CreateRigidBodyEnabledAttr(True)
    mass_api = UsdPhysics.MassAPI.Apply(body.GetPrim())
    mass_api.CreateMassAttr(float(inertial.mass))
    mass_api.CreateCenterOfMassAttr(Gf.Vec3f(*tuple(float(v) for v in inertial.origin.xyz)))
    mass_api.CreateDiagonalInertiaAttr(
        Gf.Vec3f(
            float(inertial.inertia.ixx),
            float(inertial.inertia.iyy),
            float(inertial.inertia.izz),
        )
    )
    mass_api.CreatePrincipalAxesAttr(_origin_quat(inertial.origin))
    body.GetPrim().CreateAttribute("articraft:inertialSource", Sdf.ValueTypeNames.Token).Set(source)


def _apply_collision(
    stage: Usd.Stage,
    prim: Usd.Prim,
    *,
    physics_material_path: Sdf.Path,
) -> None:
    imageable = UsdGeom.Imageable(prim)
    if imageable:
        imageable.CreatePurposeAttr(UsdGeom.Tokens.guide)
    UsdPhysics.CollisionAPI.Apply(prim).CreateCollisionEnabledAttr(True)
    if prim.IsA(UsdGeom.Mesh):
        UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr(
            UsdPhysics.Tokens.convexDecomposition
        )
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(
        UsdShade.Material.Get(stage, physics_material_path),
        materialPurpose="physics",
    )


def _physics_material_path_for_part(
    stage: Usd.Stage,
    part: Part,
    *,
    paths: dict[PhysicsMaterial, Sdf.Path],
    used_names: set[str],
) -> Sdf.Path:
    material = part.physics_material or PhysicsMaterial()
    existing = paths.get(material)
    if existing is not None:
        return existing

    token = _unique_identifier(material.name, used_names)
    path = Sdf.Path(f"{USD_ROOT_PATH}/{USD_PHYSICS_SCOPE}/{USD_PHYSICS_MATERIALS_SCOPE}/{token}")
    usd_material = UsdShade.Material.Define(stage, str(path))
    physics_api = UsdPhysics.MaterialAPI.Apply(usd_material.GetPrim())
    physics_api.CreateStaticFrictionAttr(float(material.static_friction))
    physics_api.CreateDynamicFrictionAttr(float(material.dynamic_friction))
    physics_api.CreateRestitutionAttr(float(material.restitution))
    usd_material.GetPrim().CreateAttribute("articraft:density", Sdf.ValueTypeNames.Float).Set(
        float(material.density)
    )
    paths[material] = path
    return path


def _define_joint(
    stage: Usd.Stage,
    articulation: Articulation,
    *,
    part_paths: dict[str, Sdf.Path],
    used_names: set[str],
) -> None:
    parent_path = part_paths.get(articulation.parent)
    child_path = part_paths.get(articulation.child)
    if parent_path is None or child_path is None:
        raise ValidationError(
            f"Joint {articulation.name!r} references a missing parent or child part"
        )

    name = _unique_identifier(articulation.name, used_names)
    path = Sdf.Path(f"{USD_ROOT_PATH}/{USD_JOINTS_SCOPE}/{name}")
    joint_type = articulation.articulation_type
    axis_frame: Gf.Quatf | None = None

    if joint_type == ArticulationType.FIXED:
        joint = UsdPhysics.FixedJoint.Define(stage, str(path))
    elif joint_type in {ArticulationType.REVOLUTE, ArticulationType.CONTINUOUS}:
        joint = UsdPhysics.RevoluteJoint.Define(stage, str(path))
        axis_token, axis_frame = _axis_token_and_frame_quat(articulation.axis)
        joint.CreateAxisAttr(axis_token)
        lower, upper = _angular_limits_degrees(articulation, articulation.motion_limits)
        joint.CreateLowerLimitAttr(float(lower))
        joint.CreateUpperLimitAttr(float(upper))
    elif joint_type == ArticulationType.PRISMATIC:
        joint = UsdPhysics.PrismaticJoint.Define(stage, str(path))
        axis_token, axis_frame = _axis_token_and_frame_quat(articulation.axis)
        joint.CreateAxisAttr(axis_token)
        lower, upper = _linear_limits(articulation.motion_limits)
        joint.CreateLowerLimitAttr(float(lower))
        joint.CreateUpperLimitAttr(float(upper))
    else:
        raise ValidationError(
            f"Unsupported USD articulation type {joint_type!r} for {articulation.name!r}"
        )

    joint.CreateBody0Rel().SetTargets([parent_path])
    joint.CreateBody1Rel().SetTargets([child_path])
    joint.CreateJointEnabledAttr(True)
    joint.CreateCollisionEnabledAttr(False)
    joint.CreateLocalPos0Attr(Gf.Vec3f(*tuple(float(v) for v in articulation.origin.xyz)))
    joint.CreateLocalPos1Attr(Gf.Vec3f(0.0, 0.0, 0.0))
    joint.CreateLocalRot0Attr(_compose_quats(_origin_quat(articulation.origin), axis_frame))
    joint.CreateLocalRot1Attr(axis_frame or _quat_identity())
    joint.GetPrim().CreateAttribute("articraft:jointName", Sdf.ValueTypeNames.String).Set(
        articulation.name
    )


def _angular_limits_degrees(
    articulation: Articulation,
    limits: MotionLimits | None,
) -> tuple[float, float]:
    if articulation.articulation_type == ArticulationType.CONTINUOUS or limits is None:
        return (-180.0, 180.0)
    lower = -math.pi if limits.lower is None else float(limits.lower)
    upper = math.pi if limits.upper is None else float(limits.upper)
    return _sorted_pair(math.degrees(lower), math.degrees(upper))


def _linear_limits(limits: MotionLimits | None) -> tuple[float, float]:
    if limits is None:
        return (-0.1, 0.1)
    lower = -0.1 if limits.lower is None else float(limits.lower)
    upper = 0.1 if limits.upper is None else float(limits.upper)
    return _sorted_pair(lower, upper)


def _sorted_pair(first: float, second: float) -> tuple[float, float]:
    return (first, second) if first <= second else (second, first)


def _axis_token_and_frame_quat(axis: Sequence[float]) -> tuple[str, Gf.Quatf]:
    normalized = _normalized_axis(axis)
    magnitudes = [abs(value) for value in normalized]
    index = magnitudes.index(max(magnitudes))
    token = ("X", "Y", "Z")[index]
    token_axis = (
        Gf.Vec3d(1.0, 0.0, 0.0)
        if token == "X"
        else Gf.Vec3d(0.0, 1.0, 0.0)
        if token == "Y"
        else Gf.Vec3d(0.0, 0.0, 1.0)
    )
    rotation = Gf.Rotation(token_axis, Gf.Vec3d(*normalized)).GetQuat().GetNormalized()
    return token, _gf_quat_to_quatf(rotation)


def _normalized_axis(axis: Sequence[float]) -> Vec3:
    values = (float(axis[0]), float(axis[1]), float(axis[2]))
    length = math.sqrt(sum(value * value for value in values))
    if length <= 1e-12:
        return (0.0, 0.0, 1.0)
    return (values[0] / length, values[1] / length, values[2] / length)


def _origin_quat(origin: Origin) -> Gf.Quatf:
    quat = _mat4_to_gf_matrix(_origin_to_mat4(origin)).ExtractRotationQuat().GetNormalized()
    return _gf_quat_to_quatf(quat)


def _gf_quat_to_quatf(quat: Gf.Quatd | Gf.Quatf) -> Gf.Quatf:
    imaginary = quat.GetImaginary()
    return Gf.Quatf(
        float(quat.GetReal()),
        float(imaginary[0]),
        float(imaginary[1]),
        float(imaginary[2]),
    )


def _compose_quats(first: Gf.Quatf, second: Gf.Quatf | None) -> Gf.Quatf:
    if second is None:
        return first
    return _gf_quat_to_quatf((first * second).GetNormalized())


def _quat_identity() -> Gf.Quatf:
    return Gf.Quatf(1.0, 0.0, 0.0, 0.0)


def _set_transform(xformable: UsdGeom.Xformable, transform: Mat4) -> None:
    xformable.AddTransformOp().Set(_mat4_to_gf_matrix(transform))


def _mat4_to_gf_matrix(transform: Mat4) -> Gf.Matrix4d:
    return Gf.Matrix4d(
        tuple(tuple(float(transform[column][row]) for column in range(4)) for row in range(4))
    )


def _scale_mat4(scale: Vec3) -> Mat4:
    return (
        (float(scale[0]), 0.0, 0.0, 0.0),
        (0.0, float(scale[1]), 0.0, 0.0),
        (0.0, 0.0, float(scale[2]), 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


def _unique_identifier(raw_name: str, used: set[str]) -> str:
    identifier = Tf.MakeValidIdentifier(_ascii_identifier(raw_name)) or "prim"
    if identifier[0].isdigit():
        identifier = f"_{identifier}"
    base = identifier
    suffix = 1
    while identifier in used:
        identifier = f"{base}_{suffix:03d}"
        suffix += 1
    used.add(identifier)
    return identifier


def _ascii_identifier(raw_name: str) -> str:
    text = str(raw_name or "prim").encode("ascii", "ignore").decode("ascii")
    return "_".join(text.split()).strip("_") or "prim"


__all__ = ["compile_object_to_usd_bytes", "compile_object_to_usd_file"]
