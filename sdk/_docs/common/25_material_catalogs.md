# Material Catalogs

Use a material catalog when a named surface finish materially improves the
object's appearance. Catalogs are optional: ordinary `rgba` and `texture`
materials remain supported and are often the right choice for simple parts,
prototypes, small details, or renderer-independent output.

## Select Without Reading The Library

Do not inspect material USD files and do not guess catalog material names. Call
`find_materials` with a short English appearance/use query. It returns a small set of
valid `catalog` and `name` pairs with semantic descriptions.

```text
find_materials(query="brushed silver metal for an appliance shell", limit=5)
```

Choose the closest returned candidate. If none is appropriate, use an inline
`rgba` material instead of forcing a poor catalog match.

## Bind A Catalog Material

The model-local name remains under the author's control. The catalog pair must
match a `find_materials` result exactly.

```python
shell_finish = model.material(
    "shell_finish",
    catalog="builtin_openpbr",
    catalog_material="Aluminum Brushed",
)

shell.visual(shell_geometry, material=shell_finish, name="outer_shell")
```

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

- USD preserves the selected catalog shader graph and binds it to the visual.
- URDF cannot represent OpenPBR. It receives an approximate fallback color.
- An inline `rgba` on a catalog material explicitly overrides the URDF fallback
  while USD still uses the catalog material.
- `texture` cannot be combined with a catalog material. Textures owned by a
  catalog are compiler-managed resources.

## Textured Materials And UVs

Future texture-backed catalogs may declare `requirements.uv: true` and expose
validated parameters such as texture scale. Do not invent parameter names.
Use only parameters returned or documented for that material. A visual without
the required UV coordinates must use another material until suitable UVs are
available. UV validation and parameter application are added together with the
first texture-backed catalog; the current built-in catalog exposes neither.

## Common Errors

- `Unknown catalog material`: call `find_materials` and use an exact result.
- `material is unavailable`: select another candidate; the entry has a broken
  or unsupported dependency.
- `does not support parameters`: remove the parameter or choose a material that
  declares it.
- Poor catalog match: keep or create an inline material instead.
