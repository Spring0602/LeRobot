#!/usr/bin/env python3

"""Read-only inventory of serial devices relevant to the SO-101 setup."""

from __future__ import annotations

import getpass
import glob
import os
import platform
import sys
from pathlib import Path

try:
    import grp
except ImportError:  # pragma: no cover - only used for a clearer non-Linux message
    grp = None

try:
    from serial.tools import list_ports
except ImportError:  # pragma: no cover - exercised through command-level behavior
    list_ports = None


DEVICE_PATTERNS = (
    "/dev/ttyUSB*",
    "/dev/ttyACM*",
    "/dev/ttyCH341USB*",
)
EXPECTED_ALIASES = (
    "/dev/l_left",
    "/dev/l_right",
    "/dev/f_left",
    "/dev/f_right",
)
SERIAL_LINK_DIRS = (
    Path("/dev/serial/by-id"),
    Path("/dev/serial/by-path"),
)


def resolve_link(path: Path) -> str:
    if not path.exists() and not path.is_symlink():
        return "missing"
    try:
        return str(path.resolve(strict=True))
    except FileNotFoundError:
        return "broken symlink"


def current_groups() -> list[str]:
    if grp is None or not hasattr(os, "getgroups"):
        return []
    group_ids = os.getgroups()
    return sorted({grp.getgrgid(group_id).gr_name for group_id in group_ids})


def main() -> int:
    print("SO-101 device inventory (read-only)")
    if platform.system() != "Linux":
        print("Software error: device inventory must run inside Ubuntu/Linux.", file=sys.stderr)
        return 1
    if list_ports is None:
        print("Software error: pyserial is missing; install the project dependencies.", file=sys.stderr)
        return 1
    print(f"User: {getpass.getuser()}")
    groups = current_groups()
    print(f"Groups: {', '.join(groups)}")
    print(f"dialout access: {'yes' if 'dialout' in groups else 'no'}")

    print("\nExpected aliases:")
    for alias in EXPECTED_ALIASES:
        print(f"- {alias} -> {resolve_link(Path(alias))}")

    candidate_devices = sorted({path for pattern in DEVICE_PATTERNS for path in glob.glob(pattern)})
    print("\nCandidate motor serial devices:")
    if candidate_devices:
        for device in candidate_devices:
            print(f"- {device}")
    else:
        print("- none")

    print("\nPySerial USB-related ports:")
    usb_ports = [
        port
        for port in list_ports.comports()
        if port.vid is not None or port.pid is not None or "USB" in port.device.upper()
    ]
    if usb_ports:
        for port in usb_ports:
            print(
                f"- {port.device}: description={port.description!r}, "
                f"vid={port.vid!r}, pid={port.pid!r}, serial={port.serial_number!r}, "
                f"location={port.location!r}"
            )
    else:
        print("- none")

    for directory in SERIAL_LINK_DIRS:
        print(f"\n{directory}:")
        if not directory.is_dir():
            print("- unavailable")
            continue
        entries = sorted(directory.iterdir())
        if not entries:
            print("- empty")
            continue
        for entry in entries:
            print(f"- {entry.name} -> {resolve_link(entry)}")

    if not candidate_devices:
        print("\nResult: no candidate SO-101 serial device is currently visible to Ubuntu.")
        return 2

    print("\nResult: candidate serial devices found; physical role mapping still requires manual verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
