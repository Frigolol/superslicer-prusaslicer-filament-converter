#!/usr/bin/env python3
"""Automatic filament profile converter: SuperSlicer -> PrusaSlicer.

Double-click launch.bat (Windows). Requires convert_filament.py in the same folder.

- Detects the SuperSlicer and PrusaSlicer configuration folders.
- Lists your SuperSlicer filament profiles, with checkboxes.
- Converts and writes directly into PrusaSlicer's "filament" folder.
- Never replaces an existing profile without keeping a backup copy.
"""
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import convert_filament as cf  # noqa: E402


# --------------------------------------------------------------------------
# Logic (no UI, testable)
# --------------------------------------------------------------------------
def config_roots():
    """Base configuration folder, depending on the OS."""
    home = Path.home()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = home / "Library" / "Application Support"
    else:
        base = home / ".config"
    return base


def find_filament_dirs(base=None):
    base = Path(base) if base else config_roots()
    found = {"super": [], "prusa": []}
    if not base.is_dir():
        return found
    for d in sorted(base.iterdir()):
        name = d.name.lower()
        if not (d / "filament").is_dir():
            continue
        if name.startswith("superslicer"):
            found["super"].append(d / "filament")
        elif name.startswith("prusaslicer"):
            found["prusa"].append(d / "filament")
    return found


def list_profiles(folder):
    return sorted(Path(folder).glob("*.ini"), key=lambda p: p.name.lower())


def convert_profiles(files, dest_dir, overwrite=False, keep_phony=False, log=print):
    """Convert SuperSlicer files into dest_dir (PrusaSlicer format).

    Returns (converted, skipped, errors).
    An existing profile is skipped unless overwrite=True (it is then copied to
    <PrusaSlicer config>/filament_backups before being replaced).
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    done, skipped, errors = [], [], []
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for f in map(Path, files):
        try:
            text = f.read_text(encoding="utf-8")
            out, source, target, dropped, defaulted, notes = cf.convert_text(
                text, "prusa", keep_phony)
        except Exception as e:  # noqa: BLE001
            errors.append((f.name, str(e)))
            log(f"ERROR    {f.name}: {e}")
            continue
        dest = dest_dir / f.name
        if dest.exists():
            if not overwrite:
                skipped.append(f.name)
                log(f"SKIPPED  {f.name} (already exists in PrusaSlicer)")
                continue
            bak = dest_dir.parent / "filament_backups" / stamp
            bak.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, bak / f.name)
        dest.write_text(out, encoding="utf-8")
        done.append(f.name)
        extra = f" - {len(notes)} item(s) to check" if notes else ""
        log(f"OK       {f.name}{extra}")
    return done, skipped, errors


# --------------------------------------------------------------------------
# Interface
# --------------------------------------------------------------------------
def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("Filament profile converter: SuperSlicer -> PrusaSlicer")
    root.geometry("820x640")

    found = find_filament_dirs()
    src_var = tk.StringVar(value=str(found["super"][0]) if found["super"] else "")
    dst_var = tk.StringVar(value=str(found["prusa"][0]) if found["prusa"] else "")
    overwrite_var = tk.BooleanVar(value=False)
    phony_var = tk.BooleanVar(value=False)
    checks = {}

    pad = {"padx": 10, "pady": 4}

    def folder_row(label, var, on_change=None):
        frm = ttk.Frame(root)
        frm.pack(fill="x", **pad)
        ttk.Label(frm, text=label, width=30).pack(side="left")
        ttk.Entry(frm, textvariable=var).pack(side="left", fill="x", expand=True)

        def browse():
            d = filedialog.askdirectory(initialdir=var.get() or str(config_roots()))
            if d:
                var.set(d)
                if on_change:
                    on_change()
        ttk.Button(frm, text="Browse...", command=browse).pack(side="left", padx=(6, 0))

    list_frame = None

    def refresh():
        nonlocal list_frame
        if list_frame is not None:
            list_frame.destroy()
        checks.clear()
        list_frame = ttk.LabelFrame(root, text="SuperSlicer profiles to convert")
        list_frame.pack(fill="both", expand=True, **pad)
        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        src = src_var.get().strip()
        profiles = list_profiles(src) if src and Path(src).is_dir() else []
        if not profiles:
            ttk.Label(inner, text="No .ini profile found in this folder.").pack(
                anchor="w", padx=6, pady=6)
        for p in profiles:
            v = tk.BooleanVar(value=True)
            checks[p] = v
            ttk.Checkbutton(inner, text=p.stem, variable=v).pack(anchor="w", padx=6)
        list_frame.lift()

    folder_row("SuperSlicer folder (filament):", src_var, refresh)
    folder_row("PrusaSlicer folder (filament):", dst_var)

    opts = ttk.Frame(root)
    opts.pack(fill="x", **pad)
    ttk.Checkbutton(opts, text="Replace profiles that already exist (a backup is made)",
                    variable=overwrite_var).pack(anchor="w")
    ttk.Checkbutton(opts, text="Keep SuperSlicer \"!\" values as real values",
                    variable=phony_var).pack(anchor="w")

    refresh()

    btns = ttk.Frame(root)
    btns.pack(fill="x", **pad)

    def set_all(state):
        for v in checks.values():
            v.set(state)

    ttk.Button(btns, text="Select all", command=lambda: set_all(True)).pack(side="left")
    ttk.Button(btns, text="Select none", command=lambda: set_all(False)).pack(
        side="left", padx=6)

    log_box = tk.Text(root, height=9, state="disabled", wrap="word")
    log_box.pack(fill="x", **pad)

    def log(msg):
        log_box.configure(state="normal")
        log_box.insert("end", msg + "\n")
        log_box.see("end")
        log_box.configure(state="disabled")
        root.update_idletasks()

    def go():
        files = [p for p, v in checks.items() if v.get()]
        dst = dst_var.get().strip()
        if not files:
            messagebox.showinfo("Nothing to do", "No profile selected.")
            return
        if not dst:
            messagebox.showwarning("Missing folder",
                                   "Select PrusaSlicer's filament folder.")
            return
        done, skipped, errors = convert_profiles(
            files, dst, overwrite_var.get(), phony_var.get(), log)
        log(f"\nDone: {len(done)} converted, {len(skipped)} skipped, "
            f"{len(errors)} error(s).")
        if done:
            log("Restart PrusaSlicer to see the new profiles.")

    ttk.Button(btns, text="Convert and install into PrusaSlicer",
               command=go).pack(side="right")

    if not found["super"] or not found["prusa"]:
        log("SuperSlicer or PrusaSlicer folder not found automatically: "
            "select it with \"Browse...\".")
    root.mainloop()


if __name__ == "__main__":
    run_gui()
