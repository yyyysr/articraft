from __future__ import annotations

import asyncio
import re
from pathlib import Path

from agent.tools.read_file import ReadFileTool
from agent.workspace_docs import (
    build_virtual_workspace,
    load_sdk_docs_bundle,
    load_sdk_docs_reference,
)


def test_load_sdk_docs_bundle_mounts_router_and_default_refs() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    bundle = load_sdk_docs_bundle(repo_root, sdk_package="sdk")

    assert bundle.router.virtual_path == "docs/sdk/references/quickstart.md"
    assert bundle.default_read_virtual_paths() == ("docs/sdk/references/quickstart.md",)
    assert bundle.resolve("docs/sdk/references/capability-index.md").disk_path.name == (
        "05_capability_index.md"
    )
    assert bundle.resolve("docs/sdk/references/material-catalogs.md").disk_path.name == (
        "25_material_catalogs.md"
    )
    assert "materials_libs_v2" not in bundle.read_text("docs/sdk/references/quickstart.md")
    preloaded = load_sdk_docs_reference(repo_root, sdk_package="sdk")
    assert "Aluminum Brushed" not in preloaded
    assert "materials_libs_v2" not in preloaded
    assert "docs/sdk/references/assets.md" in bundle.files_by_path
    assert "docs/sdk/references/modeling-strategy.md" in bundle.files_by_path
    assert "docs/sdk/references/physics-parameters.md" in bundle.files_by_path
    assert "docs/sdk/references/geometry/mesh-geometry.md" in bundle.files_by_path
    assert "docs/sdk/references/geometry/mesh-api.md" in bundle.files_by_path
    assert "docs/sdk/references/geometry/section-lofts-api.md" in bundle.files_by_path
    assert "docs/sdk/references/articulation/details.md" in bundle.files_by_path
    assert "docs/sdk/references/geometry/wires-and-frames.md" in bundle.files_by_path
    assert "docs/sdk/references/testing/details.md" in bundle.files_by_path
    assert "docs/sdk/references/cadquery/overview.md" in bundle.files_by_path
    assert "docs/sdk/references/cadquery/helpers.md" in bundle.files_by_path
    assert "docs/sdk/references/geometry/panels-and-grilles.md" not in bundle.files_by_path
    assert "docs/sdk/references/geometry/knobs-and-controls.md" not in bundle.files_by_path
    assert "docs/sdk/references/cadquery/gears.md" not in bundle.files_by_path

    assert bundle.resolve("docs/sdk/references/core-types.md").disk_path.parent.name == ("generic")
    assert bundle.resolve("docs/sdk/references/articulated-object.md").disk_path.parent.name == (
        "generic"
    )
    assert bundle.resolve("docs/sdk/references/physics-parameters.md").disk_path.parent.name == (
        "generic"
    )
    assert bundle.resolve("docs/sdk/references/testing.md").disk_path.parent.name == "generic"
    assert bundle.resolve("docs/sdk/references/modeling-strategy.md").disk_path.name == (
        "modeling_strategy.md"
    )
    assert (
        bundle.resolve("docs/sdk/references/cadquery/helpers.md").disk_path.name == "35_cadquery.md"
    )
    assert bundle.resolve("docs/sdk/references/geometry/mesh-api.md").disk_path.name == (
        "40_mesh_geometry.md"
    )
    assert (
        bundle.resolve("docs/sdk/references/geometry/section-lofts-api.md").disk_path.name
        == "46_section_lofts.md"
    )
    assert bundle.resolve("docs/sdk/references/articulation/details.md").disk_path.name == (
        "30_articulated_object.md"
    )
    assert bundle.resolve("docs/sdk/references/geometry/wires-and-frames.md").disk_path.name == (
        "45_wires.md"
    )
    assert bundle.resolve("docs/sdk/references/testing/details.md").disk_path.name == (
        "80_testing.md"
    )


def test_mounted_sdk_document_links_resolve() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    bundle = load_sdk_docs_bundle(repo_root, sdk_package="sdk")
    link_pattern = re.compile(r"docs/sdk/(?:references|guides)/[A-Za-z0-9_./-]+\.md")

    for source in bundle.files_by_path.values():
        for virtual_path in link_pattern.findall(source.read_text()):
            assert virtual_path in bundle.files_by_path, (
                f"{source.virtual_path} links to unmounted {virtual_path}"
            )


def test_sdk_entrypoint_and_strategy_preserve_working_set_contract() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    bundle = load_sdk_docs_bundle(repo_root, sdk_package="sdk")
    link_pattern = re.compile(r"docs/sdk/(?:references|guides)/[A-Za-z0-9_./-]+\.md")

    quickstart = bundle.read_text("docs/sdk/references/quickstart.md")
    assert set(link_pattern.findall(quickstart)) == {"docs/sdk/references/capability-index.md"}

    capability_index = bundle.read_text("docs/sdk/references/capability-index.md")
    for relationship in ("Coupled", "Alternative", "Detail", "Diagnostic"):
        assert relationship in capability_index
    assert "docs/sdk/references/modeling-strategy.md" in capability_index
    assert "docs/sdk/references/cadquery/helpers.md" in capability_index
    assert "docs/sdk/references/geometry/mesh-api.md" in capability_index
    assert "docs/sdk/references/geometry/section-lofts-api.md" in capability_index
    assert "docs/sdk/references/articulation/details.md" in capability_index
    assert "docs/sdk/references/geometry/wires-and-frames.md" in capability_index
    assert "docs/sdk/references/testing/details.md" in capability_index
    assert "## Stop Condition" in capability_index

    strategy = bundle.read_text("docs/sdk/references/modeling-strategy.md")
    assert "## Co-design Parts And Motion" in strategy
    assert "## Choose A Primary Geometry Representation" in strategy
    assert "## Stop Reading And Edit" in strategy


def test_virtual_workspace_resolves_model_and_docs_paths(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    model_path = tmp_path / "model.py"
    model_path.write_text("line1\nline2\n", encoding="utf-8")

    workspace = build_virtual_workspace(
        repo_root,
        model_file_path=model_path,
        sdk_package="sdk",
    )

    model_file = workspace.resolve("model.py")
    docs_file = workspace.resolve("docs/sdk/references/quickstart.md")

    assert model_file.disk_path == model_path
    assert docs_file.disk_path is not None
    assert docs_file.disk_path.name == "00_quickstart.md"


def test_read_file_tool_reads_virtual_model_and_docs_paths(tmp_path: Path) -> None:
    async def _run() -> tuple[str, str]:
        repo_root = Path(__file__).resolve().parents[2]
        model_path = tmp_path / "model.py"
        model_path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
        workspace = build_virtual_workspace(
            repo_root,
            model_file_path=model_path,
            sdk_package="sdk",
        )

        tool = ReadFileTool()

        model_invocation = await tool.build({"path": "model.py", "offset": 2, "limit": 2})
        model_invocation.bind_virtual_workspace(workspace)
        model_result = await model_invocation.execute()
        assert model_result.error is None

        docs_invocation = await tool.build(
            {"path": "docs/sdk/references/quickstart.md", "offset": 1, "limit": 120}
        )
        docs_invocation.bind_virtual_workspace(workspace)
        docs_result = await docs_invocation.execute()
        assert docs_result.error is None

        return str(model_result.output), str(docs_result.output)

    model_output, docs_output = asyncio.run(_run())

    assert model_output == "L2: beta\nL3: gamma"
    assert "Workspace Contract" in docs_output
    assert "Import public authoring APIs from `sdk`" in docs_output
    assert "capability-index.md" in docs_output
    assert "geometry/knobs-and-controls.md" not in docs_output


def test_read_file_tool_rejects_unknown_virtual_path(tmp_path: Path) -> None:
    async def _run() -> str | None:
        repo_root = Path(__file__).resolve().parents[2]
        model_path = tmp_path / "model.py"
        model_path.write_text("alpha\n", encoding="utf-8")
        workspace = build_virtual_workspace(
            repo_root,
            model_file_path=model_path,
            sdk_package="sdk",
        )

        tool = ReadFileTool()
        invocation = await tool.build({"path": "docs/nope.md"})
        invocation.bind_virtual_workspace(workspace)
        result = await invocation.execute()
        return result.error

    error = asyncio.run(_run())

    assert error == "File docs/nope.md not found"


def test_read_file_tool_reads_full_file_when_offset_and_limit_missing(tmp_path: Path) -> None:
    async def _run() -> str:
        repo_root = Path(__file__).resolve().parents[2]
        model_path = tmp_path / "model.py"
        model_path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
        workspace = build_virtual_workspace(
            repo_root,
            model_file_path=model_path,
            sdk_package="sdk",
        )

        tool = ReadFileTool()
        invocation = await tool.build({"path": "model.py"})
        invocation.bind_virtual_workspace(workspace)
        result = await invocation.execute()
        assert result.error is None
        return str(result.output)

    model_output = asyncio.run(_run())
    assert model_output == "L1: alpha\nL2: beta\nL3: gamma"


def test_read_file_tool_reads_from_offset_to_eof_when_limit_missing(tmp_path: Path) -> None:
    async def _run() -> str:
        repo_root = Path(__file__).resolve().parents[2]
        model_path = tmp_path / "model.py"
        model_path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
        workspace = build_virtual_workspace(
            repo_root,
            model_file_path=model_path,
            sdk_package="sdk",
        )

        tool = ReadFileTool()
        invocation = await tool.build({"path": "model.py", "offset": 2})
        invocation.bind_virtual_workspace(workspace)
        result = await invocation.execute()
        assert result.error is None
        return str(result.output)

    model_output = asyncio.run(_run())
    assert model_output == "L2: beta\nL3: gamma"


def test_read_file_tool_reads_markdown_section_with_live_line_numbers(tmp_path: Path) -> None:
    async def _run() -> str:
        repo_root = Path(__file__).resolve().parents[2]
        model_path = tmp_path / "model.py"
        model_path.write_text("alpha\n", encoding="utf-8")
        workspace = build_virtual_workspace(
            repo_root,
            model_file_path=model_path,
            sdk_package="sdk",
        )
        tool = ReadFileTool()
        invocation = await tool.build(
            {
                "path": "docs/sdk/references/geometry/mesh-api.md",
                "section": "Profile and Shell Helpers",
            }
        )
        invocation.bind_virtual_workspace(workspace)
        result = await invocation.execute()
        assert result.error is None
        return str(result.output)

    output = asyncio.run(_run())
    assert "## Profile and Shell Helpers" in output
    assert "## Panel Openings" not in output
    assert "L" in output
    assert "sample_catmull_rom_spline_2d" in output


def test_read_file_tool_rejects_section_with_paging(tmp_path: Path) -> None:
    async def _run() -> str | None:
        repo_root = Path(__file__).resolve().parents[2]
        model_path = tmp_path / "model.py"
        model_path.write_text("alpha\n", encoding="utf-8")
        workspace = build_virtual_workspace(
            repo_root,
            model_file_path=model_path,
            sdk_package="sdk",
        )
        tool = ReadFileTool()
        invocation = await tool.build(
            {
                "path": "docs/sdk/references/geometry/mesh-api.md",
                "section": "Profile and Shell Helpers",
                "limit": 10,
            }
        )
        invocation.bind_virtual_workspace(workspace)
        result = await invocation.execute()
        return result.error

    assert asyncio.run(_run()) == "section cannot be combined with offset or limit"
