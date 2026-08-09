"""Download a curated AmbientCG texture subset.

The default selection is the 20 Wood assets currently present in the curated
wood_furniture directory, all in 1K-PNG format.
Run with --dry-run before downloading.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
import time
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

DEFAULT_IDS = (
    "Wood001,Wood003,Wood006,Wood014,Wood016,Wood017,Wood021,Wood026,"
    "Wood027,Wood030,Wood031,Wood036,Wood041,Wood046,Wood052,Wood057,"
    "Wood058,Wood062,Wood067,Wood091B"
).split(",")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        default=root / "scripts" / "ambientCG_downloads_csv.csv",
        help="AmbientCG downloads CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=root / "assets" / "textures" / "wood_furniture",
        help="Directory containing one folder per assetId.",
    )
    parser.add_argument(
        "--asset-id",
        action="append",
        dest="asset_ids",
        help="Asset id to download; repeat this option to override the default 20 ids.",
    )
    parser.add_argument("--attribute", default="1K-PNG", help="Exact downloadAttribute to select.")
    parser.add_argument("--dry-run", action="store_true", help="List selected assets without downloading.")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds.")
    parser.add_argument("--retries", type=int, default=3, help="Retries per asset.")
    return parser.parse_args()


def read_rows(csv_path: Path, asset_ids: set[str], attribute: str) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    selected = [
        row
        for row in rows
        if row.get("assetId") in asset_ids and row.get("downloadAttribute") == attribute
    ]
    by_id = {row["assetId"]: row for row in selected}
    missing = sorted(asset_ids - set(by_id))
    if missing:
        raise RuntimeError(f"Missing {attribute} rows for asset ids: {', '.join(missing)}")
    return [by_id[asset_id] for asset_id in sorted(asset_ids)]


def _safe_extract(data: bytes, destination: Path) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise RuntimeError(f"Corrupt member in archive: {bad_member}")
        destination_resolved = destination.resolve()
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if target != destination_resolved and destination_resolved not in target.parents:
                raise RuntimeError(f"Unsafe archive path: {member.filename}")
        archive.extractall(destination)


def download_bytes(url: str, timeout: float) -> bytes:
    request = Request(url, headers={"User-Agent": "Articraft-AmbientCG-Downloader/1.0"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL comes from the checked CSV.
        chunks: list[bytes] = []
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks)


def has_pngs(directory: Path) -> bool:
    return any(directory.glob("*.png"))


def main() -> int:
    args = parse_args()
    asset_ids = set(args.asset_ids or DEFAULT_IDS)
    csv_path = args.csv if args.csv.is_absolute() else repo_root() / args.csv
    output_dir = args.output_dir if args.output_dir.is_absolute() else repo_root() / args.output_dir
    if not csv_path.is_file():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 2

    try:
        rows = read_rows(csv_path, asset_ids, args.attribute)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    total_bytes = sum(int(row.get("size") or 0) for row in rows)
    print(f"selected={len(rows)} attribute={args.attribute} compressed_bytes={total_bytes}")
    for row in rows:
        print(f"{row['assetId']} {row['size']} {row['downloadLink']}")
    if args.dry_run:
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir.parent / "wood_furniture_manifest.csv"
    manifest_rows: list[dict[str, str]] = []
    for row in rows:
        asset_id = row["assetId"]
        destination = output_dir / asset_id
        destination.mkdir(parents=True, exist_ok=True)
        status = "skipped_existing"
        error = ""
        if not has_pngs(destination):
            status = "failed"
            for attempt in range(1, args.retries + 1):
                try:
                    print(f"downloading {asset_id} ({attempt}/{args.retries})")
                    data = download_bytes(row["downloadLink"], args.timeout)
                    _safe_extract(data, destination)
                    if not has_pngs(destination):
                        raise RuntimeError("archive extracted successfully but contains no PNG files")
                    status = "downloaded"
                    break
                except Exception as exc:  # pragma: no cover - network behavior is environment-dependent.
                    error = str(exc)
                    if attempt < args.retries:
                        time.sleep(2.0 * attempt)
            if status == "failed":
                print(f"failed {asset_id}: {error}", file=sys.stderr)
        manifest_rows.append(
            {
                "assetId": asset_id,
                "downloadAttribute": row["downloadAttribute"],
                "downloadLink": row["downloadLink"],
                "rawLink": row.get("rawLink", ""),
                "compressedBytes": row.get("size", ""),
                "status": status,
                "error": error,
            }
        )

    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)
    failed = [row for row in manifest_rows if row["status"] == "failed"]
    print(f"manifest={manifest_path} failed={len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
