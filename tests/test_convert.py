import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import convert_filament as cf  # noqa: E402

SUPER = (ROOT / "examples" / "superslicer_abs.ini").read_text(encoding="utf-8")
PRUSA = (ROOT / "examples" / "prusaslicer_asa.ini").read_text(encoding="utf-8")


def convert(text, to=None):
    out, source, target, dropped, defaulted, notes = cf.convert_text(text, to)
    return cf.parse_ini(out), source, target, dropped


class SuperToPrusa(unittest.TestCase):
    def setUp(self):
        self.out, self.source, self.target, self.dropped = convert(SUPER)
        self.src = cf.parse_ini(SUPER)

    def test_direction_detected(self):
        self.assertEqual((self.source, self.target), ("super", "prusa"))

    def test_common_values_copied(self):
        for key in ("temperature", "first_layer_temperature", "bed_temperature",
                    "extrusion_multiplier", "filament_cost", "filament_density",
                    "filament_diameter", "filament_type", "slowdown_below_layer_time"):
            self.assertEqual(self.out[key], self.src[key], key)

    def test_renamed_parameters(self):
        self.assertEqual(self.out["min_fan_speed"], self.src["default_fan_speed"])
        self.assertIn("custom_parameters_filament", self.out)
        self.assertIn("filament_seam_gap_distance", self.out)

    def test_phony_values_become_nil(self):
        self.assertEqual(self.out["filament_retract_length"], "nil")
        self.assertEqual(self.out["filament_wipe"], "nil")

    def test_no_phony_prefix_left(self):
        self.assertFalse([k for k, v in self.out.items() if v.startswith("!")])

    def test_superslicer_only_parameters_dropped(self):
        for key in ("filament_pressure_advance", "infill_fan_speed"):
            self.assertNotIn(key, self.out)
            self.assertIn(key, self.dropped)

    def test_no_leaked_compatibility_condition(self):
        self.assertEqual(self.out["inherits"], "")
        self.assertEqual(self.out["compatible_printers_condition"], "")


class PrusaToSuper(unittest.TestCase):
    def setUp(self):
        self.out, self.source, self.target, self.dropped = convert(PRUSA)
        self.src = cf.parse_ini(PRUSA)

    def test_direction_detected(self):
        self.assertEqual((self.source, self.target), ("prusa", "super"))

    def test_common_values_copied(self):
        for key in ("temperature", "bed_temperature", "extrusion_multiplier",
                    "filament_density", "filament_type", "filament_max_volumetric_speed"):
            self.assertEqual(self.out[key], self.src[key], key)

    def test_renamed_parameters(self):
        self.assertEqual(self.out["default_fan_speed"], self.src["min_fan_speed"])

    def test_nil_becomes_phony(self):
        self.assertTrue(self.out["filament_retract_length"].startswith("!"))

    def test_prusa_only_parameters_dropped(self):
        self.assertNotIn("filament_abrasive", self.out)
        self.assertIn("filament_abrasive", self.dropped)


class Errors(unittest.TestCase):
    def test_same_target_rejected(self):
        with self.assertRaises(ValueError):
            cf.convert_text(SUPER, "super")


if __name__ == "__main__":
    unittest.main()
