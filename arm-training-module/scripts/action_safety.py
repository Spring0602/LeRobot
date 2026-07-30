#!/usr/bin/env python3

"""Validate dual-arm actions without importing PyTorch or accessing robot hardware."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class SafetyResult:
    accepted: bool
    errors: tuple[str, ...]


def module_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        config = json.load(file)
    errors = validate_config(config)
    if errors:
        raise ValueError("; ".join(errors))
    return config


def validate_config(config: Any) -> list[str]:
    if not isinstance(config, dict):
        return ["safety config must be a JSON object"]
    errors: list[str] = []
    action = config.get("action")
    control = config.get("control")
    real = config.get("real_hardware")
    synthetic = config.get("synthetic_test")
    if not isinstance(action, dict):
        return ["action must be an object"]
    if not isinstance(control, dict):
        return ["control must be an object"]
    if not isinstance(real, dict):
        return ["real_hardware must be an object"]
    if not isinstance(synthetic, dict):
        return ["synthetic_test must be an object"]

    arms = action.get("arm_order")
    joints = action.get("joint_order")
    size = action.get("size")
    if arms != ["left_follower", "right_follower"]:
        errors.append("arm_order must be left_follower then right_follower")
    if not isinstance(joints, list) or len(joints) != 7 or len(set(joints)) != 7:
        errors.append("joint_order must contain seven unique joint names")
    expected_size = len(arms or []) * len(joints or [])
    if size != expected_size:
        errors.append(f"action.size must equal {expected_size}")

    target_hz = control.get("target_frequency_hz")
    tolerance_hz = control.get("frequency_tolerance_hz")
    if not _positive_number(target_hz):
        errors.append("target_frequency_hz must be positive")
    if not _nonnegative_number(tolerance_hz):
        errors.append("frequency_tolerance_hz must be non-negative")
    elif _positive_number(target_hz) and tolerance_hz >= target_hz:
        errors.append("frequency_tolerance_hz must be smaller than target_frequency_hz")

    limits = synthetic.get("absolute_limits_per_arm")
    deltas = synthetic.get("max_step_delta_per_arm")
    if not _valid_limits(limits, len(joints or [])):
        errors.append("synthetic absolute limits must contain one min/max pair per joint")
    if (
        not isinstance(deltas, list)
        or len(deltas) != len(joints or [])
        or not all(_positive_number(value) for value in deltas)
    ):
        errors.append("synthetic max deltas must contain one positive value per joint")

    real_limits = real.get("absolute_limits")
    real_deltas = real.get("max_step_delta")
    if (real_limits is None) != (real_deltas is None):
        errors.append("real absolute limits and max deltas must be supplied together")
    return errors


def _positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


def _nonnegative_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def _valid_limits(value: Any, expected: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == expected
        and all(
            isinstance(pair, list)
            and len(pair) == 2
            and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in pair)
            and all(math.isfinite(item) for item in pair)
            and pair[0] < pair[1]
            for pair in value
        )
    )


def split_action(action: Sequence[float], config: dict[str, Any]) -> dict[str, list[float]]:
    joints_per_arm = len(config["action"]["joint_order"])
    return {
        arm: list(action[index * joints_per_arm : (index + 1) * joints_per_arm])
        for index, arm in enumerate(config["action"]["arm_order"])
    }


def join_action(
    per_arm: dict[str, Sequence[float]],
    config: dict[str, Any],
) -> list[float]:
    return [
        value
        for arm in config["action"]["arm_order"]
        for value in per_arm[arm]
    ]


def _numeric_action(action: Any, size: int, label: str) -> tuple[list[float] | None, list[str]]:
    if not isinstance(action, (list, tuple)):
        return None, [f"{label} must be a list or tuple"]
    if len(action) != size:
        return None, [f"{label} must contain exactly {size} values, got {len(action)}"]
    values: list[float] = []
    errors: list[str] = []
    for index, value in enumerate(action):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{label}[{index}] must be numeric")
            continue
        converted = float(value)
        if not math.isfinite(converted):
            errors.append(f"{label}[{index}] must be finite")
        values.append(converted)
    return (values if not errors else None), errors


def validate_action(
    action: Any,
    config: dict[str, Any],
    *,
    mode: str,
    previous_action: Any | None = None,
    previous_timestamp: float | None = None,
    timestamp: float | None = None,
) -> SafetyResult:
    errors = validate_config(config)
    if errors:
        return SafetyResult(False, tuple(f"config: {error}" for error in errors))
    if mode not in {"synthetic", "real"}:
        return SafetyResult(False, ("mode must be 'synthetic' or 'real'",))

    size = config["action"]["size"]
    values, action_errors = _numeric_action(action, size, "action")
    errors.extend(action_errors)
    if values is None:
        return SafetyResult(False, tuple(errors))

    if mode == "real":
        limits = config["real_hardware"]["absolute_limits"]
        max_deltas = config["real_hardware"]["max_step_delta"]
        if limits is None or max_deltas is None:
            return SafetyResult(
                False,
                ("real hardware output blocked: measured safety limits are missing",),
            )
    else:
        per_arm_limits = config["synthetic_test"]["absolute_limits_per_arm"]
        per_arm_deltas = config["synthetic_test"]["max_step_delta_per_arm"]
        arm_count = len(config["action"]["arm_order"])
        limits = per_arm_limits * arm_count
        max_deltas = per_arm_deltas * arm_count

    if not _valid_limits(limits, size):
        errors.append("selected absolute limits are invalid")
    elif len(max_deltas) != size or not all(_positive_number(value) for value in max_deltas):
        errors.append("selected max step deltas are invalid")
    else:
        for index, (value, bounds) in enumerate(zip(values, limits, strict=True)):
            if not bounds[0] <= value <= bounds[1]:
                errors.append(
                    f"action[{index}]={value} outside [{bounds[0]}, {bounds[1]}]"
                )

    if previous_action is not None:
        previous, previous_errors = _numeric_action(previous_action, size, "previous_action")
        errors.extend(previous_errors)
        if previous is not None and len(max_deltas) == size:
            for index, (current, old, maximum) in enumerate(
                zip(values, previous, max_deltas, strict=True)
            ):
                delta = abs(current - old)
                if delta > maximum:
                    errors.append(
                        f"action[{index}] step delta {delta} exceeds {maximum}"
                    )

    if (previous_timestamp is None) != (timestamp is None):
        errors.append("previous_timestamp and timestamp must be supplied together")
    elif previous_timestamp is not None and timestamp is not None:
        delta_time = timestamp - previous_timestamp
        if not math.isfinite(delta_time) or delta_time <= 0:
            errors.append("timestamps must be finite and strictly increasing")
        else:
            actual_hz = 1.0 / delta_time
            target = config["control"]["target_frequency_hz"]
            tolerance = config["control"]["frequency_tolerance_hz"]
            if not target - tolerance <= actual_hz <= target + tolerance:
                errors.append(
                    f"control frequency {actual_hz:.3f} Hz outside "
                    f"[{target - tolerance}, {target + tolerance}] Hz"
                )

    return SafetyResult(not errors, tuple(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=module_root() / "configs" / "action_safety.json",
    )
    parser.add_argument("--mode", choices=("synthetic", "real"), required=True)
    parser.add_argument("--action", required=True, help="JSON action vector")
    parser.add_argument("--previous-action", help="previous JSON action vector")
    parser.add_argument("--previous-timestamp", type=float)
    parser.add_argument("--timestamp", type=float)
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        action = json.loads(args.action)
        previous = json.loads(args.previous_action) if args.previous_action else None
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"[FAIL] {error}")
        return 1
    result = validate_action(
        action,
        config,
        mode=args.mode,
        previous_action=previous,
        previous_timestamp=args.previous_timestamp,
        timestamp=args.timestamp,
    )
    print("[ACCEPTED]" if result.accepted else "[REJECTED]")
    for error in result.errors:
        print(f"- {error}")
    return 0 if result.accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
