from __future__ import annotations

from pathlib import Path

from pxr import Usd

from sdk import (
    ArticulatedObject,
    ArticulationType,
    Box,
    Material,
    MotionLimits,
    Origin,
)
from sdk.v0._usd_export import compile_object_to_usd_bytes


def test_compile_object_to_usd_bytes_authors_visuals_collisions_materials_and_joint(
    tmp_path: Path,
) -> None:
    model = ArticulatedObject(name="hinged_box")
    base = model.part("base")
    lid = model.part("lid")
    blue = Material("blue", rgba=(0.1, 0.2, 0.8, 1.0))
    base.visual(Box((1.0, 0.8, 0.2)), material=blue, name="base_shell")
    lid.visual(
        Box((1.0, 0.8, 0.1)),
        origin=Origin(xyz=(0.0, 0.0, 0.05)),
        material=blue,
        name="lid_shell",
    )
    model.articulation(
        "lid_hinge",
        ArticulationType.REVOLUTE,
        parent=base,
        child=lid,
        origin=Origin(xyz=(0.0, 0.4, 0.2)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(lower=0.0, upper=1.5),
    )

    usd_bytes = compile_object_to_usd_bytes(model, asset_root=tmp_path)

    assert usd_bytes.startswith(b"PXR-USDC")
    usd_path = tmp_path / "model.usd"
    usd_path.write_bytes(usd_bytes)
    stage = Usd.Stage.Open(str(usd_path))
    assert stage is not None
    assert stage.GetDefaultPrim().GetPath().pathString == "/root"
    assert stage.GetPrimAtPath("/root/base/Visuals/base_shell").IsValid()
    assert stage.GetPrimAtPath("/root/base/Collisions/base_shell").IsValid()
    assert stage.GetPrimAtPath("/root/Looks/blue/Shader").IsValid()
    assert stage.GetPrimAtPath("/root/Joints/lid_hinge").GetTypeName() == "PhysicsRevoluteJoint"
