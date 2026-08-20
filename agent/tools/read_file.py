"""
ReadFile tool - Read an exact file from the virtual workspace with line numbers.
"""

from __future__ import annotations

import re

import aiofiles

from agent.tools.base import (
    BaseDeclarativeTool,
    BoundFileToolInvocation,
    ToolParamsModel,
    ToolResult,
    make_tool_schema,
    validate_tool_params,
)
from agent.workspace_docs import VirtualWorkspace


class ReadFileParams(ToolParamsModel):
    """Parameters for read_file tool."""

    path: str
    offset: int | None = None
    limit: int | None = None
    section: str | None = None


class ReadFileInvocation(BoundFileToolInvocation[ReadFileParams, str]):
    """Invocation for reading the target file."""

    def __init__(
        self,
        params: ReadFileParams,
        *,
        offset_provided: bool = False,
        limit_provided: bool = False,
        section_provided: bool = False,
    ):
        super().__init__(params)
        self.virtual_workspace: VirtualWorkspace | None = None
        self.offset_provided = offset_provided
        self.limit_provided = limit_provided
        self.section_provided = section_provided

    def bind_virtual_workspace(self, workspace: VirtualWorkspace) -> None:
        self.virtual_workspace = workspace

    def get_description(self) -> str:
        return (
            f"Read virtual file {self.params.path!r} "
            f"(offset={self.params.offset}, limit={self.params.limit})"
        )

    async def execute(self) -> ToolResult:
        try:
            if self.virtual_workspace is None:
                return ToolResult(error="virtual workspace is not available")

            resolved = self.virtual_workspace.resolve(self.params.path)
            if resolved.content is not None:
                full_code = resolved.content
            elif resolved.disk_path is not None:
                async with aiofiles.open(resolved.disk_path, mode="r", encoding="utf-8") as f:
                    full_code = await f.read()
            else:
                return ToolResult(error=f"Unable to resolve {self.params.path}")

            lines = full_code.splitlines()
            line_number_base = 0
            if self.section_provided and self.params.section is None:
                return ToolResult(error="section must not be null")
            if self.params.section is not None and (self.offset_provided or self.limit_provided):
                return ToolResult(error="section cannot be combined with offset or limit")

            if self.params.section is not None:
                lines, section_error, line_number_base = _select_markdown_section(
                    lines, self.params.section
                )
                if section_error is not None:
                    return ToolResult(error=section_error)

            offset = self.params.offset or 1
            if self.offset_provided and self.params.offset is None:
                return ToolResult(error="offset must be >= 1")
            if self.offset_provided and self.params.offset < 1:
                return ToolResult(error="offset must be >= 1")
            if self.limit_provided and self.params.limit is None:
                return ToolResult(error="limit must be >= 1")
            if self.limit_provided and self.params.limit < 1:
                return ToolResult(error="limit must be >= 1")

            if not lines:
                if self.offset_provided and offset > 1:
                    return ToolResult(error="offset exceeds file length")
                return ToolResult(output="")

            if self.offset_provided and self.params.offset > len(lines):
                return ToolResult(error="offset exceeds file length")

            start = offset - 1
            if self.limit_provided:
                end = min(len(lines), start + self.params.limit)
            else:
                end = len(lines)
            formatted = [
                f"L{line_number_base + idx}: {lines[idx - 1]}" for idx in range(start + 1, end + 1)
            ]
            return ToolResult(output="\n".join(formatted))
        except FileNotFoundError:
            return ToolResult(error=f"File {self.params.path} not found")
        except ValueError as exc:
            return ToolResult(error=str(exc))
        except Exception as exc:
            return ToolResult(error=f"Error reading file: {str(exc)}")


class ReadFileTool(BaseDeclarativeTool):
    """Tool for reading the current file with line numbers."""

    def __init__(self) -> None:
        description = (
            "Read an exact file from the virtual workspace with 1-indexed line numbers.\n\n"
            'Use `path="model.py"` for the full model artifact script. '
            "Use `path` under `docs/` for read-only SDK guidance and references.\n\n"
            "Returned lines are formatted as `L{line_number}: ...`.\n\n"
            "Use `offset` to choose the first line (1-indexed) and `limit` to cap the total number "
            "of returned lines. Omit both for a full-file read. Omit `limit` with an explicit `offset` "
            "to read from that offset to EOF. For Markdown references, use `section` to read one "
            "heading section without depending on fixed line numbers; do not combine `section` with "
            "`offset` or `limit`."
        )
        schema = make_tool_schema(
            name="read_file",
            description=description,
            parameters={
                "path": {
                    "type": "string",
                    "description": (
                        "Virtual workspace path to read. Use `model.py` for the model "
                        "file and `docs/...` for mounted read-only SDK docs."
                    ),
                },
                "offset": {
                    "type": "integer",
                    "description": ("Optional. 1-indexed line to start from. Omit for `1`."),
                },
                "limit": {
                    "type": "integer",
                    "description": ("Optional. Maximum number of lines to return. Omit for EOF."),
                },
                "section": {
                    "type": "string",
                    "description": (
                        "Optional Markdown heading text, such as `Profiles And Curves`. "
                        "Reads that heading through the next heading of the same or higher level."
                    ),
                },
            },
            required=["path"],
        )
        super().__init__("read_file", schema)

    async def build(self, params: dict) -> ReadFileInvocation:
        validated = validate_tool_params(ReadFileParams, params)
        invocation = ReadFileInvocation(
            validated,
            offset_provided="offset" in params and params["offset"] is not None,
            limit_provided="limit" in params and params["limit"] is not None,
            section_provided="section" in params and params["section"] is not None,
        )
        return invocation


def _select_markdown_section(lines: list[str], requested: str) -> tuple[list[str], str | None, int]:
    target = " ".join(str(requested).strip().lstrip("#").split()).casefold()
    if not target:
        return [], "section must not be empty", 0

    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match is None:
            continue
        title = " ".join(match.group(2).split())
        headings.append((index, len(match.group(1)), title))

    matches = [heading for heading in headings if heading[2].casefold() == target]
    if not matches:
        available = ", ".join(title for _, _, title in headings)
        return [], f"Unknown section {requested!r}. Available sections: {available}", 0
    if len(matches) > 1:
        return [], f"Section {requested!r} is ambiguous; use a more specific heading", 0

    start, level, _ = matches[0]
    end = len(lines)
    for candidate, candidate_level, _ in headings:
        if candidate > start and candidate_level <= level:
            end = candidate
            break
    return lines[start:end], None, start
