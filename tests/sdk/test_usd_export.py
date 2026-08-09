from __future__ import annotations

import math
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
    MotionProperties,
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
    assert base_prim.GetAttribute("articraft:physicsMaterialSource").Get() == "explicit"
    assert lid_prim.GetAttribute("articraft:physicsMaterialSource").Get() == "explicit"
    physics_material = stage.GetPrimAtPath("/root/Physics/Materials/steel")
    physics_api = UsdPhysics.MaterialAPI(physics_material)
    assert physics_api.GetDensityAttr().HasAuthoredValueOpinion()
    assert physics_api.GetDensityAttr().Get() == pytest.approx(7800.0)
    assert physics_api.GetStaticFrictionAttr().Get() == pytest.approx(0.7)
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


def test_usd_and_urdf_export_passive_joint_dynamics(tmp_path: Path) -> None:
    model = ArticulatedObject(name="passive_joint_dynamics")
    base = model.part("base")
    door = model.part("door")
    drawer = model.part("drawer")
    base.visual(Box((1.0, 0.6, 1.0)), name="base_shell")
    door.visual(Box((0.5, 0.04, 0.8)), name="door_shell")
    drawer.visual(Box((0.4, 0.4, 0.15)), name="drawer_shell")
    model.articulation(
        "door_hinge",
        ArticulationType.REVOLUTE,
        parent=base,
        child=door,
        motion_limits=MotionLimits(effort=12.0, velocity=1.4, lower=0.0, upper=1.5),
        motion_properties=MotionProperties(
            damping=0.36,
            friction=0.2,
            stiffness=40.0,
            equilibrium=0.1,
        ),
    )
    model.articulation(
        "drawer_slide",
        ArticulationType.PRISMATIC,
        parent=base,
        child=drawer,
        motion_limits=MotionLimits(effort=28.0, velocity=0.35, lower=0.0, upper=0.3),
        motion_properties=MotionProperties(damping=3.0, friction=1.5),
    )

    usd_path = tmp_path / "passive_joint_dynamics.usd"
    usd_path.write_bytes(compile_object_to_usd_bytes(model, asset_root=tmp_path))
    stage = Usd.Stage.Open(str(usd_path))
    assert stage is not None

    hinge = stage.GetPrimAtPath("/root/Joints/door_hinge")
    assert hinge.HasAPI(UsdPhysics.DriveAPI, UsdPhysics.Tokens.angular)
    assert hinge.GetAttribute("drive:angular:physics:type").Get() == UsdPhysics.Tokens.force
    assert hinge.GetAttribute("drive:angular:physics:stiffness").Get() == pytest.approx(
        40.0 * math.pi / 180.0
    )
    assert hinge.GetAttribute("drive:angular:physics:damping").Get() == pytest.approx(
        0.36 * math.pi / 180.0
    )
    assert hinge.GetAttribute("drive:angular:physics:targetVelocity").Get() == 0.0
    assert hinge.GetAttribute("drive:angular:physics:targetPosition").Get() == pytest.approx(
        0.1 * 180.0 / math.pi
    )
    assert hinge.GetAttribute("drive:angular:physics:maxForce").Get() == pytest.approx(12.0)
    assert hinge.GetAttribute("articraft:jointFriction").Get() == pytest.approx(0.2)
    assert hinge.GetAttribute("articraft:jointStiffness").Get() == pytest.approx(40.0)
    assert hinge.GetAttribute("articraft:jointEquilibrium").Get() == pytest.approx(0.1)

    slide = stage.GetPrimAtPath("/root/Joints/drawer_slide")
    assert slide.HasAPI(UsdPhysics.DriveAPI, UsdPhysics.Tokens.linear)
    assert slide.GetAttribute("drive:linear:physics:damping").Get() == pytest.approx(3.0)
    assert slide.GetAttribute("drive:linear:physics:maxForce").Get() == pytest.approx(28.0)
    assert slide.GetAttribute("articraft:jointFriction").Get() == pytest.approx(1.5)

    root = ET.fromstring(compile_object_to_urdf_xml(model))
    joints = {joint.attrib["name"]: joint for joint in root.findall("joint")}
    assert joints["door_hinge"].find("dynamics").attrib == {
        "damping": "0.36",
        "friction": "0.2",
    }
    assert joints["drawer_slide"].find("dynamics").attrib == {
        "damping": "3",
        "friction": "1.5",
    }
