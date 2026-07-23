from __future__ import annotations

import math
import os

import numpy as np

from .assets import resolve_mesh_path
from .errors import ValidationError
from .geometry_qc import _origin_to_mat4
from .types import (
    Box,
    Cylinder,
    Geometry,
    Inertia,
    Inertial,
    Mesh,
    Origin,
    Part,
    PhysicsMaterial,
    Sphere,
)
from .viewer_assets import load_obj_triangles

Mat4 = tuple[tuple[float, float, float, float], ...]


def resolve_part_inertial(
    part: Part,
    *,
    asset_root: object = None,
) -> tuple[Inertial, str]:
    """Return authored inertia or a collision-derived fallback for a part."""
    if part.inertial is not None:
        return part.inertial, "explicit"

    resolved_assets = asset_root if asset_root is not None else part.assets
    lower, upper, volume = _collision_bounds_and_volume(part, asset_root=resolved_assets)
    dimensions = tuple(max(1e-4, float(upper[index] - lower[index])) for index in range(3))
    density = float((part.physics_material or PhysicsMaterial()).density)
    mass = max(1e-4, density * max(volume, 1e-9))
    x, y, z = dimensions
    inertia = Inertia(
        ixx=(mass / 12.0) * (y * y + z * z),
        ixy=0.0,
        ixz=0.0,
        iyy=(mass / 12.0) * (x * x + z * z),
        iyz=0.0,
        izz=(mass / 12.0) * (x * x + y * y),
    )
    center = tuple((float(lower[index]) + float(upper[index])) * 0.5 for index in range(3))
    return Inertial(mass=mass, inertia=inertia, origin=Origin(xyz=center)), "estimated_collision"


def _collision_bounds_and_volume(
    part: Part,
    *,
    asset_root: object,
) -> tuple[np.ndarray, np.ndarray, float]:
    lower = np.asarray((math.inf, math.inf, math.inf), dtype=np.float64)
    upper = np.asarray((-math.inf, -math.inf, -math.inf), dtype=np.float64)
    volume = 0.0
    for collision in part.collisions:
        geometry_lower, geometry_upper, geometry_volume = _geometry_bounds_and_volume(
            collision.geometry,
            asset_root=asset_root,
        )
        geometry_lower, geometry_upper = _transform_bounds(
            geometry_lower,
            geometry_upper,
            _origin_to_mat4(collision.origin),
        )
        lower = np.minimum(lower, geometry_lower)
        upper = np.maximum(upper, geometry_upper)
        volume += geometry_volume

    if not np.isfinite(lower).all() or not np.isfinite(upper).all():
        # A visual-only part must remain simulatable rather than becoming massless.
        lower = np.asarray((-0.05, -0.05, -0.05), dtype=np.float64)
        upper = np.asarray((0.05, 0.05, 0.05), dtype=np.float64)
        volume = 0.001
    return lower, upper, volume


def _geometry_bounds_and_volume(
    geometry: Geometry,
    *,
    asset_root: object,
) -> tuple[np.ndarray, np.ndarray, float]:
    if isinstance(geometry, Box):
        dimensions = np.asarray(geometry.size, dtype=np.float64)
        half = np.abs(dimensions) * 0.5
        return -half, half, float(np.prod(np.abs(dimensions)))
    if isinstance(geometry, Cylinder):
        radius = abs(float(geometry.radius))
        length = abs(float(geometry.length))
        half = np.asarray((radius, radius, length * 0.5), dtype=np.float64)
        return -half, half, math.pi * radius * radius * length
    if isinstance(geometry, Sphere):
        radius = abs(float(geometry.radius))
        half = np.asarray((radius, radius, radius), dtype=np.float64)
        return -half, half, (4.0 / 3.0) * math.pi * radius**3
    if isinstance(geometry, Mesh):
        if geometry.source_geometry is not None:
            return _geometry_bounds_and_volume(geometry.source_geometry, asset_root=asset_root)
        if not geometry.filename:
            raise ValidationError("Mesh geometry filename is missing while estimating inertia")
        mesh_path = resolve_mesh_path(os.fspath(geometry.filename), assets=asset_root)
        vertices, _faces, _normals, _normal_indices = load_obj_triangles(mesh_path)
        scaled_vertices = np.asarray(vertices, dtype=np.float64)
        scale = np.asarray(geometry.scale or (1.0, 1.0, 1.0), dtype=np.float64)
        scaled_vertices = scaled_vertices * scale
        lower = np.min(scaled_vertices, axis=0)
        upper = np.max(scaled_vertices, axis=0)
        # Generated meshes are not always watertight, so their signed volume is unreliable.
        volume = float(np.prod(np.maximum(upper - lower, 1e-4))) * 0.4
        return lower, upper, volume
    raise ValidationError(
        f"Unsupported geometry type while estimating inertia: {type(geometry).__name__}"
    )


def _transform_bounds(
    lower: np.ndarray,
    upper: np.ndarray,
    transform: Mat4,
) -> tuple[np.ndarray, np.ndarray]:
    corners = np.asarray(
        [
            (x, y, z, 1.0)
            for x in (lower[0], upper[0])
            for y in (lower[1], upper[1])
            for z in (lower[2], upper[2])
        ],
        dtype=np.float64,
    )
    transformed = corners @ np.asarray(transform, dtype=np.float64).T
    return np.min(transformed[:, :3], axis=0), np.max(transformed[:, :3], axis=0)
