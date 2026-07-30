from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "calibration_files.py"
SPEC = importlib.util.spec_from_file_location("calibration_files", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
calibration_files = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(calibration_files)


def valid_calibration() -> dict:
    return {
        "homing_offset": [0] * 7,
        "drive_mode": [0] * 7,
        "start_pos": [100] * 7,
        "end_pos": [200] * 7,
        "calib_mode": ["DEGREE"] * 6 + ["LINEAR"],
        "motor_names": list(calibration_files.MOTOR_NAMES),
    }


class CalibrationFilesTest(unittest.TestCase):
    def test_valid_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "left_follower.json"
            path.write_text(json.dumps(valid_calibration()), encoding="utf-8")
            self.assertEqual(calibration_files.validate_calibration(path), [])

    def test_rejects_wrong_motor_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data = valid_calibration()
            data["motor_names"] = list(reversed(data["motor_names"]))
            path = Path(temp_dir) / "left_follower.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            errors = calibration_files.validate_calibration(path)
            self.assertIn("motor_names does not match the configured SO-101 joint order", errors)

    def test_rejects_missing_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data = valid_calibration()
            del data["homing_offset"]
            path = Path(temp_dir) / "left_follower.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertIn(
                "missing keys: homing_offset",
                calibration_files.validate_calibration(path),
            )

    def test_rejects_invalid_drive_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data = valid_calibration()
            data["drive_mode"][3] = 2
            path = Path(temp_dir) / "left_follower.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertIn(
                "drive_mode values must be 0 or 1",
                calibration_files.validate_calibration(path),
            )

    def test_rejects_damaged_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "left_follower.json"
            path.write_text("{damaged", encoding="utf-8")
            self.assertTrue(
                calibration_files.validate_calibration(path)[0].startswith(
                    "cannot read valid calibration JSON"
                )
            )

    def test_rejects_stationary_range(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data = valid_calibration()
            data["end_pos"][0] = data["start_pos"][0]
            path = Path(temp_dir) / "left_follower.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertIn(
                "start_pos and end_pos must differ for: shoulder_pan",
                calibration_files.validate_calibration(path),
            )

    def test_synthetic_fixtures_require_explicit_opt_in(self) -> None:
        fixture_dir = Path(__file__).parent / "fixtures" / "calibration_synthetic"
        for arm_id in calibration_files.ARM_IDS:
            path = fixture_dir / f"{arm_id}.json"
            self.assertIn(
                "synthetic calibration is test-only; pass allow_synthetic explicitly",
                calibration_files.validate_calibration(path),
            )
            self.assertEqual(
                calibration_files.validate_calibration(path, allow_synthetic=True),
                [],
            )

    def test_synthetic_fixture_role_must_match_filename(self) -> None:
        fixture = (
            Path(__file__).parent
            / "fixtures"
            / "calibration_synthetic"
            / "left_follower.json"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            wrong_name = Path(temp_dir) / "right_follower.json"
            wrong_name.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertIn(
                "synthetic fixture_role must match the calibration filename",
                calibration_files.validate_calibration(
                    wrong_name,
                    allow_synthetic=True,
                ),
            )

    def test_complete_backup_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            calibration_dir = root / "calibration"
            destination_root = root / "backups"
            calibration_dir.mkdir()
            for arm_id in calibration_files.ARM_IDS:
                (calibration_dir / f"{arm_id}.json").write_text(
                    json.dumps(valid_calibration()), encoding="utf-8"
                )

            result = calibration_files.back_up(calibration_dir, destination_root, allow_partial=False)
            self.assertEqual(result, 0)
            backups = list(destination_root.iterdir())
            self.assertEqual(len(backups), 1)
            manifest = json.loads((backups[0] / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["complete"])
            self.assertEqual(len(manifest["files"]), 4)

    def test_partial_backup_requires_explicit_permission(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            calibration_dir = root / "calibration"
            calibration_dir.mkdir()
            (calibration_dir / "left_follower.json").write_text(
                json.dumps(valid_calibration()),
                encoding="utf-8",
            )
            self.assertEqual(
                calibration_files.back_up(
                    calibration_dir,
                    root / "backups",
                    allow_partial=False,
                ),
                2,
            )


if __name__ == "__main__":
    unittest.main()
