<tools>
- Available tools: `read_file`, `apply_patch`, `compile_model`, `probe_model`, `find_examples`, and `find_materials`.
- `read_file` is a JSON tool for reading exact virtual workspace file text.
- `apply_patch` accepts a Codex-style patch in the required JSON `input` string.
- `compile_model` runs compile + QC and returns structured `<compile_signals>`.
- `probe_model` is read-only Python inspection; no file writes, no object mutation, and no subprocesses.
- `find_examples` searches curated SDK examples for patterns. Adapt results against current SDK docs and do not mechanically copy example code; entries marked `[weakly relevant]` are inspiration-only.
- `find_materials` searches installed visual-material descriptions and returns exact catalog/name pairs. Use it only when a catalog finish adds value; ordinary inline materials remain valid.
- Read exact current file text with `read_file(path="model.py")` before you patch.
- Prefer several small `apply_patch` edits over one giant patch or full-file rewrite.
- Modify the existing `model.py` rather than assuming a blank start.
</tools>
