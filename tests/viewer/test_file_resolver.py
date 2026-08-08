from __future__ import annotations

from pathlib import Path

from storage.repo import StorageRepo
from viewer.api.file_resolver import ViewerFileResolver, should_attempt_materialize_for_record_path


class _Store:
    def __init__(self, repo: StorageRepo) -> None:
        self.repo = repo

    def materialize_record_assets(self, record_id: str, **kwargs: object) -> object:
        raise AssertionError("Existing texture should resolve without recompilation")


def test_record_texture_resolves_from_materialization_directory(tmp_path: Path) -> None:
    repo = StorageRepo(tmp_path, data_root=tmp_path / "data")
    record_id = "rec_texture_test"
    repo.layout.record_dir(record_id).mkdir(parents=True)
    texture = repo.layout.record_materialization_textures_dir(record_id) / "Wood001_Color.png"
    texture.parent.mkdir(parents=True)
    texture.write_bytes(b"png")

    root, target = ViewerFileResolver(_Store(repo)).resolve_record_target(
        record_id, "textures/Wood001_Color.png"
    )

    assert root == repo.layout.record_materialization_dir(record_id).resolve()
    assert target == texture.resolve()
    assert should_attempt_materialize_for_record_path("textures/Wood001_Color.png")
