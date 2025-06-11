# modules/sapos_batch.py
from pathlib import Path
from typing import Union            

from modules.sapos_query import generate_sapos_query, generate_sapos_query_v2

def batch_generate_sapos_queries(
        root_dir: str,
        master_out: Union[str, Path] = "all_sapos_queries.txt",
        *,
        recurse: bool = False) -> None:
    """
    Run generate_sapos_query on every flight folder inside *root_dir*
    and collect their lines into *master_out*.

    *master_out* can be:
      • a filename   -> that exact file is created/overwritten
      • a directory  -> we drop 'all_sapos_queries.txt' inside it
    """
    root_dir   = Path(root_dir)
    master_out = Path(master_out).expanduser()

    # ──► if the user passed a directory, pick a default file inside it
    if master_out.is_dir() or master_out.suffix == "":
        master_out = master_out / "all_sapos_queries.txt"
    # ◄───────────────────────────────────────────────────────────────────────

    folders = (
        (p for p in root_dir.rglob("*") if p.is_dir()) if recurse
        else (p for p in root_dir.iterdir() if p.is_dir())
    )

    lines_written = 0
    with master_out.open("w", encoding="utf-8") as master:
        for fld in folders:
            try:
                line = generate_sapos_query(fld)    # <- must return str
                master.write(line + "\n")
                lines_written += 1
                print(f"✅ {fld.name}")
            except Exception as exc:
                print(f"❌ skipping {fld.name}: {exc}")

    print(f"\n📝  {lines_written} query line(s) saved to {master_out.resolve()}")


# for nested folder structure

def batch_generate_sapos_queries_v2(
        root_dir: str,
        master_out: Union[str, Path] = "all_sapos_queries_v2.txt",
        *,
        recurse: bool = False) -> None:
    root = Path(root_dir)
    master_out = Path(master_out).expanduser()
    if master_out.is_dir() or master_out.suffix == "":
        master_out = master_out / "all_sapos_queries_v2.txt"

    folders = []
    if not recurse:
        # Only two levels: date_folder → flight_folder
        for date_folder in root.iterdir():
            if not date_folder.is_dir():
                continue
            for flight_folder in date_folder.iterdir():
                if flight_folder.is_dir():
                    folders.append(flight_folder)
    else:
        # Walk all subfolders but select exactly those at depth two under root:
        for p in root.rglob("*"):
            if not p.is_dir():
                continue
            try:
                rel = p.relative_to(root).parts
            except Exception:
                continue
            if len(rel) == 2:
                folders.append(p)

    lines_written = 0
    with master_out.open("w", encoding="utf-8") as master:
        for fld in folders:
            try:
                line = generate_sapos_query_v2(str(fld))
                master.write(line + "\n")
                lines_written += 1
                print(f"✅ {fld.relative_to(root)}")
            except Exception as exc:
                print(f"❌ skipping {fld.relative_to(root)}: {exc}")

    print(f"\n📝  {lines_written} query line(s) saved to {master_out.resolve()}")