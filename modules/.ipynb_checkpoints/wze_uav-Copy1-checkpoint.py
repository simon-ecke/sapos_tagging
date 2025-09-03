
import os
import re
import pandas as pd
import shutil
import errno
import ntpath
from pathlib import Path
from datetime import date, datetime
from typing import List, Dict, Optional, Union, Iterable



def extract_fplans(
    sapos_fn: str,
    dir_path: str,
    output_fn: str
) -> None:
    """
    Scan through `dir_path` (and its subfolders) for files containing "FPLAN"
    in their names and write their full paths to `output_fn`, one per line.

    Parameters
    ----------
    sapos_fn : str
        Path to the SAPOS queries file.
    dir_path : str
        Root directory under which to search for FPLAN files.
    output_fn : str
        Path to the text file where results will be written.
    """
    # (Optional) read the SAPOS file if you need to filter or augment:
    df_sapos = pd.read_table(sapos_fn)

    fplan_list = []
    # Iterate over each date-folder
    for date_folder in os.listdir(dir_path):
        sub_path = os.path.join(dir_path, date_folder)
        if not os.path.isdir(sub_path):
            continue

        # Iterate over each TNR folder
        for tnr_folder in os.listdir(sub_path):
            tnr_path = os.path.join(sub_path, tnr_folder)
            if not os.path.isdir(tnr_path):
                continue

            # Extract integer TNR and date string if needed:
            try:
                tnr_int = int(tnr_folder)
            except ValueError:
                # skip folders whose names aren’t pure integers
                continue
            date_str = date_folder.rsplit('_', 1)[0]

            # Scan files (skipping hidden ones)
            for entry in os.listdir(tnr_path):
                if entry.startswith('.'):
                    continue
                if 'FPLAN' in entry:
                    fplan_list.append(os.path.join(tnr_path, entry))

    # Write results
    with open(output_fn, 'w') as fp:
        for path in fplan_list:
            fp.write(f"{path}\n")

    # Print summary
    print(f"Found {len(fplan_list)} FPLAN entries.")
    print(f"Saved list to: {output_fn}")






def copy_vrs_for_fplans(
    fplan_list_fn: str,
    vrs_root: str,
    ignore_existing: bool = True
) -> None:
    """
    Read a list of FPLAN file paths.  For each one:
      • Locate the parent folder whose name contains "FPLAN"
      • Determine the TNR code from the segment just above that
      • Copy _all_ files/dirs in vrs_root starting with "{TNR}_" into
        that FPLAN folder, preserving names and reporting each copy.

    Parameters
    ----------
    fplan_list_fn : str
        Path to the text file containing full paths to your FPLAN files.
    vrs_root : str
        Directory holding the VRS items (named like "16197_Protokoll_7893220_VRS.txt", 
        "16197_Rinex.obs", etc.).
    ignore_existing : bool
        If True, existing files/dirs in the target will be merged/overwritten
        instead of throwing an error.
    """
    # 1) read and clean your FPLAN paths
    with open(fplan_list_fn, 'r', encoding='utf-8') as fp:
        fplan_paths = [ln.strip() for ln in fp if ln.strip()]

    for fplan_path in fplan_paths:
        # 2) split into parts, look for the folder containing "FPLAN"
        parts = fplan_path.split(os.sep)
        try:
            idx = next(i for i, p in enumerate(parts) if 'FPLAN' in p.upper())
        except StopIteration:
            print(f"⚠️  No FPLAN folder in path, skipping: {fplan_path}")
            continue

        # the FPLAN directory itself:
        fplan_dir = os.sep.join(parts[:idx+1])
        # assume the TNR code is the directory just above it:
        tnr_code = parts[idx-1]

        # 3) find _all_ VRS items that start with "{tnr_code}_"
        candidates: List[str] = [
            itm for itm in os.listdir(vrs_root)
            if itm.startswith(f"{tnr_code}_")
        ]
        if not candidates:
            print(f"⚠️  No VRS items for TNR {tnr_code}, skipping.")
            continue

        # ensure the FPLAN directory exists
        os.makedirs(fplan_dir, exist_ok=True)

        # 4) copy each one
        for itm in candidates:
            src = os.path.join(vrs_root, itm)
            dst = os.path.join(fplan_dir, itm)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=ignore_existing)
                print(f"📁 Copied dir : {src} -> {dst}")
            else:
                shutil.copy2(src, dst)
                print(f"📄 Copied file: {src} -> {dst}")




# SAPOS .batch generation

def write2log(entry: str, log_fn: str) -> None:
    """Append one line to the log file and also print it."""
    with open(log_fn, 'a+', encoding='utf-8') as lf:
        lf.write(entry + '\n')
    print(entry)

def remove_comments(lines: List[str]) -> List[str]:
    """Return a new list with any line starting with '#' removed."""
    return [ln for ln in (l.strip() for l in lines) if ln and not ln.startswith('#')]

def read_dirlist(dirlist_fn: str) -> List[str]:
    """Read all non-comment lines from your mission list file."""
    with open(dirlist_fn, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    return remove_comments(lines)

def find_ppk_files(d: str, epn_yr: str) -> Dict[str, str]:
    """
    Find REDtoolbox inputs in directory `d`.
    Returns keys: 'MRK', 'OBS' (optional), 'O', 'P'.
    Chooses the newest match when multiple exist.
    """
    def _first_match(base: Path, pats: Union[str, Iterable[str]]):
        pat_list = pats if isinstance(pats, (list, tuple)) else (pats,)
        for p in pat_list:
            hits = list(base.rglob(p))
            if hits:
                hits.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                return hits[0]
        return None

    base = Path(d)
    if not base.is_dir():
        raise FileNotFoundError(f"Not a folder: {d}")

    patterns = {
        # MRK: be tolerant (Timestamp.MRK vs .MRK/.mrk)
        'MRK': ('*Timestamp.MRK', '*.MRK', '*.mrk'),
        # Rover OBS: accept Rinex or PPKOBS (or any .obs as fallback if you want)
        'OBS': ('*Rinex.obs', '*PPKOBS.obs'),
        # Base obs/nav: prefer yy-coded; fall back to any .o/.p/.n if needed
        'O':   (f'*.{epn_yr}o', '*.o'),
        'P':   (f'*.{epn_yr}p', f'*.{epn_yr}n', '*.p', '*.n'),
    }

    found: Dict[str, str] = {}
    for key, pats in patterns.items():
        m = _first_match(base, pats)
        if not m:
            raise FileNotFoundError(f"No files matching {pats} in {d}")
        found[key] = ntpath.basename(str(m))

    return found

def build_batch_commands(
    d: str,
    files: Dict[str, str],
    redtoolbox_exe: str = 'REDtoolboxCLI.exe'
) -> List[str]:
    """
    Given directory `d` and a dict of filenames, return the list of batch lines
    that call REDtoolbox.
    """
    batch = [
        '@ECHO OFF',
        fr'SET _directory="{d}"',
        'md "%_directory%\\output_dir"',
    ]
    red_str = (
        f'{redtoolbox_exe} mapping '
        f'--device dji_multispectral --correction-type ppk '
        f'--output-format "exif" '
        f'--log-file "%_directory%\\{files["MRK"]}" '
        f'--rover-file "%_directory%\\{files["OBS"]}" '
        f'--base-file "%_directory%\\{files["O"]}" '
        f'--nav-file "%_directory%\\{files["P"]}" '
        f'--output-dir "%_directory%\\output_dir" '
        f'-i "%_directory%"'
    )
    batch.append(red_str)
    return batch


def build_batch_commands_M3E(
    d: str,
    files: Dict[str, str],
    redtoolbox_exe: str = 'REDtoolboxCLI.exe'
) -> List[str]:
    """
    Given directory `d` and a dict of filenames, return the list of batch lines
    that call REDtoolbox.
    """
    batch = [
        '@ECHO OFF',
        fr'SET _directory="{d}"',
        'md "%_directory%\\output_dir"',
    ]
    red_str = (
        f'{redtoolbox_exe} mapping '
        f'--device dji --correction-type ppk '
        f'--output-format "exif" '
        f'--geoid-file "D:\\Ecke_Simon\\de_bkg_GCG2016v2023.tif" '
        f'--log-file "%_directory%\\{files["MRK"]}" '
        f'--rover-file "%_directory%\\{files["OBS"]}" '
        f'--base-file "%_directory%\\{files["O"]}" '
        f'--nav-file "%_directory%\\{files["P"]}" '
        f'--output-dir "%_directory%\\output_dir" '
        f'-i "%_directory%"'
    )
    batch.append(red_str)
    return batch

def generate_redtoolbox_batch(
    dirlist_fn: str,
    redtoolbox_dir: str,
    log_dir: str,
    epn_yr: str = '24'
) -> None:
    """
    Orchestrate: read mission list, create log & batch filenames, then
    process each directory in turn, writing both log entries and
    accumulating/appending batch commands.
    """
    start_time = datetime.now()
    today = date.today().isoformat()
    log_fn = os.path.join(
        log_dir,
        f'REDToolBox_CMD_Start_batch_v02_LOG_{today}_{start_time:%H%M%S}.txt'
    )
    batch_fn = os.path.join(
        redtoolbox_dir,
        f'REDToolBox_CMD_Start_batch_ALL_{today}_{start_time:%H%M%S}.bat'
    )

    # initialize files
    write2log(f"Starting batch generation", log_fn)
    # ensure batch file is empty to start
    open(batch_fn, 'w').close()

    dir_li = read_dirlist(dirlist_fn)
    for d in dir_li:
        write2log(f"Processing {d}", log_fn)
        files = find_ppk_files(d, epn_yr)
        for key, fn in files.items():
            write2log(f"    Found {key} file: {fn}", log_fn)

        batch_lines = build_batch_commands(d, files)
        # append to batch file
        with open(batch_fn, 'a+', encoding='utf-8') as bf:
            for line in batch_lines:
                bf.write(line + '\n')

    elapsed = datetime.now() - start_time
    write2log(f"\nTotal time elapsed: {elapsed}", log_fn)
    write2log(f"Batch file written to: {batch_fn}", log_fn)


def generate_redtoolbox_batch_M3E(
    dirlist_fn: str,
    redtoolbox_dir: str,
    log_dir: str,
    epn_yr: str = '24'
) -> None:
    """
    Orchestrate: read mission list, create log & batch filenames, then
    process each directory in turn, writing both log entries and
    accumulating/appending batch commands.
    """
    start_time = datetime.now()
    today = date.today().isoformat()
    log_fn = os.path.join(
        log_dir,
        f'REDToolBox_CMD_Start_batch_v02_LOG_{today}_{start_time:%H%M%S}.txt'
    )
    batch_fn = os.path.join(
        redtoolbox_dir,
        f'REDToolBox_CMD_Start_batch_ALL_{today}_{start_time:%H%M%S}.bat'
    )

    # initialize files
    write2log(f"Starting batch generation", log_fn)
    # ensure batch file is empty to start
    open(batch_fn, 'w').close()

    dir_li = read_dirlist(dirlist_fn)
    for d in dir_li:
        write2log(f"Processing {d}", log_fn)
        files = find_ppk_files(d, epn_yr)
        for key, fn in files.items():
            write2log(f"    Found {key} file: {fn}", log_fn)

        batch_lines = build_batch_commands_M3E(d, files)
        # append to batch file
        with open(batch_fn, 'a+', encoding='utf-8') as bf:
            for line in batch_lines:
                bf.write(line + '\n')

    elapsed = datetime.now() - start_time
    write2log(f"\nTotal time elapsed: {elapsed}", log_fn)
    write2log(f"Batch file written to: {batch_fn}", log_fn)


# copy PPK corrected images to a separate folder
def copy_ppk_images(
    source_folder: str,
    destination_folder: str,
    dirs_exist_ok: bool = True
) -> None:
    """
    Traverse `source_folder`, find any subdirectories whose names contain
    "MEDIA" or "EXIF_images", and copy them (and their contents) into
    `destination_folder`, preserving the relative directory structure.

    Parameters
    ----------
    source_folder : str
        Root directory under which to search for "MEDIA" or "EXIF_images" folders.
    destination_folder : str
        Directory into which matching folders will be copied.
    dirs_exist_ok : bool, default True
        If True, existing directories in the destination will be merged;
        otherwise an error is raised when a target already exists.
    """
    for date_folder in os.listdir(source_folder):
        date_path = os.path.join(source_folder, date_folder)
        if not os.path.isdir(date_path):
            continue

        for flight_folder in os.listdir(date_path):
            flight_path = os.path.join(date_path, flight_folder)
            if not os.path.isdir(flight_path):
                continue

            # Walk the flight folder tree
            for root, dirs, files in os.walk(flight_path):
                for dir_name in dirs:
                    if 'MEDIA' in dir_name or 'EXIF_images' in dir_name:
                        full_dir_path = os.path.join(root, dir_name)

                        # Compute relative path from source_folder
                        relative_path = os.path.relpath(full_dir_path, source_folder)
                        target_path = os.path.join(destination_folder, relative_path)

                        # Copy the directory tree
                        shutil.copytree(full_dir_path, target_path, dirs_exist_ok=dirs_exist_ok)
                        print(f"Copied: {full_dir_path} -> {target_path}")


def move_files_like_subfolders(master_folder, dest_root,
                               ignore_folder_name="output_dir",
                               recursive=False, dry_run=False):
    """
    For each immediate subfolder of `master_folder`, move its files to
    `dest_root/<subfolder_name>`. Skip any folder named `output_dir`.
    If `recursive=True`, also move files from nested subfolders while skipping
    any path that has a folder named `output_dir` in it (preserves relative structure).
    """
    master = Path(master_folder)
    dest_root = Path(dest_root)
    if not master.is_dir():
        raise ValueError(f"Master folder not found: {master}")
    if str(dest_root).startswith(str(master)):
        raise ValueError("Refusing to move into a destination inside the master folder (safety).")

    def has_ignored_part(p: Path) -> bool:
        return any(part.lower() == ignore_folder_name.lower() for part in p.parts)

    def unique_path(p: Path) -> Path:
        if not p.exists():
            return p
        stem, suffix = p.stem, p.suffix
        i = 1
        while True:
            cand = p.with_name(f"{stem} ({i}){suffix}")
            if not cand.exists():
                return cand
            i += 1

    moved_count = 0
    for sub in sorted([p for p in master.iterdir() if p.is_dir()]):
        if sub.name.lower() == ignore_folder_name.lower():
            # ignore top-level output_dir
            continue

        target_dir = dest_root / sub.name
        target_dir.mkdir(parents=True, exist_ok=True)

        if not recursive:
            # only files directly inside the subfolder
            files = [p for p in sub.iterdir() if p.is_file()]
            for f in files:
                dest = unique_path(target_dir / f.name)
                if dry_run:
                    print(f"[DRY] move {f} -> {dest}")
                else:
                    shutil.move(str(f), str(dest))
                    moved_count += 1
        else:
            # move files from sub and all nested subfolders, skipping any path containing output_dir
            for f in sub.rglob("*"):
                if f.is_file() and not has_ignored_part(f):
                    rel = f.relative_to(sub)  # preserve structure under target_dir
                    dest = unique_path((target_dir / rel).parent / rel.name)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if dry_run:
                        print(f"[DRY] move {f} -> {dest}")
                    else:
                        shutil.move(str(f), str(dest))
                        moved_count += 1

    print(f"Done. Moved {moved_count} file(s).")


def list_folders(master_folder: Union[str, Path],
                 output_txt: Optional[Union[str, Path]] = None,
                 recursive: bool = False) -> List[str]:
    """
    Collect folder paths inside `master_folder`.

    Parameters
    ----------
    master_folder : str | Path
        The base directory to scan.
    output_txt : str | Path | None
        If given, write the list to this text file (UTF-8, one path per line).
    recursive : bool
        If True, include all nested subfolders; otherwise only direct children.

    Returns
    -------
    List[str]
        Sorted absolute folder paths.
    """
    base = Path(master_folder).expanduser()
    if not base.exists() or not base.is_dir():
        raise ValueError(f"Not a folder: {base}")

    # Gather directories
    it = base.rglob("*") if recursive else base.iterdir()
    dirs = [p for p in it if p.is_dir()]

    # Sort case-insensitively, return absolute paths
    paths = sorted((str(p.resolve()) for p in dirs), key=str.lower)

    if output_txt is not None:
        out = Path(output_txt).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(paths) + ("\n" if paths else ""), encoding="utf-8")

    return paths