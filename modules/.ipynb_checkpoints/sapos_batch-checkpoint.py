import os
from pathlib import Path
from sapos_utils import generate_sapos_query   # your existing function

def batch_generate_sapos_queries(root_dir: str,
                                 master_out: str | Path = "all_sapos_queries.txt",
                                 *,
                                 recurse: bool = False) -> None:
    """
    Run `generate_sapos_query` on *every* flight folder inside *root_dir*.

    Parameters
    ----------
    root_dir : str
        A directory whose sub-folders are the individual Wingtra / DJI-L2 flights.
    master_out : str | Path, default 'all_sapos_queries.txt'
        File where **all** query strings are appended (one line per flight).
    recurse : bool, default False
        • False → only the first level of sub-folders is processed.<br>
        • True  → walk the entire tree beneath *root_dir*.
    """
    root_dir  = Path(root_dir)
    master_out = Path(master_out).expanduser()

    folders = (
        (p for p in root_dir.rglob("*") if p.is_dir())
        if recurse else
        (p for p in root_dir.iterdir() if p.is_dir())
    )

    with master_out.open("w", encoding="utf-8") as master:
        for fld in folders:
            try:
                # write the per-flight @sapos_query.txt where the data live
                generate_sapos_query(fld)

                # read the freshly written line back
                qfile = fld / "@sapos_query.txt"
                if qfile.exists():
                    master.write(qfile.read_text(encoding="utf-8").strip() + "\n")
                    print(f"✅  {fld.name} done")
                else:
                    print(f"⚠️   {fld.name}: no @sapos_query.txt produced")

            except Exception as exc:
                print(f"❌  skipping {fld}: {exc}")

    print(f"\n📝  All queries collected in {master_out.resolve()}\n")
