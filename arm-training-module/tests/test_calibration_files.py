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


if __name__ == "__main__":
    unittest.main()
