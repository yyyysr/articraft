from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

from agent.record_persistence import create_draft_record
from cli.common import add_data_root_argument, storage_repo_from_args
from storage.identifiers import validate_category_slug, validate_record_id
from storage.library_manifest import upsert_record
from storage.revisions import (
    active_inputs_dir,
    active_model_path,
    active_revision_id,
    sha256_file,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="articraft external")
    add_data_root_argument(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create an external-agent draft record.")
    init.add_argument("prompt")
    init.add_argument("--agent", choices=("codex", "claude-code", "cursor"), default="codex")
    init.add_argument("--record-id", default=None)
    init.add_argument("--label", default=None)
    init.add_argument("--tag", dest="tags", action="append", default=None)

    fork = subparsers.add_parser("fork", help="Fork a record for external-agent editing.")
    fork.add_argument("record")
    fork.add_argument("prompt")
    fork.add_argument("--agent", choices=("codex", "claude-code", "cursor"), default=None)
    fork.add_argument("--record-id", default=None)
    fork.add_argument("--label", default=None)
    fork.add_argument("--tag", dest="tags", action="append", default=None)

    finalize = subparsers.add_parser("finalize", help="Finalize a local external-agent record.")
    finalize.add_argument("record")
    finalize.add_argument("--category-slug", default=None)

    subparsers.add_parser("categories", help="List local categories.")
    return parser


def _resolve_record_id(repo, record_ref: str) -> str:
    candidate = Path(record_ref).expanduser()
    if candidate.exists():
        resolved = candidate.resolve()
        records_root = repo.layout.records_root.resolve()
        try:
            relative = resolved.relative_to(records_root)
        except ValueError as exc:
            raise ValueError(f"Record path must be inside {records_root}") from exc
        if len(relative.parts) != 1 or not resolved.is_dir():
            raise ValueError(f"Record path must point to a direct child of {records_root}")
        return validate_record_id(relative.parts[0])
    return validate_record_id(record_ref)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    repo = storage_repo_from_args(args)
    repo.ensure_layout()

    if args.command == "init":
        try:
            record_dir = create_draft_record(
                repo_root=args.repo_root,
                data_root=repo.layout.data_root,
                prompt_text=args.prompt,
                record_id=args.record_id,
                label=args.label,
                tags=list(args.tags or []),
                external_agent=args.agent,
            )
        except Exception as exc:
            print(str(exc))
            return 1
        print(f"record_id={record_dir.name}")
        print(f"record_dir={record_dir}")
        return 0

    if args.command == "fork":
        try:
            parent_record_id = _resolve_record_id(repo, args.record)
            parent = repo.read_json(repo.layout.record_metadata_path(parent_record_id))
            if not isinstance(parent, dict):
                raise ValueError(f"Record not found: {parent_record_id}")
            parent_revision_id = active_revision_id(repo, parent_record_id, record=parent)
            parent_model = active_model_path(repo, parent_record_id, record=parent)
            if not parent_model.is_file():
                raise ValueError(f"Missing parent model.py: {parent_model}")

            creator = parent.get("creator") if isinstance(parent.get("creator"), dict) else {}
            inherited_agent = str(creator.get("agent") or "").strip()
            external_agent = args.agent or inherited_agent or "codex"
            parent_tags = parent.get("tags")
            tags = (
                list(args.tags)
                if args.tags is not None
                else [str(tag) for tag in parent_tags]
                if isinstance(parent_tags, list)
                else []
            )
            label = args.label if args.label is not None else parent.get("label")
            record_dir = create_draft_record(
                repo_root=args.repo_root,
                data_root=repo.layout.data_root,
                prompt_text=args.prompt,
                record_id=args.record_id,
                label=str(label) if label is not None else None,
                tags=tags,
                external_agent=external_agent,
            )
            child_record_id = record_dir.name
            child = repo.read_json(repo.layout.record_metadata_path(child_record_id))
            if not isinstance(child, dict):
                raise ValueError(f"Failed to create child record: {child_record_id}")
            child_revision_id = active_revision_id(repo, child_record_id, record=child)
            child_model = active_model_path(repo, child_record_id, record=child)
            shutil.copy2(parent_model, child_model)

            parent_inputs = active_inputs_dir(repo, parent_record_id, record=parent)
            child_inputs = active_inputs_dir(repo, child_record_id, record=child)
            if parent_inputs.is_dir():
                shutil.copytree(parent_inputs, child_inputs, dirs_exist_ok=True)

            model_digest = sha256_file(child_model)
            origin = (
                parent.get("lineage", {}).get("origin_record_id")
                if isinstance(parent.get("lineage"), dict)
                else None
            )
            child["category_slug"] = parent.get("category_slug")
            child["lineage"] = {
                "origin_record_id": str(origin or parent_record_id),
                "parent_record_id": parent_record_id,
                "parent_revision_id": parent_revision_id,
                "edit_mode": "copy",
            }
            if isinstance(child.get("hashes"), dict):
                child["hashes"]["model_py_sha256"] = model_digest
            repo.write_json(repo.layout.record_metadata_path(child_record_id), child)

            revision_path = repo.layout.record_revision_metadata_path(
                child_record_id, child_revision_id
            )
            revision = repo.read_json(revision_path)
            if not isinstance(revision, dict):
                raise ValueError(f"Missing child revision metadata: {revision_path}")
            revision["parent"] = {
                "record_id": parent_record_id,
                "revision_id": parent_revision_id,
            }
            revision["seed"] = {
                "record_id": parent_record_id,
                "revision_id": parent_revision_id,
                "artifact": "model.py",
            }
            if isinstance(revision.get("hashes"), dict):
                revision["hashes"]["model_py_sha256"] = model_digest
            repo.write_json(revision_path, revision)
            upsert_record(repo, child_record_id)
        except Exception as exc:
            print(str(exc))
            return 1
        print(f"record_id={child_record_id}")
        print(f"record_dir={record_dir}")
        print(f"parent_record_id={parent_record_id}")
        return 0

    if args.command == "finalize":
        try:
            record_id = _resolve_record_id(repo, args.record)
            record_path = repo.layout.record_metadata_path(record_id)
            record = repo.read_json(record_path)
            if not isinstance(record, dict):
                raise ValueError(f"Record not found: {record_id}")
            revision_id = active_revision_id(repo, record_id, record=record)
            model_path = active_model_path(repo, record_id, record=record)
            model_digest = sha256_file(model_path)
            if model_digest is None:
                raise ValueError(f"Missing active model.py: {model_path}")
            hashes = record.get("hashes")
            if not isinstance(hashes, dict):
                hashes = {}
                record["hashes"] = hashes
            hashes["model_py_sha256"] = model_digest
            record["updated_at"] = (
                datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            )
            if args.category_slug:
                record["category_slug"] = validate_category_slug(args.category_slug)
            repo.write_json(record_path, record)

            revision_path = repo.layout.record_revision_metadata_path(record_id, revision_id)
            revision = repo.read_json(revision_path)
            if isinstance(revision, dict):
                revision_hashes = revision.get("hashes")
                if not isinstance(revision_hashes, dict):
                    revision_hashes = {}
                    revision["hashes"] = revision_hashes
                revision_hashes["model_py_sha256"] = model_digest
                repo.write_json(revision_path, revision)
            upsert_record(repo, record_id)
        except Exception as exc:
            print(str(exc))
            return 1
        print(f"finalized record_id={record_id}")
        return 0

    if args.command == "categories":
        root = repo.layout.categories_root
        if root.exists():
            for path in sorted(item for item in root.iterdir() if item.is_dir()):
                print(path.name)
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
