"""
rename_rinex_tool.py – minimal helpers for renaming *.25o and cloning to *.obs
"""

from pathlib import Path
import os
import shutil

__all__ = ["process_folder", "batch_rename_convert"]

def process_folder(folder: Path, ext: str = "25o", keep_original: bool = True):
    """
    Make *.25o → *.obs with matching base name.

    Parameters
    ----------
    folder : pathlib.Path
    ext : str           File-extension to look for (default "25o")
    keep_original : bool
        • True  → keep the renamed *.25o **and** make *.obs copy  
        • False → rename in-place so the file itself becomes *.obs
    """
    rpos = list(folder.glob("*.RPOS"))
    rinx = list(folder.glob(f"*.{ext}"))

    if len(rpos) != 1 or len(rinx) != 1:
        print(f"[skip] {folder} – need exactly one .RPOS & one .{ext}")
        return

    base = rpos[0].stem                       # e.g. SITE0100
    src  = rinx[0]
    renamed_25o = folder / f"{base}.{ext}"
    obs_file    = folder / f"{base}.obs"

    # 1) ensure *.25o has the same base name as *.RPOS
    if src != renamed_25o:
        print(f"[rename] {src.name} → {renamed_25o.name}")
        src.rename(renamed_25o)
        src = renamed_25o

    if keep_original:
        print(f"[copy ] {src.name} → {obs_file.name}")
        shutil.copyfile(src, obs_file)
    else:
        print(f"[mv   ] {src.name} → {obs_file.name}")
        src.rename(obs_file)

def batch_rename_convert(master_folder, ext: str = "25o", keep_original: bool = True):
    """
    Walk *master_folder* recursively and call `process_folder` everywhere.
    """
    master = Path(master_folder).expanduser().resolve()
    for root, _, _ in os.walk(master):
        process_folder(Path(root), ext=ext, keep_original=keep_original)
