from __future__ import annotations

import pytest

from sdk import ArticulatedObject, Box, Cylinder, Material, MotionProperties, ValidationError


def test_part_get_visual_returns_named_visual() -> None:
    model = ArticulatedObject(name="visual_lookup")
    part = model.part("body")
    visual = part.visual(Box((0.1, 0.1, 0.1)), name="shell")

    assert part.get_visual("shell") is visual


def test_part_get_visual_rejects_missing_name() -> None:
    model = ArticulatedObject(name="visual_lookup")
    part = model.part("body")
    part.visual(Box((0.1, 0.1, 0.1)), name="shell")

    with pytest.raises(Exception, match="Unknown visual"):
        part.get_visual("missing")


def test_cylinder_accepts_height_alias() -> None:
    cylinder = Cylinder(radius=0.1, height=0.4)

    assert cylinder.radius == 0.1
    assert cylinder.length == 0.4
    assert cylinder.height == 0.4


def test_cylinder_rejects_length_and_height_together() -> None:
    with pytest.raises(TypeError, match="only one of 'length' or alias 'height'"):
        Cylinder(radius=0.1, length=0.4, height=0.4)


def test_part_visual_accepts_color_alias_as_named_material() -> None:
    model = ArticulatedObject(name="visual_color_alias")
    part = model.part("body")

    visual = part.visual(Box((0.1, 0.1, 0.1)), color="steel_blue", name="shell")

    assert visual.material == "steel_blue"


def test_part_visual_accepts_color_alias_as_rgba_tuple() -> None:
    model = ArticulatedObject(name="visual_color_alias")
    part = model.part("body")

    visual = part.visual(Box((0.1, 0.1, 0.1)), color=(0.1, 0.2, 0.3, 0.4), name="shell")

    assert isinstance(visual.material, Material)
    assert visual.material.rgba == (0.1, 0.2, 0.3, 0.4)


def test_part_visual_rejects_material_and_color_together() -> None:
    model = ArticulatedObject(name="visual_color_alias")
    part = model.part("body")

    with pytest.raises(TypeError, match="only one of 'material' or alias 'color'"):
        part.visual(Box((0.1, 0.1, 0.1)), material="steel", color="blue")


def test_material_accepts_color_alias_with_rgb_tuple() -> None:
    material = Material(name="paint", color=(0.1, 0.2, 0.3))

    assert material.rgba == (0.1, 0.2, 0.3, 1.0)


def test_material_accepts_color_alias_with_rgba_tuple() -> None:
    material = Material(name="paint", color=(0.1, 0.2, 0.3, 0.4))

    assert material.rgba == (0.1, 0.2, 0.3, 0.4)


def test_material_rejects_rgba_and_color_together() -> None:
    with pytest.raises(ValidationError, match="Material cannot set both rgba and color"):
        Material(name="paint", rgba=(0.1, 0.2, 0.3, 1.0), color=(0.2, 0.3, 0.4, 1.0))


def test_material_preserves_positional_rgba_usage() -> None:
    material = Material("paint", (0.1, 0.2, 0.3, 1.0))

    assert material.rgba == (0.1, 0.2, 0.3, 1.0)


def test_articulated_object_material_accepts_material_compatibility_form() -> None:
    model = ArticulatedObject(name="material_compat")
    material = Material("wood", catalog="wood_furniture", catalog_material="wood_001")

    registered = model.material(material)

    assert registered is material
    assert model.materials == [material]


def test_articulated_object_material_rejects_mixed_material_forms() -> None:
    model = ArticulatedObject(name="material_compat")

    with pytest.raises(ValidationError, match="cannot be combined"):
        model.material(Material("wood"), rgba=(0.2, 0.2, 0.2, 1.0))


def test_articulated_object_material_rejects_non_string_name() -> None:
    model = ArticulatedObject(name="material_validation")

    with pytest.raises(ValidationError, match="string or Material instance"):
        model.material(123)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("damping", -0.1),
        ("friction", -0.1),
        ("stiffness", -0.1),
        ("damping", float("inf")),
        ("equilibrium", float("inf")),
    ),
)
def test_motion_properties_reject_invalid_values(field: str, value: float) -> None:
    with pytest.raises(ValidationError, match=f"motion_properties.{field}"):
        MotionProperties(**{field: value})


def test_motion_properties_distinguishes_unspecified_from_explicit_zero() -> None:
    unspecified = MotionProperties()
    frictionless = MotionProperties(damping=0.0, friction=0.0)

    assert unspecified.damping is None
    assert unspecified.friction is None
    assert frictionless.damping == 0.0
    assert frictionless.friction == 0.0
