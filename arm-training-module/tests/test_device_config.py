from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "device_config.py"
SPEC = importlib.util.spec_from_file_location("device_config", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
device_config = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(device_config)


class DeviceConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.map_path = root / "configs" / "so101_devices.json"
        self.rules_path = root / "configs" / "99-so101.rules"

    def test_project_map_and_rules_match(self) -> None:
        data = device_config.load_map(self.map_path)
        self.assertEqual(device_config.validate_map(data), [])
        self.assertEqual(device_config.validate_rules(data, self.rules_path), [])

    def test_duplicate_serial_is_rejected(self) -> None:
        data = device_config.load_map(self.map_path)
        data["arms"][1]["serial"] = data["arms"][0]["serial"]
        self.assertIn(
            "controller serial numbers must be unique",
            device_config.validate_map(data),
        )

    def test_world_writable_rule_is_rejected(self) -> None:
        data = device_config.load_map(self.map_path)
        text = self.rules_path.read_text(encoding="utf-8").replace(
            'MODE="0660"', 'MODE="0777"'
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "99-so101.rules"
            path.write_text(text, encoding="utf-8")
            self.assertIn(
                "udev rules must not grant world read/write/execute access",
                device_config.validate_rules(data, path),
            )


if __name__ == "__main__":
    unittest.main()
