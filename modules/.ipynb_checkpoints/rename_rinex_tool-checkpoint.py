import os
from modules.platform import *

#def generate_sapos_query(data_dir):
#    """Detect Wingtra or DJI-L2 flight in *data_dir* and return the SAPOS line."""
#    if not os.path.isdir(data_dir):
#        raise FileNotFoundError(f"Directory not found: {data_dir}")
#
#    json_fp = find_json_file(data_dir)
#    if json_fp:
#        # ─── Wingtra ─────────────────────────────────────────────────────────
#        print("🛩 Detected Wingtra dataset")
#        lat, lon, alt = extract_coordinates(json_fp)
#        alt += 120
#        s_ts, e_ts = extract_timestamps(json_fp)
#        s_ts -= 300_000
#        e_ts += 300_000
#        duration    = int(round((e_ts - s_ts) / 1000 / 60 + 1))
#        dt_str      = gps_time_to_utc(s_ts)
#        flight_name = "_".join(os.path.basename(os.path.dirname(os.path.dirname(json_fp))).split())
#
#        sapos_str = f"{lat:.6f} {lon:.6f} {int(alt)} {dt_str} {duration} 1 R3 {flight_name}"
#        (Path(data_dir) / "@sapos_query.txt").write_text(sapos_str + "\n", encoding="utf-8")
#
#        print("📄", sapos_str)
#        print("✅ SAPOS query written")
#        return sapos_str          # ←─────────── this was missing
#    else:
#        # ─── DJI L2 ─────────────────────────────────────────────────────────
#        mrk_fp = find_mrk_file(data_dir)
#        if mrk_fp is None:
#            raise FileNotFoundError("No Wingtra JSON or DJI MRK file found.")
#        print("🚁 Detected DJI Zenmuse L2 dataset")
#
#        sapos_str = process_mrk_file_and_jpg(mrk_fp)   # make this helper **return** its string
#        return sapos_str          # ←─────────── also return here


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