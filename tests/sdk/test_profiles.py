from __future__ import annotations

import pytest

from sdk._profiles import get_sdk_profile

_REMOVED_PACKAGE = "_".join(("sdk", "hybrid"))


def test_sdk_docs_profile_exposes_compact_production_references() -> None:
    base = get_sdk_profile("sdk")

    base_docs = {path.as_posix() for path in base.docs_full}

    assert "sdk/_docs/common/00_quickstart.md" in base_docs
    assert "sdk/_docs/common/05_capability_index.md" in base_docs
    assert "sdk/_docs/generic/modeling_strategy.md" in base_docs
    assert "sdk/_docs/generic/core_types.md" in base_docs
    assert "sdk/_docs/generic/articulated_object.md" in base_docs
    assert "sdk/_docs/generic/physics_parameters.md" in base_docs
    assert "sdk/_docs/generic/mesh_geometry.md" in base_docs
    assert "sdk/_docs/generic/section_lofts.md" in base_docs
    assert "sdk/_docs/generic/cadquery.md" in base_docs
    assert "sdk/_docs/generic/testing.md" in base_docs
    assert "sdk/_docs/common/40_assets.md" in base_docs
    assert "sdk/_docs/common/30_articulated_object.md" in base_docs
    assert "sdk/_docs/common/80_testing.md" in base_docs
    assert "sdk/_docs/base/40_mesh_geometry.md" in base_docs
    assert "sdk/_docs/base/45_wires.md" in base_docs
    assert "sdk/_docs/base/46_section_lofts.md" in base_docs
    assert "sdk/_docs/cadquery/35_cadquery.md" in base_docs
    assert "sdk/_docs/cadquery/39c_cadquery_api_ref.md" in base_docs

    assert "sdk/_docs/common/20_core_types.md" not in base_docs
    assert "sdk/_docs/common/35_physics_parameters.md" not in base_docs
    assert "sdk/_docs/base/41_panels_and_grilles.md" not in base_docs
    assert "sdk/_docs/base/44_knobs_and_controls.md" not in base_docs
    assert "sdk/_docs/base/48_wheels_and_tires.md" not in base_docs
    assert "sdk/_docs/cadquery/36_cadquery_primer.md" not in base_docs
    assert "sdk/_docs/cadquery/39d_cadquery_gears.md" not in base_docs

    assert tuple(path.as_posix() for path in base.docs_core) == (
        "sdk/_docs/common/00_quickstart.md",
        "sdk/_docs/common/05_capability_index.md",
        "sdk/_docs/generic/modeling_strategy.md",
    )


def test_sdk_docs_profile_rejects_removed_legacy_sdk_package() -> None:
    with pytest.raises(ValueError, match="Unsupported SDK package"):
        get_sdk_profile(_REMOVED_PACKAGE)
