from __future__ import annotations

import asyncio

from agent.materials import search_materials
from agent.tools.find_materials import FindMaterialsTool


def test_material_search_finds_semantic_openpbr_candidates() -> None:
    matches = search_materials("brushed silver appliance metal", limit=3)
    assert matches
    assert matches[0].entry.name == "Aluminum Brushed"
    assert all(match.entry.name != "Copper Brushed" for match in matches)


def test_find_materials_tool_returns_semantics_without_usd_internals() -> None:
    async def run() -> object:
        invocation = await FindMaterialsTool().build({"query": "clear glass window", "limit": 3})
        return await invocation.execute()

    result = asyncio.run(run())
    assert result.error is None
    assert isinstance(result.output, list) and result.output
    first = result.output[0]
    assert set(first) == {
        "catalog",
        "name",
        "description",
        "profile",
        "requirements",
        "match_quality",
    }
    assert "binding" not in first
    assert "library_path" not in first
