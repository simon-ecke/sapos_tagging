"""
sapos_query.py – to create strings for SAPOS queries
"""

import os
from modules.platform import *

def generate_sapos_query(data_dir: str) -> str:
    """Return one SAPOS query line for *data_dir*."""
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"{data_dir} is not a directory")

    # ── 1) Wingtra ────────────────────────────────────────────────────────
    json_fp = find_json_file(data_dir)
    if json_fp:
        print("🛩 Detected Wingtra dataset")
        lat, lon, alt = extract_coordinates(json_fp)
        alt += 120
        s_ts, e_ts = extract_timestamps(json_fp)
        s_ts -= 300_000;  e_ts += 300_000
        duration  = int(round((e_ts - s_ts) / 1000 / 60 + 1))
        dt_str    = gps_time_to_utc(s_ts)
        flight    = "_".join(Path(json_fp).parents[1].name.split())
        line = f"{lat:.6f} {lon:.6f} {int(alt)} {dt_str} {duration} 1 R3 {flight}"
        Path(data_dir, "@sapos_query.txt").write_text(line + "\n", encoding="utf-8")
        print("📄", line);  print("✅ SAPOS query written");  return line

    # ── 2) DJI MRK-based flights ─────────────────────────────────────────
    #     • .LDR present  →  Zenmuse L2
    #     • no .LDR       →  Mavic 3 Enterprise (same MRK parser)
    ldr_fp = find_ldr_file(data_dir)
    mrk_fp = find_mrk_file(data_dir)
    if mrk_fp:
        if ldr_fp:
            print("🚁 Detected DJI Zenmuse L2 dataset")
        else:
            print("🛸 Detected DJI Mavic 3 Enterprise dataset")
        return process_mrk_file_and_jpg(mrk_fp)

    # ── 3) nothing matched ───────────────────────────────────────────────
    raise FileNotFoundError("No Wingtra JSON or DJI MRK found in folder")


# ────────────────────────────────────────────────────────────────────────────
# New generate_sapos_query_v2 for nested folder structure (WZE-UAV)
# ────────────────────────────────────────────────────────────────────────────
def generate_sapos_query_v2(data_dir: str) -> str:
    """
    Like the original, but always uses process_mrk_file_and_jpg_v2 for DJI.
    """
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"{data_dir} is not a directory")

    # 1) Wingtra (unchanged)
    json_fp = find_json_file(data_dir)
    if json_fp:
        print("🛩 Detected Wingtra dataset (v2)")
        lat, lon, alt = extract_coordinates(json_fp)
        alt += 120
        s_ts, e_ts = extract_timestamps(json_fp)
        s_ts -= 300_000
        e_ts += 300_000
        duration = int(round((e_ts - s_ts) / 1000 / 60 + 1))
        dt_str = gps_time_to_utc(s_ts)

        flight = "_".join(Path(data_dir).name.split())
        line = f"{lat:.6f} {lon:.6f} {int(alt)} {dt_str} {duration} 1 R3 {flight}"
        Path(data_dir, "@sapos_query.txt").write_text(line + "\n", encoding="utf-8")
        print("📄", line)
        print("✅ SAPOS query written")
        return line

    # 2) DJI MRK (always EXIF-based v2)
    ldr_fp = find_ldr_file(data_dir)
    mrk_fp = find_mrk_file(data_dir)
    if mrk_fp:
        if ldr_fp:
            print("🚁 Detected DJI Zenmuse L2 dataset (v2)")
        else:
            print("🛸 Detected DJI Phantom 3 Multispectral dataset (v2)")
        # Only one call: the two-argument v2 helper
        return process_mrk_file_and_jpg_v2(mrk_fp, data_dir)

    # 3) Nothing matched
    raise FileNotFoundError("No Wingtra JSON or DJI MRK found (v2)")
