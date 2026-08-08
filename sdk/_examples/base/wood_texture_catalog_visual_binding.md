---
title: 'Wood Texture Catalog Visual Binding'
description: 'A compact cabinet panel using a selectively resolved wood texture catalog material, with an inline material retained for the handle.'
tags:
  - sdk
  - base sdk
  - wood texture
  - catalog material
  - visual material binding
---
# Wood Texture Catalog Visual Binding

Use the exact catalog and material id returned by `find_materials`. The compiler
resolves the detail YAML, builds the USD texture shader, and packages only the
used PNG files under `textures/` beside `model.usd`.

```python
from __future__ import annotations

from sdk import ArticulatedObject, Box, Origin, TestContext, TestReport


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject(name="wood_catalog_panel")
    wood_finish = model.material(
        "wood_finish",
        catalog="wood_furniture",
        catalog_material="wood_001",
    )
    handle_finish = model.material("handle_finish", rgba=(0.12, 0.13, 0.14, 1.0))

    cabinet = model.part("cabinet")
    cabinet.visual(
        Box((0.72, 0.04, 0.48)),
        material=wood_finish,
        name="wood_front_panel",
    )
    cabinet.visual(
        Box((0.18, 0.025, 0.025)),
        origin=Origin(xyz=(0.0, -0.0325, 0.12)),
        material=handle_finish,
        name="handle",
    )
    return model


def run_tests() -> TestReport:
    ctx = TestContext(object_model)
    cabinet = object_model.get_part("cabinet")
    ctx.check("two_visuals", len(cabinet.visuals) == 2, "Expected panel and handle")
    ctx.check(
        "wood_catalog_selected",
        object_model.materials[0].catalog_material == "wood_001",
        "Expected the selected wood catalog id",
    )
    return ctx.report()


object_model = build_object_model()
```
