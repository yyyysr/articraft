from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from pxr import Usd, UsdGeom, UsdShade

from sdk import ArticulatedObject, Box, Material, ValidationError
from sdk._core.v0.material_catalog import load_material_entries, resolve_material_entry
from sdk.v0._urdf_export import compile_object_to_urdf_xml
from sdk.v0._usd_export import (
    compile_object_to_usd_bytes,
    compile_object_to_usd_file,
    compile_object_to_usd_package,
)


def _catalog_model() -> ArticulatedObject:
    model = ArticulatedObject(name="catalog_box")
    finish = model.material(
        "shell_finish",
        catalog="builtin_openpbr",
        catalog_material="Aluminum Brushed",
    )
    model.part("body").visual(Box((0.4, 0.3, 0.2)), material=finish, name="shell")
    return model


def test_builtin_catalog_loads_without_exposing_disabled_entry() -> None:
    all_entries = load_material_entries(include_disabled=True)
    enabled_entries = load_material_entries()
    assert sum(entry.catalog_id == "builtin_openpbr" for entry in all_entries) == 74
    assert sum(entry.catalog_id == "builtin_openpbr" for entry in enabled_entries) == 73
    assert sum(entry.catalog_id == "wood_furniture" for entry in enabled_entries) == 20
    with pytest.raises(ValidationError, match="unresolved external normal texture"):
        resolve_material_entry("builtin_openpbr", "Copper Brushed")


def test_catalog_material_compiles_to_embedded_openpbr_and_binds_visual(
    tmp_path: Path,
) -> None:
    usd_path = tmp_path / "model.usd"
    usd_path.write_bytes(compile_object_to_usd_bytes(_catalog_model(), asset_root=tmp_path))
    stage = Usd.Stage.Open(str(usd_path))
    assert stage is not None

    material = UsdShade.Material(stage.GetPrimAtPath("/root/Looks/shell_finish"))
    assert material.GetSurfaceOutput("mtlx").HasConnectedSource()
    assert material.GetPrim().GetAttribute("articraft:catalog").Get() == "builtin_openpbr"
    assert material.GetPrim().GetAttribute("articraft:catalogMaterial").Get() == "Aluminum Brushed"
    visual = stage.GetPrimAtPath("/root/body/Visuals/shell")
    bound, _relationship = UsdShade.MaterialBindingAPI(visual).ComputeBoundMaterial()
    assert bound.GetPath() == material.GetPath()


def test_catalog_material_urdf_uses_fallback_color() -> None:
    root = ET.fromstring(compile_object_to_urdf_xml(_catalog_model()))
    material = root.find("material[@name='shell_finish']")
    assert material is not None
    color = material.find("color")
    assert color is not None
    rgba = tuple(float(value) for value in color.attrib["rgba"].split())
    assert len(rgba) == 4
    assert rgba[0] > 0.8


def test_inline_material_remains_the_default_behavior(tmp_path: Path) -> None:
    model = ArticulatedObject(name="inline_box")
    finish = model.material("paint", rgba=(0.2, 0.3, 0.4, 1.0))
    model.part("body").visual(Box((0.2, 0.2, 0.2)), material=finish)
    usd_path = tmp_path / "inline.usd"
    usd_path.write_bytes(compile_object_to_usd_bytes(model, asset_root=tmp_path))
    stage = Usd.Stage.Open(str(usd_path))
    shader = UsdShade.Shader(stage.GetPrimAtPath("/root/Looks/paint/Shader"))
    assert shader.GetIdAttr().Get() == "UsdPreviewSurface"


def test_catalog_material_requires_an_exact_valid_pair() -> None:
    with pytest.raises(ValidationError, match="both catalog and catalog_material"):
        Material("bad", catalog="builtin_openpbr")
    model = ArticulatedObject(name="bad_catalog")
    material = model.material(
        "bad",
        catalog="builtin_openpbr",
        catalog_material="Invented Steel",
    )
    model.part("body").visual(Box((0.1, 0.1, 0.1)), material=material)
    with pytest.raises(ValidationError, match="Unknown catalog material"):
        model.validate()


def test_catalog_material_rejects_undeclared_parameters() -> None:
    model = ArticulatedObject(name="bad_parameters")
    material = model.material(
        "bad",
        catalog="builtin_openpbr",
        catalog_material="Aluminum Brushed",
        parameters={"texture_scale": (2.0, 2.0)},
    )
    model.part("body").visual(Box((0.1, 0.1, 0.1)), material=material)
    with pytest.raises(ValidationError, match="does not support parameters"):
        model.validate()


def _wood_catalog_model() -> ArticulatedObject:
    model = ArticulatedObject(name="wood_box")
    finish = model.material(
        "wood_finish",
        catalog="wood_furniture",
        catalog_material="wood_001",
    )
    model.part("body").visual(Box((0.4, 0.3, 0.2)), material=finish, name="panel")
    return model


def test_texture_catalog_resolves_detail_only_after_selection() -> None:
    entry = resolve_material_entry("wood_furniture", "wood_001")
    assert entry.material_id == "wood_001"
    assert entry.name == "Natural Tan Fine Grain"
    assert set(entry.texture_paths) == {"base_color", "roughness", "normal", "displacement"}
    assert entry.texture_paths["normal"].name == "Wood001_1K-PNG_NormalGL.png"


def test_texture_catalog_compiles_relative_shader_and_package(tmp_path: Path) -> None:
    usd_bytes, assets = compile_object_to_usd_package(_wood_catalog_model(), asset_root=tmp_path)
    assert set(assets) == {
        "textures/Wood001_1K-PNG_Color.png",
        "textures/Wood001_1K-PNG_Displacement.png",
        "textures/Wood001_1K-PNG_NormalGL.png",
        "textures/Wood001_1K-PNG_Roughness.png",
    }

    usd_path = tmp_path / "model.usd"
    usd_path.write_bytes(usd_bytes)
    stage = Usd.Stage.Open(str(usd_path))
    assert stage is not None
    material = UsdShade.Material(stage.GetPrimAtPath("/root/Looks/wood_finish"))
    assert material.GetPrim().GetAttribute("articraft:catalogMaterial").Get() == "wood_001"
    color_texture = UsdShade.Shader(stage.GetPrimAtPath("/root/Looks/wood_finish/base_color"))
    assert color_texture.GetInput("file").Get().path == "textures/Wood001_1K-PNG_Color.png"
    visual = stage.GetPrimAtPath("/root/body/Visuals/panel")
    st = UsdGeom.PrimvarsAPI(visual).GetPrimvar("st")
    assert st and len(st.Get()) == 24


def test_texture_catalog_file_export_writes_portable_texture_folder(tmp_path: Path) -> None:
    usd_path = compile_object_to_usd_file(
        _wood_catalog_model(), tmp_path / "model.usd", asset_root=tmp_path
    )
    assert usd_path.is_file()
    assert sorted(path.name for path in (tmp_path / "textures").glob("*.png")) == [
        "Wood001_1K-PNG_Color.png",
        "Wood001_1K-PNG_Displacement.png",
        "Wood001_1K-PNG_NormalGL.png",
        "Wood001_1K-PNG_Roughness.png",
    ]


def test_optional_texture_catalog_is_omitted_when_assets_are_not_installed(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "catalogs" / "optional_textures"
    catalog.mkdir(parents=True)
    (tmp_path / "registry.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "catalogs:",
                "  - id: optional_textures",
                "    metadata: catalogs/optional_textures/catalog.yaml",
                "    manifest: catalogs/optional_textures/index.yaml",
            ]
        ),
        encoding="utf-8",
    )
    (catalog / "catalog.yaml").write_text(
        "\n".join(
            [
                "id: optional_textures",
                "optional: true",
                "profile: texture_maps",
                "texture_root: missing-assets",
                "detail_pattern: materials/{id}.yaml",
            ]
        ),
        encoding="utf-8",
    )
    (catalog / "index.yaml").write_text("entries: []\n", encoding="utf-8")

    assert load_material_entries(catalog_root=tmp_path) == ()
