from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from articraft.values import ProviderName, normalize_provider_name

OPENAI_DESIGNER_PROMPT_NAME = "designer_system_prompt_openai.txt"
CODEX_CLI_DESIGNER_PROMPT_NAME = "designer_system_prompt_codex_cli.txt"
GEMINI_DESIGNER_PROMPT_NAME = "designer_system_prompt_gemini.txt"
OPENROUTER_DESIGNER_PROMPT_NAME = "designer_system_prompt_openrouter.txt"
ANTHROPIC_DESIGNER_PROMPT_NAME = "designer_system_prompt_anthropic.txt"
DEEPSEEK_DESIGNER_PROMPT_NAME = "designer_system_prompt_deepseek.txt"


@dataclass(slots=True, frozen=True)
class SdkProfile:
    package_name: str
    scaffold_path: Path
    docs_full: tuple[Path, ...]
    docs_core: tuple[Path, ...]
    openai_prompt_name: str
    codex_cli_prompt_name: str
    gemini_prompt_name: str
    openrouter_prompt_name: str
    anthropic_prompt_name: str
    deepseek_prompt_name: str

    def docs_for_mode(self, docs_mode: str) -> tuple[Path, ...]:
        if docs_mode == "full":
            return self.docs_full
        if docs_mode == "core":
            return self.docs_core
        if docs_mode == "none":
            return ()
        raise ValueError(f"Unsupported SDK docs mode: {docs_mode!r}")

    def prompt_name_for_provider(self, provider: str | None) -> str | None:
        if not (provider or "").strip():
            return None
        try:
            provider_norm = normalize_provider_name(provider)
        except ValueError:
            return None
        if provider_norm is ProviderName.OPENAI:
            return self.openai_prompt_name
        if provider_norm is ProviderName.CODEX_CLI:
            return self.codex_cli_prompt_name
        if provider_norm is ProviderName.DASHSCOPE:
            return self.openrouter_prompt_name
        if provider_norm is ProviderName.GEMINI:
            return self.gemini_prompt_name
        if provider_norm is ProviderName.OPENROUTER:
            return self.openrouter_prompt_name
        if provider_norm is ProviderName.ANTHROPIC:
            return self.anthropic_prompt_name
        if provider_norm is ProviderName.DEEPSEEK:
            return self.deepseek_prompt_name
        return None


_AGENT_ENTRY_DOCS = (
    Path("sdk/_docs/common/00_quickstart.md"),
    Path("sdk/_docs/common/05_capability_index.md"),
    Path("sdk/_docs/generic/modeling_strategy.md"),
)

_AGENT_REFERENCE_DOCS = (
    Path("sdk/_docs/generic/core_types.md"),
    Path("sdk/_docs/generic/articulated_object.md"),
    Path("sdk/_docs/generic/assembly_patterns.md"),
    Path("sdk/_docs/generic/mesh_geometry.md"),
    Path("sdk/_docs/generic/section_lofts.md"),
    Path("sdk/_docs/generic/cadquery.md"),
    Path("sdk/_docs/generic/physics_parameters.md"),
    Path("sdk/_docs/generic/testing.md"),
    Path("sdk/_docs/common/10_errors.md"),
    Path("sdk/_docs/common/25_material_catalogs.md"),
    Path("sdk/_docs/common/40_assets.md"),
    Path("sdk/_docs/common/50_placement.md"),
    Path("sdk/_docs/common/70_probe_tooling.md"),
    Path("sdk/_docs/common/30_articulated_object.md"),
    Path("sdk/_docs/common/80_testing.md"),
    Path("sdk/_docs/base/40_mesh_geometry.md"),
    Path("sdk/_docs/base/45_wires.md"),
    Path("sdk/_docs/base/46_section_lofts.md"),
    Path("sdk/_docs/base/49_hinges.md"),
    Path("sdk/_docs/cadquery/35_cadquery.md"),
    Path("sdk/_docs/cadquery/39c_cadquery_api_ref.md"),
)

_SDK_PACKAGE_ALIASES = {
    "": "sdk",
    "base": "sdk",
    "sdk": "sdk",
}


SDK_PROFILES: dict[str, SdkProfile] = {
    "sdk": SdkProfile(
        package_name="sdk",
        scaffold_path=Path("scaffold.py"),
        docs_full=(
            *_AGENT_ENTRY_DOCS,
            *_AGENT_REFERENCE_DOCS,
        ),
        docs_core=_AGENT_ENTRY_DOCS,
        openai_prompt_name=OPENAI_DESIGNER_PROMPT_NAME,
        codex_cli_prompt_name=CODEX_CLI_DESIGNER_PROMPT_NAME,
        gemini_prompt_name=GEMINI_DESIGNER_PROMPT_NAME,
        openrouter_prompt_name=OPENROUTER_DESIGNER_PROMPT_NAME,
        anthropic_prompt_name=ANTHROPIC_DESIGNER_PROMPT_NAME,
        deepseek_prompt_name=DEEPSEEK_DESIGNER_PROMPT_NAME,
    ),
}


SUPPORTED_SDK_PACKAGES = frozenset(SDK_PROFILES)


def get_sdk_profile(package_name: str) -> SdkProfile:
    normalized = _SDK_PACKAGE_ALIASES.get(str(package_name or "").strip().lower())
    if normalized is None:
        raise ValueError(
            f"Unsupported SDK package: {package_name!r}. "
            f"Expected one of {sorted(SUPPORTED_SDK_PACKAGES)!r}."
        )
    try:
        return SDK_PROFILES[normalized]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported SDK package: {package_name!r}. "
            f"Expected one of {sorted(SUPPORTED_SDK_PACKAGES)!r}."
        ) from exc
