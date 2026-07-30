#!/usr/bin/env python3

"""Validate the recorded SO-101 device map and optionally inspect live aliases."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


EXPECTED_ROLES = {"left_follower", "right_follower", "left_leader", "right_leader"}
EXPECTED_ALIASES = {"/dev/f_left", "/dev/f_right", "/dev/l_left", "/dev/l_right"}
RULE_PATTERN = re.compile(
    r'ATTRS\{idVendor\}=="(?P<vendor>[^"]+)".*'
    r'ATTRS\{idProduct\}=="(?P<product>[^"]+)".*'
    r'ATTRS\{serial\}=="(?P<serial>[^"]+)".*'
    r'SYMLINK\+="(?P<alias>[^"]+)"'
)


def module_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_map(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError("device map must be a JSON object")
    return value


def validate_map(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    usb = data.get("usb")
    arms = data.get("arms")
    if not isinstance(usb, dict):
        return ["usb must be an object"]
    if not isinstance(arms, list):
        return ["arms must be a list"]

    vendor = usb.get("vendor_id")
    product = usb.get("product_id")
    if not isinstance(vendor, str) or not re.fullmatch(r"[0-9a-fA-F]{4}", vendor):
        errors.append("usb.vendor_id must contain four hexadecimal characters")
    if not isinstance(product, str) or not re.fullmatch(r"[0-9a-fA-F]{4}", product):
        errors.append("usb.product_id must contain four hexadecimal characters")

    roles: list[str] = []
    aliases: list[str] = []
    serials: list[str] = []
    for index, arm in enumerate(arms):
        if not isinstance(arm, dict):
            errors.append(f"arms[{index}] must be an object")
            continue
        for key in ("label", "role", "alias", "serial"):
            if not isinstance(arm.get(key), str) or not arm[key]:
                errors.append(f"arms[{index}].{key} must be a non-empty string")
        if isinstance(arm.get("role"), str):
            roles.append(arm["role"])
        if isinstance(arm.get("alias"), str):
            aliases.append(arm["alias"])
        if isinstance(arm.get("serial"), str):
            serials.append(arm["serial"])

    if set(roles) != EXPECTED_ROLES or len(roles) != len(EXPECTED_ROLES):
        errors.append("arms must contain each expected role exactly once")
    if set(aliases) != EXPECTED_ALIASES or len(aliases) != len(EXPECTED_ALIASES):
        errors.append("arms must contain each expected /dev alias exactly once")
    if len(serials) != len(set(serials)):
        errors.append("controller serial numbers must be unique")
    return errors


def parse_rules(path: Path) -> list[dict[str, str]]:
    rules: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = RULE_PATTERN.search(line)
        if match:
            rule = match.groupdict()
            rule["alias"] = f"/dev/{rule['alias']}"
            rules.append(rule)
    return rules


def validate_rules(data: dict[str, Any], rules_path: Path) -> list[str]:
    rules = parse_rules(rules_path)
    usb = data["usb"]
    expected = {
        (usb["vendor_id"].lower(), usb["product_id"].lower(), arm["serial"], arm["alias"])
        for arm in data["arms"]
    }
    actual = {
        (rule["vendor"].lower(), rule["product"].lower(), rule["serial"], rule["alias"])
        for rule in rules
    }
    errors: list[str] = []
    if expected != actual:
        errors.append("udev rules do not exactly match the JSON device map")
    text = rules_path.read_text(encoding="utf-8")
    if 'MODE="0777"' in text or 'MODE:="0777"' in text:
        errors.append("udev rules must not grant world read/write/execute access")
    for required in ('GROUP="dialout"', 'MODE="0660"', 'TAG+="uaccess"'):
        if len(re.findall(re.escape(required), text)) != len(data["arms"]):
            errors.append(f"each udev rule must contain {required}")
    return errors


def udev_properties(device: Path) -> dict[str, str]:
    try:
        result = subprocess.run(
            ["udevadm", "info", "--query=property", f"--name={device}"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return {"_ERROR": "udevadm is unavailable"}
    if result.returncode != 0:
        detail = result.stderr.strip() or f"udevadm exited with {result.returncode}"
        return {"_ERROR": detail}
    return dict(
        line.split("=", 1)
        for line in result.stdout.splitlines()
        if "=" in line
    )


def check_live(data: dict[str, Any]) -> int:
    failed = False
    for arm in data["arms"]:
        alias = Path(arm["alias"])
        if alias.is_symlink() and not alias.exists():
            print(f"[BROKEN] {arm['role']}: {alias} is a broken symlink")
            failed = True
            continue
        if not alias.exists():
            print(f"[MISSING] {arm['role']}: {alias}")
            failed = True
            continue
        target = alias.resolve()
        properties = udev_properties(target)
        if "_ERROR" in properties:
            print(f"[FAIL] {arm['role']}: cannot inspect {target}: {properties['_ERROR']}")
            failed = True
            continue
        serial = properties.get("ID_SERIAL_SHORT")
        vendor = properties.get("ID_VENDOR_ID")
        product = properties.get("ID_MODEL_ID")
        access = os.access(target, os.R_OK | os.W_OK)
        matches = (
            serial == arm["serial"]
            and vendor == data["usb"]["vendor_id"]
            and product == data["usb"]["product_id"]
        )
        state = "OK" if matches and access else "FAIL"
        print(
            f"[{state}] {arm['role']}: {alias} -> {target}; "
            f"serial={serial!r}; usb={vendor!r}:{product!r}; rw={access}"
        )
        failed = failed or not (matches and access)
    return 2 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--map",
        type=Path,
        default=module_root() / "configs" / "so101_devices.json",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=module_root() / "configs" / "99-so101.rules",
    )
    parser.add_argument("--live", action="store_true", help="also verify connected /dev aliases")
    args = parser.parse_args()

    try:
        data = load_map(args.map)
        errors = validate_map(data)
        if not errors:
            errors.extend(validate_rules(data, args.rules))
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as error:
        errors = [str(error)]

    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1
    print("[OK] device map and udev rules are internally consistent")
    if args.live:
        return check_live(data)
    print("[SKIP] live device verification was not requested")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
