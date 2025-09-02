from pathlib import Path
import re
import shutil

# --- Patterns ---
# Folder: DJI_YYYYMMDDHHMM_<ID>
FOLDER_RE = re.compile(r"^DJI_\d{12}_([A-Za-z0-9]+)$")
# File:   <ID>_something.ext
FILE_RE   = re.compile(r"^([A-Za-z0-9]+)_.+$")

def build_folder_map(master: Path):
    """Return ({ID: folder_path}, duplicates_dict) for DJI folders in master."""
    by_id = {}
    dups = {}
    for p in master.iterdir():
        if p.is_dir():
            m = FOLDER_RE.match(p.name)
            if m:
                id_ = m.group(1)
                if id_ in by_id:
                    dups.setdefault(id_, [by_id[id_]]).append(p)
                else:
                    by_id[id_] = p
    return by_id, dups

def plan_moves(master: Path, id_to_folder: dict):
    """Return list of (src_file, dest_file) pairs to move."""
    planned = []
    for p in master.iterdir():
        if p.is_file():
            m = FILE_RE.match(p.name)
            if not m:
                continue
            id_ = m.group(1)
            dest_dir = id_to_folder.get(id_)
            if dest_dir is None:
                continue
            planned.append((p, dest_dir / p.name))
    return planned

def resolve_conflict(dest: Path):
    """Create a unique name by appending _1, _2, ... before the extension."""
    base, ext = dest.stem, dest.suffix
    parent = dest.parent
    i = 1
    while True:
        candidate = parent / f"{base}_{i}{ext}"
        if not candidate.exists():
            return candidate
        i += 1

def organize_files(master_dir, rename_on_conflict=False):
    """
    Set rename_on_conflict=True to show the auto-rename that would happen if destination exists.
    """
    master = Path(master_dir).resolve()
    if not master.is_dir():
        raise NotADirectoryError(master)

    id_to_folder, dups = build_folder_map(master)
    if dups:
        print("WARNING: Duplicate IDs mapped to multiple folders:")
        for k, paths in dups.items():
            print(f"  {k}:")
            for p in paths:
                print(f"    - {p}")

    planned = plan_moves(master, id_to_folder)
    if not planned:
        print("No matching files found to move.")
        return

    print(f"Found {len(planned)} file(s) that are placed into matching folders.\n")

    moves_count = 0
    for src, dest in planned:
        final_dest = dest
        if dest.exists():
            if rename_on_conflict:
                final_dest = resolve_conflict(dest)
                print(f"DRY-RUN rename+move : {src.name} -> {final_dest}")
                moves_count += 1
            else:
                print(f"SKIP (exists)       : {src.name} -> {dest}")
                continue
        else:
            print(f"DRY-RUN move        : {src.name} -> {final_dest}")
            moves_count += 1

        final_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(final_dest))

    print(f"\n Complete. {moves_count} move(s) performed.")
