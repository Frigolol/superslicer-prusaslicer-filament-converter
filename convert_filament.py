#!/usr/bin/env python3
"""Filament profile converter: SuperSlicer <-> PrusaSlicer (.ini).

Usage:
    python convert_filament.py profile.ini                  # direction auto-detected
    python convert_filament.py profile.ini -o out.ini
    python convert_filament.py profile.ini --to prusa|super
    python convert_filament.py folder/ -d out_folder/       # batch conversion

How it works: start from a "template" profile of the target slicer (embedded below,
taken from two sample exports), then overwrite every parameter that has an equivalent
in the source profile. Parameters without an equivalent are listed in the report.

SuperSlicer convention: a value prefixed with "!" is a "phony" value (not enabled,
the setting is inherited from the printer / print profile). It becomes "nil" in
PrusaSlicer when the parameter accepts "nil".
Use --keep-phony to treat it as a real value instead.
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# --------------------------------------------------------------------------
# Embedded template profiles (defaults for parameters with no source value)
# --------------------------------------------------------------------------
SUPER_TEMPLATE = r"""
bed_temperature = 110
bridge_fan_speed = !100
chamber_temperature = 50
compatible_printers =
compatible_printers_condition =
compatible_prints =
compatible_prints_condition =
default_fan_speed = 50
disable_fan_first_layers = 1
end_filament_gcode = "; Filament-specific end gcode \n;END gcode for filament\n"
external_perimeter_fan_speed = !100
extrusion_multiplier = 0.96
fan_below_layer_time = 0
filament_colour = #FF00FF
filament_cooling_final_speed = 3.4
filament_cooling_initial_speed = 2.2
filament_cooling_moves = 4
filament_cooling_zone_pause = 0
filament_cost = 22
filament_custom_variables = ""
filament_density = 1.03
filament_deretract_speed = !0
filament_diameter = 1.75
filament_dip_extraction_speed = 70
filament_dip_insertion_speed = 33
filament_enable_toolchange_part_fan = 0
filament_enable_toolchange_temp = 0
filament_fill_top_flow_ratio = 100%
filament_first_layer_flow_ratio = 100%
filament_load_time = 0
filament_loading_speed = 28
filament_loading_speed_start = 3
filament_max_overlap = 100%
filament_max_speed = 0
filament_max_volumetric_speed = 0
filament_max_wipe_tower_speed = 0
filament_melt_zone_pause = 0
filament_minimal_purge_on_wipe_tower = 15
filament_multitool_ramming = 0
filament_multitool_ramming_flow = 10
filament_multitool_ramming_volume = 10
filament_notes = ""
filament_pressure_advance = !0.02
filament_ramming_parameters = "120 100 6.6 6.8 7.2 7.6 7.9 8.2 8.7 9.4 9.9 10.0| 0.05 6.6 0.45 6.8 0.95 7.8 1.45 8.3 1.95 9.7 2.45 10 2.95 7.6 3.45 7.6 3.95 7.6 4.45 7.6 4.95 7.6"
filament_retract_before_travel = !2
filament_retract_before_wipe = !0%
filament_retract_layer_change = !0
filament_retract_length = !2
filament_retract_length_toolchange = !10
filament_retract_lift = !0
filament_retract_lift_above = !0
filament_retract_lift_before_travel = !2
filament_retract_lift_below = !0
filament_retract_restart_extra = !0
filament_retract_restart_extra_toolchange = !0
filament_retract_speed = !40
filament_seam_gap = !15%
filament_settings_id = "ABS - KVP"
filament_shrink = 100%
filament_skinnydip_distance = 31
filament_soluble = 0
filament_spool_weight = 1000
filament_toolchange_delay = 0
filament_toolchange_part_fan_speed = 50
filament_toolchange_temp = 200
filament_travel_lift_before_obstacle = !0
filament_travel_ramping_lift = !0
filament_travel_slope = !0
filament_type = ABS
filament_unload_time = 0
filament_unloading_speed = 90
filament_unloading_speed_start = 100
filament_use_fast_skinnydip = 0
filament_use_skinnydip = 0
filament_vendor = (Unknown)
filament_wipe = !0
filament_wipe_advanced_pigment = 0.5
filament_wipe_extra_perimeter = !0
filament_wipe_inside_depth = !50%
filament_wipe_inside_end = !1
filament_wipe_inside_start = !0
filament_wipe_lift = !0
filament_wipe_lift_length = !50%
filament_wipe_min = !150%
filament_wipe_only_crossing = !1
filament_wipe_speed = !0
first_layer_bed_temperature = 110
first_layer_temperature = 255
full_fan_speed_layer = 0
gap_fill_fan_speed = !100
idle_temperature = !30
infill_fan_speed = !100
inherits =
internal_bridge_fan_speed = !100
max_fan_speed = 100
max_speed_reduction = 90%
min_print_speed = 10
overhangs_dynamic_fan_speed = !0:5:1:0x100:25x80:50x60:75x40:100x20
overhangs_fan_speed = !100
perimeter_fan_speed = !100
slowdown_below_layer_time = 15
solid_infill_fan_speed = !100
start_filament_gcode = "; Filament gcode\n"
support_material_fan_speed = !100
support_material_interface_fan_speed = !100
temperature = 255
top_fan_speed = !100
"""

PRUSA_TEMPLATE = r"""
bed_temperature = 110
bridge_fan_speed = 50
chamber_minimal_temperature = 40
chamber_temperature = 55
compatible_printers =
compatible_printers_condition = printer_model=~/(V2_250|V2_300|V2_350|VT_250|VT_300|VT_350|V0_120|VS_MK52)/ and nozzle_high_flow[0] and nozzle_diameter[0]==0.4
compatible_prints =
compatible_prints_condition =
cooling = 1
cooling_perimeter_transition_distance = 10
cooling_slowdown_logic = uniform_cooling
custom_parameters_filament = ""
disable_fan_first_layers = 1
enable_dynamic_fan_speeds = 0
end_filament_gcode = "; Filament-specific end gcode"
extrusion_multiplier = 0.92
fan_always_on = 1
fan_below_layer_time = 0
filament_abrasive = 0
filament_colour = #FF3232
filament_cooling_final_speed = 3.4
filament_cooling_initial_speed = 2.2
filament_cooling_moves = 4
filament_cost = 0
filament_density = 1.07
filament_deretract_speed = nil
filament_diameter = 1.75
filament_flush_speed = 0
filament_flush_volume = 0
filament_infill_max_crossing_speed = 0
filament_infill_max_speed = 0
filament_load_time = 0
filament_loading_speed = 28
filament_loading_speed_start = 3
filament_max_volumetric_speed = 25
filament_minimal_purge_on_wipe_tower = 15
filament_multitool_ramming = 0
filament_multitool_ramming_flow = 10
filament_multitool_ramming_volume = 10
filament_notes = ""
filament_purge_multiplier = 100%
filament_ramming_parameters = "120 100 5.70968 6.03226 7 8.25806 9 9.19355 9.3871 9.77419 10.129 10.3226 10.4516 10.5161| 0.05 5.69677 0.45 6.15484 0.95 8.76774 1.45 9.20323 1.95 9.95806 2.45 10.3871 2.95 10.5677 3.45 7.6 3.95 7.6 4.45 7.6 4.95 7.6"
filament_retract_before_travel = nil
filament_retract_before_wipe = nil
filament_retract_layer_change = nil
filament_retract_length = nil
filament_retract_length_toolchange = nil
filament_retract_lift = nil
filament_retract_lift_above = nil
filament_retract_lift_below = nil
filament_retract_restart_extra = nil
filament_retract_restart_extra_toolchange = nil
filament_retract_speed = nil
filament_seam_gap_distance = nil
filament_settings_id = ""
filament_shrinkage_compensation_xy = 0%
filament_shrinkage_compensation_z = 0%
filament_soluble = 0
filament_spool_weight = 0
filament_stamping_distance = 0
filament_stamping_loading_speed = 20
filament_toolchange_delay = 0
filament_travel_lift_before_obstacle = nil
filament_travel_max_lift = nil
filament_travel_ramping_lift = nil
filament_travel_slope = nil
filament_type = ASA
filament_unload_time = 0
filament_unloading_speed = 90
filament_unloading_speed_start = 100
filament_vendor = Generic
filament_wipe = nil
first_layer_bed_temperature = 110
first_layer_temperature = 255
full_fan_speed_layer = 0
idle_temperature = nil
inherits = Generic ASA @Voron HF0.4
max_fan_speed = 50
min_fan_speed = 50
min_print_speed = 10
overhang_fan_speed_0 = 0
overhang_fan_speed_1 = 0
overhang_fan_speed_2 = 0
overhang_fan_speed_3 = 0
slowdown_below_layer_time = 10
start_filament_gcode = "; Filament-specific start gcode"
temperature = 255
"""

# Parameters that are renamed (SuperSlicer -> PrusaSlicer)
RENAME_SUPER_TO_PRUSA = {
    "default_fan_speed": "min_fan_speed",
    "filament_custom_variables": "custom_parameters_filament",
    "filament_seam_gap": "filament_seam_gap_distance",
}
RENAME_PRUSA_TO_SUPER = {v: k for k, v in RENAME_SUPER_TO_PRUSA.items()}

# Profile/machine-specific parameters: never copied as-is
RESET_KEYS = ("inherits", "compatible_printers", "compatible_printers_condition",
              "compatible_prints", "compatible_prints_condition")


def parse_ini(text):
    data = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if sep:
            data[key.strip()] = value.strip()
    return data


def write_ini(data, header):
    lines = [header] + [f"{k} = {v}" for k, v in sorted(data.items())]
    return "\n".join(lines) + "\n"


def detect_source(text, data):
    head = text.splitlines()[0] if text else ""
    if "SuperSlicer" in head:
        return "super"
    if "PrusaSlicer" in head:
        return "prusa"
    if "default_fan_speed" in data or "filament_shrink" in data:
        return "super"
    if "min_fan_speed" in data or "filament_shrinkage_compensation_xy" in data:
        return "prusa"
    raise ValueError("Cannot guess the source slicer: use --to.")


def pct(value):
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*%?\s*$", value.strip('"'))
    return float(m.group(1)) if m else None


def fmt_pct(x):
    return f"{x:g}%"


def to_number(value):
    try:
        return float(value.lstrip("!"))
    except ValueError:
        return None


def super_to_prusa(src, keep_phony=False):
    tmpl = parse_ini(PRUSA_TEMPLATE)
    out = dict(tmpl)
    filled, dropped, notes = set(), [], []

    for k, v in src.items():
        if k == "filament_shrink":
            continue  # handled below
        tk = RENAME_SUPER_TO_PRUSA.get(k, k)
        if tk not in tmpl:
            dropped.append(k)
            continue
        phony = v.startswith("!")
        val = v[1:] if phony else v
        if phony and not keep_phony and tmpl[tk] == "nil":
            out[tk] = "nil"
        else:
            out[tk] = val
            if phony and tmpl[tk] != "nil":
                notes.append(f"{k} = {v}: '!' value kept as-is ({val}), "
                             f"the parameter does not accept 'nil' in PrusaSlicer")
        filled.add(tk)

    # Shrinkage: SuperSlicer stores a factor (100% = no shrinkage),
    # PrusaSlicer stores a compensation (0% = none).
    if "filament_shrink" in src:
        s = pct(src["filament_shrink"].lstrip("!"))
        if s is not None:
            comp = 100 - s
            out["filament_shrinkage_compensation_xy"] = fmt_pct(comp)
            filled.add("filament_shrinkage_compensation_xy")
            if abs(comp) > 1e-9:
                notes.append(f"filament_shrink = {src['filament_shrink']} converti en "
                             f"{fmt_pct(comp)}: check the direction in PrusaSlicer")

    # Printer/machine-specific settings: no inherited condition
    for k in RESET_KEYS:
        out[k] = src.get(k, "")
        filled.add(k)

    # Fan: minimum fan speed set -> fan always on
    fan_min = to_number(out.get("min_fan_speed", "0")) or 0
    out["fan_always_on"] = "1" if fan_min > 0 else "0"
    filled.add("fan_always_on")

    if out.get("filament_vendor") == "(Unknown)":
        out["filament_vendor"] = "Generic"

    defaulted = sorted(k for k in tmpl if k not in filled)
    return out, sorted(set(dropped)), defaulted, notes


def prusa_to_super(src, keep_phony=False):
    tmpl = parse_ini(SUPER_TEMPLATE)
    out = dict(tmpl)
    filled, dropped, notes = set(), [], []

    for k, v in src.items():
        if k in ("filament_shrinkage_compensation_xy", "filament_shrinkage_compensation_z"):
            continue
        tk = RENAME_PRUSA_TO_SUPER.get(k, k)
        if tk not in tmpl:
            dropped.append(k)
            continue
        if v == "nil":
            default = tmpl[tk]
            out[tk] = default if default.startswith("!") else "!" + default
        else:
            out[tk] = v
        filled.add(tk)

    if "filament_shrinkage_compensation_xy" in src:
        c = pct(src["filament_shrinkage_compensation_xy"])
        if c is not None:
            out["filament_shrink"] = fmt_pct(100 - c)
            filled.add("filament_shrink")
            if abs(c) > 1e-9:
                notes.append("filament_shrinkage_compensation_xy converti en "
                             f"filament_shrink = {out['filament_shrink']}: check the direction")

    for k in RESET_KEYS:
        if src.get(k):
            notes.append(f"{k} not carried over (PrusaSlicer-specific expression): {src[k][:60]}")
        out[k] = ""
        filled.add(k)

    defaulted = sorted(k for k in tmpl if k not in filled)
    return out, sorted(set(dropped)), defaulted, notes


def convert_text(text, to=None, keep_phony=False):
    src = parse_ini(text)
    source = detect_source(text, src)
    target = to or ("prusa" if source == "super" else "super")
    if target == source:
        raise ValueError(f"The file is already in {source} format.")
    fn = super_to_prusa if target == "prusa" else prusa_to_super
    out, dropped, defaulted, notes = fn(src, keep_phony)
    name = {"prusa": "PrusaSlicer", "super": "SuperSlicer"}[target]
    header = (f"# converted for {name} by convert_filament.py "
              f"on {datetime.now():%Y-%m-%d at %H:%M:%S}")
    return write_ini(out, header), source, target, dropped, defaulted, notes


def report(path, source, target, dropped, defaulted, notes):
    print(f"== {path.name} : {source} -> {target}")
    if notes:
        print("  To check:")
        for n in notes:
            print(f"    - {n}")
    print(f"  No equivalent, dropped ({len(dropped)}): {', '.join(dropped) or '-'}")
    print(f"  Template defaults used ({len(defaulted)}): {', '.join(defaulted) or '-'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path, help=".ini file or folder of .ini files")
    ap.add_argument("-o", "--output", type=Path, help="output file (single input file)")
    ap.add_argument("-d", "--outdir", type=Path, help="output folder (batch conversion)")
    ap.add_argument("--to", choices=["prusa", "super"], help="target slicer")
    ap.add_argument("--keep-phony", action="store_true",
                    help="treat SuperSlicer '!' values as real values")
    args = ap.parse_args()

    files = sorted(args.input.glob("*.ini")) if args.input.is_dir() else [args.input]
    for f in files:
        text = f.read_text(encoding="utf-8")
        try:
            out, source, target, dropped, defaulted, notes = convert_text(
                text, args.to, args.keep_phony)
        except ValueError as e:
            print(f"!! {f.name} : {e}", file=sys.stderr)
            continue
        suffix = "_prusaslicer" if target == "prusa" else "_superslicer"
        if args.output and len(files) == 1:
            dest = args.output
        else:
            folder = args.outdir or f.parent
            folder.mkdir(parents=True, exist_ok=True)
            # Add a suffix only when writing next to the original (avoids overwriting it)
            same_folder = folder.resolve() == f.parent.resolve()
            dest = folder / (f"{f.stem}{suffix}.ini" if same_folder else f.name)
        dest.write_text(out, encoding="utf-8")
        report(f, source, target, dropped, defaulted, notes)
        print(f"  -> {dest}")


if __name__ == "__main__":
    main()
