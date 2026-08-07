from __future__ import annotations

from agent.materials import search_materials
from agent.tools.base import (
    BaseDeclarativeTool,
    BaseToolInvocation,
    ToolParamsModel,
    ToolResult,
    make_tool_schema,
    validate_tool_params,
)


class FindMaterialsParams(ToolParamsModel):
    query: str
    catalog: str | None = None
    limit: int = 5


class FindMaterialsInvocation(BaseToolInvocation[FindMaterialsParams, list[dict[str, object]]]):
    def get_description(self) -> str:
        catalog = f", catalog={self.params.catalog!r}" if self.params.catalog else ""
        return (
            f"Search material catalogs for query={self.params.query!r}{catalog} "
            f"(limit={self.params.limit})"
        )

    async def execute(self) -> ToolResult:
        query = self.params.query.strip()
        if not query:
            return ToolResult(error="query must not be empty")
        if self.params.limit < 1 or self.params.limit > 10:
            return ToolResult(error="limit must be between 1 and 10")
        matches = search_materials(
            query,
            catalog=self.params.catalog,
            limit=self.params.limit,
        )
        return ToolResult(
            output=[
                {
                    "catalog": match.entry.catalog_id,
                    "name": match.entry.name,
                    "description": match.entry.description,
                    "profile": match.entry.profile,
                    "requirements": dict(match.entry.requirements),
                    "match_quality": match.match_quality,
                }
                for match in matches
            ]
        )


class FindMaterialsTool(BaseDeclarativeTool):
    def __init__(self) -> None:
        schema = make_tool_schema(
            name="find_materials",
            description=(
                "Search the installed visual-material catalogs by appearance or intended use. "
                "Returns a small set of valid catalog/name pairs and descriptions. Use the exact "
                "returned identifiers in model.material(...); do not invent catalog names. This "
                "tool does not expose USD shader paths or read the material USD."
            ),
            parameters={
                "query": {
                    "type": "string",
                    "description": (
                        "Short English appearance query, for example 'brushed silver appliance metal' "
                        "or 'clear glass window'."
                    ),
                },
                "catalog": {
                    "type": "string",
                    "description": "Optional exact catalog id used to restrict the search.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum candidates to return, from 1 to 10 (default 5).",
                },
            },
            required=["query"],
        )
        super().__init__("find_materials", schema)

    async def build(self, params: dict) -> FindMaterialsInvocation:
        return FindMaterialsInvocation(validate_tool_params(FindMaterialsParams, params))


__all__ = ["FindMaterialsInvocation", "FindMaterialsParams", "FindMaterialsTool"]
