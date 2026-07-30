from __future__ import annotations

import importlib.util
import math
import sys
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "action_safety.py"
SPEC = importlib.util.spec_from_file_location("action_safety", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
action_safety = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = action_safety
SPEC.loader.exec_module(action_safety)


class ActionSafetyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.config = action_safety.load_config(cls.root / "configs" / "action_safety.json")
        cls.zero = [0.0] * 14

    def assert_rejected(self, action, expected: str, **kwargs) -> None:
        result = action_safety.validate_action(
            action,
            self.config,
            mode="synthetic",
            **kwargs,
        )
        self.assertFalse(result.accepted)
        self.assertTrue(
            any(expected in error for error in result.errors),
            result.errors,
        )

    def test_valid_synthetic_action_is_accepted(self) -> None:
        result = action_safety.validate_action(
            self.zero,
            self.config,
            mode="synthetic",
        )
        self.assertTrue(result.accepted, result.errors)

    def test_boundary_values_are_accepted(self) -> None:
        one_arm = [-180.0] * 6 + [100.0]
        result = action_safety.validate_action(
            one_arm * 2,
            self.config,
            mode="synthetic",
        )
        self.assertTrue(result.accepted, result.errors)

    def test_wrong_length_is_rejected(self) -> None:
        self.assert_rejected([0.0] * 13, "exactly 14")

    def test_non_numeric_value_is_rejected(self) -> None:
        action = self.zero.copy()
        action[2] = "bad"
        self.assert_rejected(action, "must be numeric")

    def test_nan_and_inf_are_rejected(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            action = self.zero.copy()
            action[0] = value
            self.assert_rejected(action, "must be finite")

    def test_absolute_limit_is_enforced(self) -> None:
        action = self.zero.copy()
        action[6] = 101.0
        self.assert_rejected(action, "outside [0.0, 100.0]")

    def test_step_delta_is_enforced(self) -> None:
        action = self.zero.copy()
        action[4] = 10.01
        self.assert_rejected(
            action,
            "step delta",
            previous_action=self.zero,
        )

    def test_exact_step_delta_is_accepted(self) -> None:
        action = self.zero.copy()
        action[4] = 10.0
        result = action_safety.validate_action(
            action,
            self.config,
            mode="synthetic",
            previous_action=self.zero,
        )
        self.assertTrue(result.accepted, result.errors)

    def test_frequency_is_enforced(self) -> None:
        self.assert_rejected(
            self.zero,
            "control frequency",
            previous_timestamp=1.0,
            timestamp=1.1,
        )

    def test_target_frequency_is_accepted(self) -> None:
        result = action_safety.validate_action(
            self.zero,
            self.config,
            mode="synthetic",
            previous_timestamp=1.0,
            timestamp=1.0 + 1.0 / 30.0,
        )
        self.assertTrue(result.accepted, result.errors)

    def test_real_output_is_blocked_without_measured_limits(self) -> None:
        result = action_safety.validate_action(
            self.zero,
            self.config,
            mode="real",
        )
        self.assertFalse(result.accepted)
        self.assertIn("measured safety limits are missing", result.errors[0])

    def test_split_and_join_dual_arm_action(self) -> None:
        action = [float(index) for index in range(14)]
        split = action_safety.split_action(action, self.config)
        self.assertEqual(split["left_follower"], action[:7])
        self.assertEqual(split["right_follower"], action[7:])
        self.assertEqual(action_safety.join_action(split, self.config), action)


if __name__ == "__main__":
    unittest.main()
