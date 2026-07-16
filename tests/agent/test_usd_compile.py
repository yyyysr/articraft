from __future__ import annotations

from pathlib import Path

from pxr import Usd

from agent.compiler import compile_urdf_report, compile_urdf_report_maybe_timeout


def _write_model(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "from sdk import ArticulatedObject, Box, Material",
                "",
                "object_model = ArticulatedObject(name='usd_compile_test')",
                "base = object_model.part('base')",
                "base.visual(",
                "    Box((1.0, 2.0, 3.0)),",
                "    material=Material('red', rgba=(0.8, 0.1, 0.1, 1.0)),",
                "    name='body',",
                ")",
            ]
        ),
        encoding="utf-8",
    )


def _assert_valid_usd(payload: bytes | None, tmp_path: Path, name: str) -> None:
    assert payload is not None
    assert payload.startswith(b"PXR-USDC")
    path = tmp_path / name
    path.write_bytes(payload)
    stage = Usd.Stage.Open(str(path))
    assert stage is not None
    assert stage.GetPrimAtPath("/root/base/Visuals/body").IsValid()


def test_compile_urdf_report_also_returns_usd_bytes(tmp_path: Path) -> None:
    script_path = tmp_path / "model.py"
    _write_model(script_path)

    report = compile_urdf_report(script_path, run_checks=False)

    assert "<robot" in report.urdf_xml
    _assert_valid_usd(report.usd_bytes, tmp_path, "direct.usd")


def test_compile_worker_transports_usd_bytes(tmp_path: Path) -> None:
    script_path = tmp_path / "model.py"
    _write_model(script_path)

    report = compile_urdf_report_maybe_timeout(script_path, run_checks=False)

    _assert_valid_usd(report.usd_bytes, tmp_path, "worker.usd")


def test_visual_target_usd_omits_derived_collision_geometry(tmp_path: Path) -> None:
    script_path = tmp_path / "model.py"
    _write_model(script_path)

    report = compile_urdf_report(script_path, run_checks=False, target="visual")

    assert report.usd_bytes is not None
    usd_path = tmp_path / "visual.usd"
    usd_path.write_bytes(report.usd_bytes)
    stage = Usd.Stage.Open(str(usd_path))
    assert stage is not None
    assert stage.GetPrimAtPath("/root/base/Collisions").GetChildren() == []
