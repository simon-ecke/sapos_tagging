from pathlib import Path
import shutil

def _next_unique_name(base: str, ext: str, dest_root: Path, used_names: set) -> str:
    """
    Reserve a unique filename in dest_root like:
    base.ext, base_1.ext, base_2.ext, ...
    Avoids collisions with both the filesystem and names already planned this run.
    """
    i = 0
    while True:
        name = f"{base}{ext}" if i == 0 else f"{base}_{i}{ext}"
        if (name not in used_names) and not (dest_root / name).exists():
            used_names.add(name)
            return name
        i += 1

def move_las(master_dir, las_dest_dir, recursive=True, standardize_ext=True):
    """
    - master_dir: path to the folder containing multiple project folders
    - las_dest_dir: destination folder to collect all LAS files (e.g. "/path/to/master/las")
    - recursive: if True, find .las files also in subfolders of each project folder
    - standardize_ext: if True, rename extension to '.las' (lowercase)

    Notes:
    - Explicitly ignores .zip files.
    - Each .las file is renamed to the *top-level project folder* name, with _1, _2… added if needed.
    """
    master = Path(master_dir).resolve()
    dest_root = Path(las_dest_dir).resolve()

    if not master.is_dir():
        raise NotADirectoryError(f"Not a directory: {master}")
    if dest_root == master:
        raise ValueError("Destination folder must not be the same as the master folder.")

    # Get top-level project folders (exclude the destination folder if it's inside master)
    top_level_folders = [p for p in master.iterdir() if p.is_dir()]
    top_level_folders = [p for p in top_level_folders if p.resolve() != dest_root.resolve()]

    plan = []
    used_names = set()  # reserve names during this run to avoid duplicate targets
    for proj in sorted(top_level_folders, key=lambda x: x.name):
        # Gather files inside this project folder
        candidates = (p for p in proj.rglob("*") if p.is_file()) if recursive else \
                     (p for p in proj.iterdir() if p.is_file())

        for src in candidates:
            suffix = src.suffix.lower()

            # --- Explicitly ignore .zip files ---
            if suffix == ".zip":
                continue

            # Only handle .las files
            if suffix != ".las":
                continue

            # New base name is the *top-level* project folder name
            base = proj.name
            ext = ".las" if standardize_ext else src.suffix

            # Reserve a unique destination name like base.las, base_1.las, ...
            dest_name = _next_unique_name(base, ext, dest_root, used_names)
            dest_path = dest_root / dest_name

            plan.append((src, dest_path))

    if not plan:
        print("No .las files found to move.")
        return

    # Print plan
    print(f"Found {len(plan)} .las file(s) to place into: {dest_root}")

    for src, dest in plan:
        print(f"DRY-RUN move: {src}  ->  {dest}")

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))

    print(f"\nRun complete. {len(plan)} move(s) performed.")
