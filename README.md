# SuperSlicer ⇄ PrusaSlicer filament profile converter

Convert filament profiles (`.ini`) between **SuperSlicer** and **PrusaSlicer**, in both directions.
Includes a command-line script and a small Windows-friendly GUI that finds your slicer folders
and installs the converted profiles directly into PrusaSlicer.

> Not affiliated with Prusa Research or the SuperSlicer project.
> Always check a converted profile in the slicer before printing with it.

## Features

- SuperSlicer → PrusaSlicer and PrusaSlicer → SuperSlicer, source format auto-detected
- Batch conversion of a whole folder
- Parameters present in both slicers are copied; renamed ones are mapped
  (`default_fan_speed` ↔ `min_fan_speed`, `filament_seam_gap` ↔ `filament_seam_gap_distance`, …)
- Parameters that exist in only one slicer are dropped or filled with defaults, and **listed in a report**
- SuperSlicer "phony" values (prefixed with `!`) become `nil` in PrusaSlicer
- GUI: auto-detects config folders, checkboxes per profile, never overwrites without a backup
- No dependency beyond Python 3.8+ (the GUI uses `tkinter`, bundled with Python on Windows)

## Usage

### Graphical interface (Windows)

Keep `converter_gui.py`, `convert_filament.py` and `launch.bat` in the same folder and
double-click `launch.bat`. Pick your profiles, click **Convert and install into PrusaSlicer**,
then restart PrusaSlicer.

Existing PrusaSlicer profiles are skipped unless you tick *overwrite*; in that case the old
version is saved in `filament_backups/` next to PrusaSlicer's `filament` folder.

### Command line

```
python convert_filament.py profile.ini                # direction auto-detected
python convert_filament.py profile.ini -o out.ini
python convert_filament.py profile.ini --to prusa     # or --to super
python convert_filament.py folder/ -d out_folder/     # batch
python convert_filament.py profile.ini --keep-phony   # keep "!" values as real values
```

When the output goes to another folder (`-d`), file names are kept. Otherwise a
`_prusaslicer` / `_superslicer` suffix is added so the original is never overwritten.

### Standalone .exe (optional)

```
pip install pyinstaller
pyinstaller --onefile --windowed --name FilamentConverter converter_gui.py
```

The result is in `dist/`. Unsigned PyInstaller executables are sometimes flagged by
SmartScreen or antivirus software.

### Where are the profiles?

| OS | SuperSlicer / PrusaSlicer filament folders |
|---|---|
| Windows | `%APPDATA%\SuperSlicer\filament`, `%APPDATA%\PrusaSlicer\filament` |
| macOS | `~/Library/Application Support/SuperSlicer/filament`, `.../PrusaSlicer/filament` |
| Linux | `~/.config/SuperSlicer/filament`, `~/.config/PrusaSlicer/filament` |

## Known limitations

- The mapping was built from one pair of exports (SuperSlicer 2.7.61.10, PrusaSlicer 2.9.6).
  Other versions may add or rename parameters; unknown ones are reported as dropped.
- Dynamic overhang fan speeds are not translated (the two slicers express them differently).
- The meaning of the `!` prefix (a disabled/inherited value) is inferred from the sample files,
  not from official documentation. If it is wrong for your profiles, use `--keep-phony`.
- `inherits` and compatibility conditions are not carried over; converted profiles show up for all printers.
- Only filament profiles are supported (not print or printer profiles).

## Tests

```
python -m unittest discover tests
```

## Contributing

Issues and pull requests are welcome, especially: more sample pairs (PLA, PETG, TPU…),
other slicer versions, and print/printer profile support. If a conversion looks wrong,
please attach the source `.ini` and the converted one.

## License

MIT, see [LICENSE](LICENSE).
