#!/usr/bin/env python3

"""Verify the Ubuntu Python environment required by the arm training module."""

from __future__ import annotations

import importlib
import importlib.metadata
import platform
import sys
from dataclasses import dataclass


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


def check_dependency(dependency: Dependency) -> tuple[bool, str]:
    try:
        importlib.import_module(dependency.module)
        version = importlib.metadata.version(dependency.distribution)
    except (ImportError, importlib.metadata.PackageNotFoundError) as error:
        return False, str(error)
    return True, version


def main() -> int:
    print(f"Python: {sys.version.split()[0]}")
    print(f"Executable: {sys.executable}")
    print(f"Platform: {platform.platform()}")
    print()

    failures: list[str] = []
    for dependency in DEPENDENCIES:
        available, detail = check_dependency(dependency)
        status = "OK" if available else "MISSING"
        print(f"[{status:7}] {dependency.distribution}: {detail}")
        if dependency.required and not available:
            failures.append(dependency.distribution)

    if failures:
        print("\n缺少依赖: " + ", ".join(failures))
        return 1

    torch = importlib.import_module("torch")
    print(f"\nCUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA device: {torch.cuda.get_device_name(0)}")

    print("环境检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
