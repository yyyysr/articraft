---
title: 'Catalog Material Visual Bindings'
description: 'A compact appliance panel showing optional catalog materials bound independently to metal, glass, and plastic visuals while retaining inline materials as a valid fallback.'
tags:
  - sdk
  - base sdk
  - catalog material
  - visual material binding
  - openpbr
  - appliance panel
---
# Catalog Material Visual Bindings

This example focuses on material ownership rather than complex geometry. Each
finish has a model-local name, while its catalog selection uses an exact pair
returned by `find_materials`.

```python
from __future__ import annotations

from sdk import ArticulatedObject, Box, Origin, TestContext, TestReport


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject(name="catalog_material_panel")
    shell_finish = model.material(
        "shell_finish",
        catalog="builtin_openpbr",
        catalog_material="Aluminum Brushed",
    )
    window_finish = model.material(
        "window_finish",
        catalog="builtin_openpbr",
        catalog_material="Glass Clear",
    )
    button_finish = model.material(
        "button_finish",
        catalog="builtin_openpbr",
        catalog_material="Plastic Black",
    )
    indicator_finish = model.material(
        "indicator_finish",
        rgba=(0.75, 0.03, 0.02, 1.0),
    )

    panel = model.part("panel")
    panel.visual(Box((0.42, 0.08, 0.24)), material=shell_finish, name="metal_shell")
    panel.visual(
        Box((0.24, 0.006, 0.12)),
        origin=Origin(xyz=(-0.04, -0.043, 0.01)),
        material=window_finish,
        name="glass_window",
    )
    panel.visual(
        Box((0.055, 0.014, 0.055)),
        origin=Origin(xyz=(0.155, -0.047, 0.02)),
        material=button_finish,
        name="plastic_button",
    )
    panel.visual(
        Box((0.018, 0.008, 0.008)),
        origin=Origin(xyz=(0.155, -0.055, 0.07)),
        material=indicator_finish,
        name="inline_color_indicator",
    )
    return model


def run_tests() -> TestReport:
    ctx = TestContext(object_model)
    panel = object_model.get_part("panel")
    ctx.check("four_visuals", len(panel.visuals) == 4, "Expected four material regions")
    ctx.check(
        "catalog_is_optional",
        object_model.materials[-1].catalog is None,
        "Inline materials must remain supported",
    )
    return ctx.report()


object_model = build_object_model()
```
