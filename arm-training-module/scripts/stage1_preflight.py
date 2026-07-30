#!/usr/bin/env python3

"""Read-only first-stage readiness report; this script never drives a motor."""

from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def module_root() -> Path:
    return Path(__file__).resolve().parents[1]


def command_version(command: list[str]) -> str:
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError:
        return "unavailable"
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0] if output else f"exit {result.returncode}"


def import_version(name: str) -> str:
    try:
        module = __import__(name)
    except Exception as error:
        return f"unavailable ({error})"
    return str(getattr(module, "__version__", "installed"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    root = module_root()
    lerobot_root = root.parent / "lerobot-main"
    aliases = ["/dev/f_left", "/dev/f_right", "/dev/l_left", "/dev/l_right"]
    cameras = sorted(glob.glob("/dev/video*"))
    report = {
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "executable": sys.executable,
            "torch": import_version("torch"),
            "lerobot": import_version("lerobot"),
            "cuda_available": False,
            "ros2": command_version(["ros2", "--help"]),
        },
        "paths": {
            "module_root": str(root),
            "module_accessible": root.is_dir(),
            "lerobot_root": str(lerobot_root),
            "lerobot_accessible": lerobot_root.is_dir(),
        },
        "devices": {
            "aliases": {
                alias: str(Path(alias).resolve()) if Path(alias).exists() else None
                for alias in aliases
            },
            "video_devices": cameras,
        },
        "safety": {
            "read_only": True,
            "motors_commanded": False,
            "physical_stop_verified": False,
        },
    }
    try:
        import torch

        report["environment"]["cuda_available"] = torch.cuda.is_available()
    except Exception:
        pass

    checks = {
        "Python environment": report["environment"]["python"] != "unavailable",
        "LeRobot import": not report["environment"]["lerobot"].startswith("unavailable"),
        "Project paths": report["paths"]["module_accessible"] and report["paths"]["lerobot_accessible"],
        "Four stable motor aliases": all(report["devices"]["aliases"].values()),
        "At least one camera": bool(cameras),
        "Physical stop process": report["safety"]["physical_stop_verified"],
    }
    for name, passed in checks.items():
        print(f"[{'PASS' if passed else 'BLOCKED'}] {name}")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Report saved: {args.json_output}")

    # Missing hardware is an expected blocked state, represented by exit code 2.
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
