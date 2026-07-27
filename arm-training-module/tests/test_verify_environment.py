from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_environment.py"
SPEC = importlib.util.spec_from_file_location("verify_environment", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
verify_environment = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verify_environment
SPEC.loader.exec_module(verify_environment)


class VerifyEnvironmentTest(unittest.TestCase):
    def test_report_distinguishes_software_from_hardware(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            module = workspace / "arm-training-module"
            module.mkdir()
            (workspace / "lerobot-main").mkdir()
            with mock.patch.object(verify_environment, "DEPENDENCIES", ()):
                report = verify_environment.build_report(module)
            self.assertTrue(report["result"]["software_ready"])
            self.assertEqual(report["result"]["hardware_status"], "not_checked")

    def test_missing_lerobot_path_is_software_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            module = Path(temp_dir) / "arm-training-module"
            module.mkdir()
            with mock.patch.object(verify_environment, "DEPENDENCIES", ()):
                report = verify_environment.build_report(module)
            self.assertFalse(report["result"]["software_ready"])
            self.assertIn(
                "lerobot",
                report["result"]["software_failures"]["missing_paths"],
            )

    def test_runtime_directories_can_be_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            module = workspace / "arm-training-module"
            module.mkdir()
            (workspace / "lerobot-main").mkdir()
            with mock.patch.object(verify_environment, "DEPENDENCIES", ()):
                report = verify_environment.build_report(
                    module,
                    create_runtime_dirs=True,
                )
            self.assertTrue(report["paths"]["datasets"]["is_directory"])
            self.assertTrue(report["paths"]["outputs"]["is_directory"])


if __name__ == "__main__":
    unittest.main()
