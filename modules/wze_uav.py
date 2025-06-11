
import os
import re
import pandas as pd
import shutil
import errno
import ntpath
from pathlib import Path
from datetime import date, datetime
from typing import List, Dict, Optional



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
    Within directory `d`, locate the MRK, Rinex.obs, base (.o), and nav (.p) files.
    Returns a dict with keys 'MRK', 'OBS', 'O', 'P' and their filenames.
    """
    patterns = {
        'MRK': '*.MRK',
        'OBS': '*Rinex.obs',
        'O': f'*.{epn_yr}o',
        'P': f'*.{epn_yr}p',
    }
    found = {}
    for key, pat in patterns.items():
        files = list(Path(d).rglob(pat))
        if not files:
            raise FileNotFoundError(f"No files matching {pat} in {d}")
        # take the first match
        found[key] = ntpath.basename(str(files[0]))
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