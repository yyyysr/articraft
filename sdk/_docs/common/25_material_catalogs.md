# Material Catalogs

Use a material catalog when a named surface finish materially improves the
object's appearance. Catalogs are optional: ordinary `rgba` and `texture`
materials remain supported and are often the right choice for simple parts,
prototypes, small details, or renderer-independent output.

## Select Without Reading The Library

Do not inspect material USD files and do not guess catalog material names. Call
`find_materials` with a short English appearance/use query. It returns a small set of
valid `catalog`, `id`, `name`, and `description` fields. Selection reads only
this lightweight semantic index; texture paths and shader details remain hidden.

```text
find_materials(query="brushed silver metal for an appliance shell", limit=5)
```

Choose the closest returned candidate. If none is appropriate, use an inline
`rgba` material instead of forcing a poor catalog match.

## Bind A Catalog Material

The model-local name remains under the author's control. Use the exact catalog
and material `id` returned by `find_materials`.

```python
shell_finish = model.material(
    "shell_finish",
    catalog="builtin_openpbr",
    catalog_material="Aluminum Brushed",
)

shell.visual(shell_geometry, material=shell_finish, name="outer_shell")
```

`model.material("name", ...)` is the canonical registration form. The
compatibility form `model.material(Material("name", ...))` is accepted, but do
not combine a `Material` object with separate material keyword arguments.

Texture-backed catalogs use the same API:

```python
wood_finish = model.material(
    "wood_finish",
    catalog="wood_furniture",
    catalog_material="wood_001",
)
cabinet.visual(Box((0.8, 0.4, 0.02)), material=wood_finish, name="wood_panel")
```

Texture catalogs backed by locally installed assets are optional. If their
texture root is absent, they are omitted from `find_materials` without affecting
the built-in catalog. Install the catalog assets before using its ids.

Material assignment remains per visual. Reuse one registered material for
visuals that need the same finish, and use separate local materials when future
texture scale or orientation parameters must differ.

## Inline Materials Remain First-Class

```python
indicator_red = model.material("indicator_red", rgba=(0.75, 0.03, 0.02, 1.0))
button.visual(button_geometry, material=indicator_red, name="indicator")
```

Do not replace a clear, adequate inline color merely because a catalog exists.
Catalog selection is an opt-in visual enhancement, not a compile requirement.

## Export Behavior

- USD preserves or builds the selected catalog shader graph and binds it to the visual.
- Texture-backed materials are packaged beside `model.usd` under `textures/`;
  USD references them with portable relative paths.
- URDF cannot represent OpenPBR. It receives an approximate fallback color.
- An inline `rgba` on a catalog material explicitly overrides the URDF fallback
  while USD still uses the catalog material.
- `texture` cannot be combined with a catalog material. Textures owned by a
  catalog are compiler-managed resources.

## Textured Materials And UVs

Texture-backed materials require UV coordinates. `Box` visuals receive a
face-varying `st` layout automatically during USD export. Other primitives and
meshes must already provide a supported UV path before using a texture-backed
catalog. Do not invent texture parameters; use only parameters returned or
documented for that material.

## Common Errors

- `Unknown catalog material`: call `find_materials` and use an exact result.
- `material is unavailable`: select another candidate; the entry has a broken
  or unsupported dependency.
- `does not support parameters`: remove the parameter or choose a material that
  declares it.
- Poor catalog match: keep or create an inline material instead.
