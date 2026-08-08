from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml
from pxr import Gf, Sdf, Usd, UsdShade

from .errors import ValidationError

_DEFAULT_CATALOG_ROOT = Path(__file__).resolve().parents[2] / "_materials"


@dataclass(frozen=True)
class MaterialCatalogEntry:
    catalog_id: str
    material_id: str
    name: str
    description: str
    binding: str | None
    library_path: Path | None
    profile: str
    texture_paths: Mapping[str, Path] = field(default_factory=dict)
    texture_dir: str | None = None
    usd_path: Path | None = None
    tags: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    requirements: Mapping[str, Any] = field(default_factory=dict)
    parameters: Mapping[str, Any] = field(default_factory=dict)
    disabled_reason: str | None = None

    @property
    def key(self) -> tuple[str, str]:
        return self.catalog_id, self.name


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValidationError(f"Material catalog file not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValidationError(f"Material catalog file must contain a mapping: {path}")
    return payload


def _relative_file(base: Path, value: object, *, field_name: str) -> Path:
    text = str(value or "").strip()
    if not text:
        raise ValidationError(f"{field_name} is required")
    candidate = (base / text).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError as exc:
        raise ValidationError(f"{field_name} must stay inside its catalog package") from exc
    return candidate


def _relative_asset(base: Path, value: object, *, field_name: str) -> Path:
    text = str(value or "").strip()
    if not text:
        raise ValidationError(f"{field_name} is required")
    candidate = (base / text).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must stay inside its material asset directory"
        ) from exc
    if not candidate.is_file():
        raise ValidationError(f"{field_name} not found: {candidate}")
    return candidate


def _string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, (list, tuple)):
        raise ValidationError("Material tags and aliases must be strings or lists of strings")
    return tuple(str(item).strip() for item in values if str(item).strip())


@lru_cache(maxsize=4)
def _load_material_entries_cached(catalog_root_text: str) -> tuple[MaterialCatalogEntry, ...]:
    catalog_root = Path(catalog_root_text)
    registry = _load_yaml(catalog_root / "registry.yaml")
    raw_catalogs = registry.get("catalogs")
    if not isinstance(raw_catalogs, list):
        raise ValidationError("Material registry 'catalogs' must be a list")

    entries: list[MaterialCatalogEntry] = []
    seen_catalogs: set[str] = set()
    for raw_catalog in raw_catalogs:
        if not isinstance(raw_catalog, dict):
            raise ValidationError("Material registry entries must be mappings")
        catalog_id = str(raw_catalog.get("id") or "").strip()
        if not catalog_id or catalog_id in seen_catalogs:
            raise ValidationError(f"Invalid or duplicate material catalog id: {catalog_id!r}")
        seen_catalogs.add(catalog_id)

        metadata_path = _relative_file(
            catalog_root,
            raw_catalog.get("metadata"),
            field_name=f"catalog {catalog_id!r} metadata",
        )
        manifest_path = _relative_file(
            catalog_root,
            raw_catalog.get("manifest"),
            field_name=f"catalog {catalog_id!r} manifest",
        )
        metadata = _load_yaml(metadata_path)
        manifest = _load_yaml(manifest_path)
        if str(metadata.get("id") or "") != catalog_id:
            raise ValidationError(f"Material catalog metadata id does not match {catalog_id!r}")

        library_value = metadata.get("library") or manifest.get("library_path")
        library_path: Path | None = None
        if library_value:
            library_path = _relative_file(
                metadata_path.parent,
                library_value,
                field_name=f"catalog {catalog_id!r} library",
            )
            if not library_path.is_file():
                raise ValidationError(f"Material catalog library not found: {library_path}")

        detail_pattern = str(metadata.get("detail_pattern") or "").strip()
        texture_root_value = str(metadata.get("texture_root") or "").strip()
        texture_root = (
            (metadata_path.parent / texture_root_value).resolve() if texture_root_value else None
        )
        if detail_pattern and (texture_root is None or not texture_root.is_dir()):
            if bool(metadata.get("optional")):
                continue
            raise ValidationError(f"Material catalog texture root not found: {texture_root}")
        if not library_path and not detail_pattern:
            raise ValidationError(
                f"Material catalog {catalog_id!r} must define library or detail_pattern"
            )

        disabled: dict[str, str] = {}
        for item in metadata.get("disabled_entries") or []:
            if not isinstance(item, dict) or not str(item.get("name") or "").strip():
                raise ValidationError(f"Invalid disabled entry in catalog {catalog_id!r}")
            disabled[str(item["name"]).strip()] = str(item.get("reason") or "disabled")

        raw_entries = manifest.get("entries")
        if not isinstance(raw_entries, list):
            raise ValidationError(f"Material catalog {catalog_id!r} entries must be a list")
        seen_names: set[str] = set()
        seen_ids: set[str] = set()
        for raw_entry in raw_entries:
            if not isinstance(raw_entry, dict):
                raise ValidationError(f"Material catalog {catalog_id!r} entry must be a mapping")
            name = str(raw_entry.get("name") or "").strip()
            material_id = str(raw_entry.get("id") or name).strip()
            binding = str(raw_entry.get("binding") or "").strip() or None
            if not name or not material_id or name in seen_names or material_id in seen_ids:
                raise ValidationError(
                    f"Invalid or duplicate material entry {name!r} in catalog {catalog_id!r}"
                )
            if binding and not Sdf.Path(binding).IsAbsolutePath():
                raise ValidationError(f"Material binding must be an absolute USD path: {binding}")
            if bool(binding) != bool(library_path):
                raise ValidationError(
                    f"Material entry {catalog_id!r}/{name!r} must match its catalog library"
                )

            texture_paths: dict[str, Path] = {}
            texture_dir: str | None = None
            usd_path: Path | None = None
            if detail_pattern:
                try:
                    detail_relative = detail_pattern.format(id=material_id)
                except (KeyError, ValueError) as exc:
                    raise ValidationError(
                        f"Invalid detail_pattern for catalog {catalog_id!r}"
                    ) from exc
                detail_path = _relative_file(
                    metadata_path.parent,
                    detail_relative,
                    field_name=f"material {catalog_id!r}/{material_id!r} detail",
                )
                detail = _load_yaml(detail_path)
                if str(detail.get("id") or "").strip() != material_id:
                    raise ValidationError(
                        f"Material detail id does not match {catalog_id!r}/{material_id!r}"
                    )
                texture_dir = str(detail.get("dir") or "").strip()
                asset_dir = (texture_root / texture_dir).resolve()  # type: ignore[operator]
                try:
                    asset_dir.relative_to(texture_root)  # type: ignore[arg-type]
                except ValueError as exc:
                    raise ValidationError(
                        f"Material directory must stay inside texture_root: {texture_dir}"
                    ) from exc
                raw_maps = detail.get("maps")
                if not isinstance(raw_maps, dict) or "base_color" not in raw_maps:
                    raise ValidationError(
                        f"Material detail {catalog_id!r}/{material_id!r} requires maps.base_color"
                    )
                supported_maps = {"base_color", "roughness", "normal", "displacement"}
                unsupported_maps = sorted(set(raw_maps) - supported_maps)
                if unsupported_maps:
                    raise ValidationError(
                        f"Unsupported texture maps for {catalog_id!r}/{material_id!r}: "
                        f"{', '.join(unsupported_maps)}"
                    )
                texture_paths = {
                    str(map_name): _relative_asset(
                        asset_dir,
                        map_file,
                        field_name=f"material {catalog_id!r}/{material_id!r} map {map_name!r}",
                    )
                    for map_name, map_file in raw_maps.items()
                }
                if detail.get("usd"):
                    usd_path = _relative_asset(
                        asset_dir,
                        detail["usd"],
                        field_name=f"material {catalog_id!r}/{material_id!r} usd",
                    )
            seen_names.add(name)
            seen_ids.add(material_id)
            entries.append(
                MaterialCatalogEntry(
                    catalog_id=catalog_id,
                    material_id=material_id,
                    name=name,
                    description=str(raw_entry.get("description") or "").strip(),
                    binding=binding,
                    library_path=library_path,
                    profile=str(metadata.get("profile") or "").strip(),
                    texture_paths=texture_paths,
                    texture_dir=texture_dir,
                    usd_path=usd_path,
                    tags=_string_tuple(raw_entry.get("tags")),
                    aliases=_string_tuple(raw_entry.get("aliases")),
                    requirements=dict(raw_entry.get("requirements") or {}),
                    parameters=dict(raw_entry.get("parameters") or {}),
                    disabled_reason=disabled.get(name),
                )
            )
    return tuple(entries)


def load_material_entries(
    *,
    catalog_root: str | Path | None = None,
    include_disabled: bool = False,
) -> tuple[MaterialCatalogEntry, ...]:
    root = Path(catalog_root or _DEFAULT_CATALOG_ROOT).resolve()
    entries = _load_material_entries_cached(str(root))
    if include_disabled:
        return entries
    return tuple(entry for entry in entries if entry.disabled_reason is None)


def resolve_material_entry(
    catalog_id: str,
    material_name: str,
    *,
    catalog_root: str | Path | None = None,
) -> MaterialCatalogEntry:
    catalog_key = str(catalog_id).strip()
    material_key = str(material_name).strip()
    for entry in load_material_entries(catalog_root=catalog_root, include_disabled=True):
        if entry.catalog_id == catalog_key and material_key in {entry.name, entry.material_id}:
            if entry.disabled_reason:
                raise ValidationError(
                    f"Catalog material {catalog_key}/{material_key} is unavailable: "
                    f"{entry.disabled_reason}"
                )
            return entry
    raise ValidationError(f"Unknown catalog material: {catalog_key}/{material_key}")


def validate_material_parameters(
    entry: MaterialCatalogEntry,
    parameters: Mapping[str, object] | None,
) -> None:
    supplied = dict(parameters or {})
    unsupported = sorted(set(supplied) - set(entry.parameters))
    if unsupported:
        raise ValidationError(
            f"Catalog material {entry.catalog_id}/{entry.name} does not support parameters: "
            f"{', '.join(unsupported)}"
        )


def copy_catalog_material(
    stage: Usd.Stage,
    entry: MaterialCatalogEntry,
    target_path: Sdf.Path,
) -> UsdShade.Material:
    if entry.texture_paths:
        return _define_texture_material(stage, entry, target_path)
    if entry.library_path is None or entry.binding is None:
        raise ValidationError(
            f"Catalog material has no usable implementation: {entry.catalog_id}/{entry.name}"
        )
    source_layer = Sdf.Layer.FindOrOpen(str(entry.library_path))
    if source_layer is None or source_layer.GetPrimAtPath(entry.binding) is None:
        raise ValidationError(
            f"Catalog material binding not found: {entry.catalog_id}/{entry.name} -> {entry.binding}"
        )
    if not Sdf.CopySpec(source_layer, Sdf.Path(entry.binding), stage.GetRootLayer(), target_path):
        raise ValidationError(f"Failed to copy catalog material {entry.catalog_id}/{entry.name}")
    material = UsdShade.Material.Get(stage, target_path)
    if not material or not material.GetPrim().IsValid():
        raise ValidationError(
            f"Copied catalog material is invalid: {entry.catalog_id}/{entry.name}"
        )
    material.GetPrim().CreateAttribute("articraft:catalog", Sdf.ValueTypeNames.String).Set(
        entry.catalog_id
    )
    material.GetPrim().CreateAttribute("articraft:catalogMaterial", Sdf.ValueTypeNames.String).Set(
        entry.name
    )
    return material


def _texture_asset_path(entry: MaterialCatalogEntry, source: Path) -> str:
    return f"textures/{source.name}"


def _define_texture_material(
    stage: Usd.Stage,
    entry: MaterialCatalogEntry,
    target_path: Sdf.Path,
) -> UsdShade.Material:
    material = UsdShade.Material.Define(stage, target_path)
    shader = UsdShade.Shader.Define(stage, target_path.AppendChild("Shader"))
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.55)
    shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

    texcoord = UsdShade.Shader.Define(stage, target_path.AppendChild("TextureCoordinateReader"))
    texcoord.CreateIdAttr("UsdPrimvarReader_float2")
    texcoord.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    texcoord.CreateOutput("result", Sdf.ValueTypeNames.Float2)

    map_specs = {
        "base_color": ("diffuseColor", "rgb", Sdf.ValueTypeNames.Color3f, "sRGB"),
        "roughness": ("roughness", "r", Sdf.ValueTypeNames.Float, "raw"),
        "normal": ("normal", "rgb", Sdf.ValueTypeNames.Normal3f, "raw"),
        "displacement": ("displacement", "r", Sdf.ValueTypeNames.Float, "raw"),
    }
    for map_name, source in entry.texture_paths.items():
        input_name, output_name, value_type, color_space = map_specs[map_name]
        texture = UsdShade.Shader.Define(stage, target_path.AppendChild(map_name))
        texture.CreateIdAttr("UsdUVTexture")
        texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(
            Sdf.AssetPath(_texture_asset_path(entry, source))
        )
        texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set(color_space)
        texture.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
        texture.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
        texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
            texcoord.ConnectableAPI(), "result"
        )
        if map_name == "normal":
            texture.CreateInput("bias", Sdf.ValueTypeNames.Float4).Set((-1.0, -1.0, -1.0, 0.0))
            texture.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set((2.0, 2.0, 2.0, 1.0))
        texture.CreateOutput(output_name, value_type)
        shader.CreateInput(input_name, value_type).ConnectToSource(
            texture.ConnectableAPI(), output_name
        )

    material.GetPrim().CreateAttribute("articraft:catalog", Sdf.ValueTypeNames.String).Set(
        entry.catalog_id
    )
    material.GetPrim().CreateAttribute("articraft:catalogMaterial", Sdf.ValueTypeNames.String).Set(
        entry.material_id
    )
    return material


def catalog_texture_assets(entry: MaterialCatalogEntry) -> dict[str, Path]:
    return {_texture_asset_path(entry, source): source for source in entry.texture_paths.values()}


@lru_cache(maxsize=256)
def _catalog_fallback_rgba_cached(
    library_path: str,
    binding: str,
) -> tuple[float, float, float, float]:
    stage = Usd.Stage.Open(library_path)
    if stage is None:
        return (0.8, 0.8, 0.8, 1.0)
    material = UsdShade.Material(stage.GetPrimAtPath(binding))
    if not material or not material.GetPrim().IsValid():
        return (0.8, 0.8, 0.8, 1.0)
    color_value = material.GetInput("base_color").Get() if material.GetInput("base_color") else None
    opacity_value = (
        material.GetInput("geometry_opacity").Get()
        if material.GetInput("geometry_opacity")
        else 1.0
    )
    transmission = (
        float(material.GetInput("transmission_weight").Get() or 0.0)
        if material.GetInput("transmission_weight")
        else 0.0
    )
    if isinstance(color_value, (Gf.Vec3f, Gf.Vec3d, Gf.Vec3h)):
        color = tuple(float(channel) for channel in color_value)
    else:
        color = (0.8, 0.8, 0.8)
    opacity = float(opacity_value if opacity_value is not None else 1.0)
    if transmission > 0.5:
        opacity = min(opacity, 0.35)
        if max(color) < 0.05:
            color = (0.7, 0.8, 0.85)
    return color[0], color[1], color[2], opacity


def catalog_fallback_rgba(entry: MaterialCatalogEntry) -> tuple[float, float, float, float]:
    if "base_color" in entry.texture_paths:
        return (0.55, 0.4, 0.25, 1.0)
    if entry.library_path is None or entry.binding is None:
        return (0.8, 0.8, 0.8, 1.0)
    return _catalog_fallback_rgba_cached(str(entry.library_path), entry.binding)


__all__ = [
    "MaterialCatalogEntry",
    "catalog_texture_assets",
    "catalog_fallback_rgba",
    "copy_catalog_material",
    "load_material_entries",
    "resolve_material_entry",
    "validate_material_parameters",
]
