#!/usr/bin/env python3

"""Inspect, validate, and back up SO-101 calibration files without accessing hardware."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ARM_IDS = (
    "left_follower",
    "right_follower",
    "left_leader",
    "right_leader",
)
MOTOR_NAMES = (
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "wrist_x",
    "gripper",
)
CALIBRATION_KEYS = (
    "homing_offset",
    "drive_mode",
    "start_pos",
    "end_pos",
    "calib_mode",
    "motor_names",
)
SYNTHETIC_MARKER = "synthetic"


def default_calibration_dir() -> Path:
    workspace_root = Path(__file__).resolve().parents[2]
    return workspace_root / "lerobot-main" / ".cache" / "calibration" / "so101_two"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def validate_calibration(path: Path, allow_synthetic: bool = False) -> list[str]:
    errors: list[str] = []
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return [f"cannot read valid calibration JSON: {error}"]

    missing_keys = [key for key in CALIBRATION_KEYS if key not in data]
    if missing_keys:
        errors.append("missing keys: " + ", ".join(missing_keys))

    if data.get(SYNTHETIC_MARKER) is True and not allow_synthetic:
        errors.append("synthetic calibration is test-only; pass allow_synthetic explicitly")
    if data.get(SYNTHETIC_MARKER) is True:
        fixture_role = data.get("fixture_role")
        if fixture_role not in ARM_IDS:
            errors.append("synthetic fixture_role must name one of the four configured arms")
        elif path.stem != fixture_role:
            errors.append("synthetic fixture_role must match the calibration filename")

    for key in CALIBRATION_KEYS:
        if key in data and (not isinstance(data[key], list) or len(data[key]) != len(MOTOR_NAMES)):
            errors.append(f"{key} must be a list of {len(MOTOR_NAMES)} values")

    if isinstance(data.get("motor_names"), list) and tuple(data["motor_names"]) != MOTOR_NAMES:
        errors.append("motor_names does not match the configured SO-101 joint order")

    if isinstance(data.get("drive_mode"), list) and any(value not in (0, 1) for value in data["drive_mode"]):
        errors.append("drive_mode values must be 0 or 1")

    expected_modes = ("DEGREE",) * 6 + ("LINEAR",)
    if isinstance(data.get("calib_mode"), list) and tuple(data["calib_mode"]) != expected_modes:
        errors.append("calib_mode must be DEGREE for six joints and LINEAR for the gripper")

    for key in ("homing_offset", "start_pos", "end_pos"):
        values = data.get(key)
        if isinstance(values, list) and any(not isinstance(value, (int, float)) for value in values):
            errors.append(f"{key} values must be numeric")

    starts = data.get("start_pos")
    ends = data.get("end_pos")
    if (
        isinstance(starts, list)
        and isinstance(ends, list)
        and len(starts) == len(MOTOR_NAMES)
        and len(ends) == len(MOTOR_NAMES)
        and all(isinstance(value, (int, float)) for value in starts + ends)
    ):
        stationary = [
            MOTOR_NAMES[index]
            for index, (start, end) in enumerate(zip(starts, ends, strict=True))
            if start == end
        ]
        if stationary:
            errors.append("start_pos and end_pos must differ for: " + ", ".join(stationary))

    return errors


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def calibration_paths(calibration_dir: Path) -> dict[str, Path]:
    return {arm_id: calibration_dir / f"{arm_id}.json" for arm_id in ARM_IDS}


def print_status(calibration_dir: Path, allow_synthetic: bool = False) -> int:
    print(f"Calibration directory: {calibration_dir}")
    all_valid = True
    for arm_id, path in calibration_paths(calibration_dir).items():
        if not path.is_file():
            print(f"[MISSING] {arm_id}: {path}")
            all_valid = False
            continue
        errors = validate_calibration(path, allow_synthetic=allow_synthetic)
        if errors:
            print(f"[INVALID] {arm_id}: {path}")
            for error in errors:
                print(f"          - {error}")
            all_valid = False
        else:
            print(f"[OK]      {arm_id}: {path}")
    return 0 if all_valid else 2


def back_up(
    calibration_dir: Path,
    destination_root: Path,
    allow_partial: bool,
    allow_synthetic: bool = False,
) -> int:
    paths = calibration_paths(calibration_dir)
    available = {arm_id: path for arm_id, path in paths.items() if path.is_file()}
    missing = [arm_id for arm_id in ARM_IDS if arm_id not in available]

    if missing and not allow_partial:
        print("Backup refused because calibration files are missing: " + ", ".join(missing), file=sys.stderr)
        print("Use --allow-partial only when an explicitly partial backup is intended.", file=sys.stderr)
        return 2
    if not available:
        print("Backup refused because no calibration files exist.", file=sys.stderr)
        return 2

    invalid = {
        arm_id: validate_calibration(path, allow_synthetic=allow_synthetic)
        for arm_id, path in available.items()
    }
    invalid = {arm_id: errors for arm_id, errors in invalid.items() if errors}
    if invalid:
        for arm_id, errors in invalid.items():
            print(f"Invalid calibration file {arm_id}:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
        return 2

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = destination_root.expanduser().resolve() / timestamp
    destination.mkdir(parents=True, exist_ok=False)

    manifest: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(calibration_dir.resolve()),
        "complete": not missing,
        "synthetic": allow_synthetic,
        "missing_arm_ids": missing,
        "files": {},
    }
    for arm_id, source in available.items():
        target = destination / source.name
        shutil.copy2(source, target)
        manifest["files"][source.name] = {
            "arm_id": arm_id,
            "sha256": file_sha256(target),
        }

    with (destination / "manifest.json").open("w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"Calibration backup created: {destination}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--calibration-dir",
        type=Path,
        default=default_calibration_dir(),
        help="SO-101 calibration directory",
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        help="allow explicitly marked test fixtures; never use this for robot operation",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="report missing or invalid calibration files")
    backup_parser = subparsers.add_parser("backup", help="validate and copy calibration files")
    backup_parser.add_argument(
        "--destination-root",
        type=Path,
        default=Path.home() / "lerobot-calibration-backups",
    )
    backup_parser.add_argument("--allow-partial", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    calibration_dir = args.calibration_dir.expanduser().resolve()
    if args.command == "status":
        return print_status(calibration_dir, allow_synthetic=args.allow_synthetic)
    if args.command == "backup":
        return back_up(
            calibration_dir,
            args.destination_root,
            args.allow_partial,
            allow_synthetic=args.allow_synthetic,
        )
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
