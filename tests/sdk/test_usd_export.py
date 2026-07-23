from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from pxr import Usd, UsdPhysics

from sdk import (
    ArticulatedObject,
    ArticulationType,
    Box,
    Inertial,
    Material,
    MotionLimits,
    Origin,
    PhysicsMaterial,
)
from sdk.v0._urdf_export import compile_object_to_urdf_xml
from sdk.v0._usd_export import compile_object_to_usd_bytes


def test_compile_object_to_usd_bytes_authors_visuals_collisions_materials_and_joint(
    tmp_path: Path,
) -> None:
    model = ArticulatedObject(name="hinged_box")
    steel = PhysicsMaterial(
        "steel",
        density=7800.0,
        static_friction=0.7,
        dynamic_friction=0.5,
        restitution=0.02,
    )
    base = model.part(
        "base",
        inertial=Inertial.from_geometry(Box((1.0, 0.8, 0.2)), mass=3.0),
        physics_material=steel,
    )
    lid = model.part("lid", physics_material=steel)
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
    base_prim = stage.GetPrimAtPath("/root/base")
    lid_prim = stage.GetPrimAtPath("/root/lid")
    assert UsdPhysics.MassAPI(base_prim).GetMassAttr().Get() == 3.0
    assert UsdPhysics.MassAPI(lid_prim).GetMassAttr().Get() > 0.0
    assert base_prim.GetAttribute("articraft:inertialSource").Get() == "explicit"
    assert lid_prim.GetAttribute("articraft:inertialSource").Get() == "estimated_collision"
    physics_material = stage.GetPrimAtPath("/root/Physics/Materials/steel")
    assert UsdPhysics.MaterialAPI(physics_material).GetStaticFrictionAttr().Get() == pytest.approx(
        0.7
    )
    collision = stage.GetPrimAtPath("/root/base/Collisions/base_shell")
    assert collision.GetRelationship("material:binding:physics").GetTargets()


def test_compile_object_to_urdf_xml_derives_missing_inertial_from_collisions() -> None:
    model = ArticulatedObject(name="inertial_fallback")
    base = model.part("base")
    lid = model.part("lid")
    base.visual(Box((1.0, 0.8, 0.2)), name="base_shell")
    lid.visual(Box((0.6, 0.4, 0.1)), name="lid_shell")
    model.articulation("base_to_lid", ArticulationType.FIXED, parent=base, child=lid)

    root = ET.fromstring(compile_object_to_urdf_xml(model))
    links = {link.attrib["name"]: link for link in root.findall("link")}
    for name in ("base", "lid"):
        inertial = links[name].find("inertial")
        assert inertial is not None
        mass = inertial.find("mass")
        inertia = inertial.find("inertia")
        assert mass is not None and float(mass.attrib["value"]) > 0.0
        assert inertia is not None and float(inertia.attrib["izz"]) > 0.0
