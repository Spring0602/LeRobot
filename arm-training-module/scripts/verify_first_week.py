#!/usr/bin/env python3

"""Run the complete software-only first-week acceptance workflow."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_step(name: str, command: list[str], cwd: Path) -> bool:
    print(f"\n=== {name} ===", flush=True)
    result = subprocess.run(command, cwd=cwd, check=False)
    if result.returncode == 0:
        print(f"[PASS] {name}")
        return True
    print(f"[FAIL] {name}: exit code {result.returncode}")
    return False


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    python = sys.executable
    steps = (
        (
            "Environment",
            [python, "scripts/verify_environment.py"],
        ),
        (
            "Device configuration",
            [python, "scripts/device_config.py"],
        ),
        (
            "Synthetic calibration fixtures",
            [
                python,
                "scripts/calibration_files.py",
                "--calibration-dir",
                "tests/fixtures/calibration_synthetic",
                "--allow-synthetic",
                "status",
            ],
        ),
        (
            "Synthetic action safety",
            [
                python,
                "scripts/action_safety.py",
                "--mode",
                "synthetic",
                "--action",
                "[0,0,0,0,0,0,0,0,0,0,0,0,0,0]",
            ],
        ),
        (
            "Unit tests",
            [python, "-m", "unittest", "discover", "-s", "tests", "-v"],
        ),
    )
    passed = [run_step(name, command, root) for name, command in steps]
    print("\n=== First-week result ===")
    if all(passed):
        print("[PASS] All software-only first-week checks passed.")
        print("[BLOCKED] Real hardware limits, calibration, ports, and cameras remain unverified.")
        return 0
    print("[FAIL] One or more software checks failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
