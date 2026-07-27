#!/usr/bin/env python3

"""Verify the software environment and emit an optional machine-readable report."""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Dependency:
    distribution: str
    module: str
    required: bool = True


DEPENDENCIES = (
    Dependency("lerobot", "lerobot"),
    Dependency("torch", "torch"),
    Dependency("torchvision", "torchvision"),
    Dependency("opencv-python-headless", "cv2"),
    Dependency("pyserial", "serial"),
    Dependency("feetech-servo-sdk", "scservo_sdk"),
    Dependency("datasets", "datasets"),
    Dependency("diffusers", "diffusers"),
    Dependency("pytest", "pytest"),
    Dependency("ruff", "ruff"),
)


def module_root() -> Path:
    return Path(__file__).resolve().parents[1]


def check_dependency(dependency: Dependency) -> dict[str, Any]:
    try:
        importlib.import_module(dependency.module)
        version = importlib.metadata.version(dependency.distribution)
    except (ImportError, importlib.metadata.PackageNotFoundError) as error:
        return {
            **asdict(dependency),
            "available": False,
            "version": None,
            "detail": str(error),
        }
    except Exception as error:
        return {
            **asdict(dependency),
            "available": False,
            "version": None,
            "detail": f"import failed: {error}",
        }
    return {
        **asdict(dependency),
        "available": True,
        "version": version,
        "detail": "installed",
    }


def directory_status(path: Path, create: bool = False) -> dict[str, Any]:
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_directory": path.is_dir(),
    }


def build_report(root: Path | None = None, create_runtime_dirs: bool = False) -> dict[str, Any]:
    root = (root or module_root()).resolve()
    workspace = root.parent
    dependencies = [check_dependency(dependency) for dependency in DEPENDENCIES]
    required_missing = [
        item["distribution"]
        for item in dependencies
        if item["required"] and not item["available"]
    ]

    cuda_available = False
    cuda_device = None
    torch_item = next(
        (item for item in dependencies if item["distribution"] == "torch"),
        None,
    )
    if torch_item is not None and torch_item["available"]:
        try:
            torch = importlib.import_module("torch")
            cuda_available = bool(torch.cuda.is_available())
            if cuda_available:
                cuda_device = str(torch.cuda.get_device_name(0))
        except Exception as error:
            torch_item["available"] = False
            torch_item["detail"] = f"CUDA inspection failed: {error}"
            required_missing.append("torch")

    paths = {
        "module": directory_status(root),
        "lerobot": directory_status(workspace / "lerobot-main"),
        "calibration_cache": directory_status(
            workspace / "lerobot-main" / ".cache" / "calibration" / "so101_two"
        ),
        "datasets": directory_status(root / "datasets", create_runtime_dirs),
        "outputs": directory_status(root / "outputs", create_runtime_dirs),
    }
    required_paths = ("module", "lerobot")
    path_failures = [name for name in required_paths if not paths[name]["is_directory"]]

    software_ready = not required_missing and not path_failures
    return {
        "schema_version": 1,
        "result": {
            "software_ready": software_ready,
            "software_failures": {
                "missing_dependencies": sorted(set(required_missing)),
                "missing_paths": path_failures,
            },
            "hardware_status": "not_checked",
            "hardware_note": "This command does not inspect or require robot hardware.",
        },
        "system": {
            "platform": platform.platform(),
            "python_version": sys.version.split()[0],
            "python_executable": sys.executable,
        },
        "compute": {
            "cuda_available": cuda_available,
            "cuda_device": cuda_device,
        },
        "dependencies": dependencies,
        "paths": paths,
    }


def print_report(report: dict[str, Any]) -> None:
    print(f"Python: {report['system']['python_version']}")
    print(f"Executable: {report['system']['python_executable']}")
    print(f"Platform: {report['system']['platform']}\n")
    for dependency in report["dependencies"]:
        status = "OK" if dependency["available"] else "MISSING"
        detail = dependency["version"] or dependency["detail"]
        print(f"[{status:7}] {dependency['distribution']}: {detail}")
    print("\nPaths:")
    for name, item in report["paths"].items():
        state = "OK" if item["is_directory"] else "MISSING"
        print(f"[{state:7}] {name}: {item['path']}")
    print(f"\nCUDA available: {report['compute']['cuda_available']}")
    print("[NOT CHECKED] Hardware is intentionally outside this software-only check.")
    print("环境检查通过。" if report["result"]["software_ready"] else "软件环境检查失败。")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument(
        "--create-runtime-dirs",
        action="store_true",
        help="create datasets/ and outputs/ when they are absent",
    )
    args = parser.parse_args()

    report = build_report(create_runtime_dirs=args.create_runtime_dirs)
    print_report(report)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"JSON report: {args.json_output}")
    return 0 if report["result"]["software_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
