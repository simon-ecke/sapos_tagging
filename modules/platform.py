# platform.py
# ---------------------------------------------------------------------------
# Helper functions for Wingtra and DJI Zenmuse L2 datasets
#
# • Wingtra:   find first JSON → extract coordinates + timestamps
# • DJI Zenmuse L2:    find MRK + JPGs → build SAPOS query string
# • DJI Mavic 3 Enterprise:    find MRK + JPGs → build SAPOS query string
#
# Every helper is written so that higher-level code (generate_sapos_query)
# can call it and—critically—*get the query string back*.
# ---------------------------------------------------------------------------

import os
import re
import time
from datetime import datetime, timedelta
from math import ceil
from typing import Optional, Union, List
from pathlib import Path
import exifread
import pytz


# ────────────────────────────────────────────────────────────────────────────
#  Wingtra helpers
# ────────────────────────────────────────────────────────────────────────────
def find_json_file(directory: str) -> Optional[str]:
    """Return the first *.json file found recursively under *directory*."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".json"):
                return os.path.join(root, file)
    return None


def extract_coordinates(file_path: str) -> List[float]:
    """Return [lat, lon, alt] extracted from the Wingtra JSON."""
    coords: List[float] = []
    with open(file_path, "r", encoding="utf-8") as fh:
        for line in fh:
            if '"coordinate"' in line:
                for _ in range(3):
                    val = next(fh)
                    m = re.search(r'"(-?\d+\.\d+)"', val)
                    if m:
                        coords.append(float(m.group(1)))
                break
    if len(coords) != 3:
        raise ValueError("Could not extract three coordinates from JSON")
    return coords


def extract_timestamps(file_path: str):
    """Return (first_ts, last_ts) in GPS-milliseconds from the Wingtra JSON."""
    first, last = None, None
    with open(file_path, "r", encoding="utf-8") as fh:
        for line in fh:
            if '"timestamp"' in line:
                m = re.search(r'"timestamp":\\s*"(\d+\\.\\d+)"', line)
                if m:
                    ts = float(m.group(1))
                    first = first or ts
                    last = ts
    if first is None or last is None:
        raise ValueError("No timestamps found in JSON")
    return first, last


def gps_time_to_utc(gps_ms: float) -> str:
    """Convert GPS ms (since 1980-01-06) → 'dd.mm.yyyy HH:MM:SS' (UTC)."""
    return time.strftime("%d.%m.%Y %H:%M:%S", time.gmtime(int(gps_ms / 1000)))


# ────────────────────────────────────────────────────────────────────────────
#  DJI Zenmuse L2 + Mavic 3 Enterprise helpers 
# ────────────────────────────────────────────────────────────────────────────

# .LDR file unique for Zenmuse L2!
def find_ldr_file(dir_: str) -> Optional[str]:
    for f in os.listdir(dir_):
        if f.lower().endswith(".ldr"):
            return os.path.join(dir_, f)
    return None

def find_mrk_file(directory: str) -> Optional[str]:
    """Return the first *.MRK file found recursively under *directory*."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".mrk"):
                return os.path.join(root, file)
    return None


def get_sorted_jpg_files(directory: str):
    """Alphabetically sorted list of JPG filenames in *directory*."""
    return sorted(f for f in os.listdir(directory) if f.lower().endswith(".jpg"))


def convert_gps_time(gps_time_berlin: datetime) -> datetime:
    """Convert naive Berlin-time datetime (GPS) → UTC datetime."""
    gps_epoch = datetime(1980, 1, 6, tzinfo=pytz.utc)
    leap_seconds = 18

    berlin = pytz.timezone("Europe/Berlin")
    gps_time_berlin = (
        berlin.localize(gps_time_berlin)
        if gps_time_berlin.tzinfo is None
        else gps_time_berlin.astimezone(berlin)
    )
    gps_time_utc = gps_time_berlin.astimezone(pytz.utc)

    delta = gps_time_utc - gps_epoch
    return gps_epoch + timedelta(seconds=delta.total_seconds() - leap_seconds)


def process_mrk_file_and_jpg(mrk_path: str) -> str:
    """
    Build SAPOS query string from a DJI *.MRK file + JPGs,
    write '@sapos_query.txt' next to the MRK,
    and **return the string**.
    """
    path = os.path.dirname(mrk_path)
    jpg_files = get_sorted_jpg_files(path)
    if not jpg_files:
        raise FileNotFoundError("No JPG files next to the MRK file.")

    # start / end timestamps
    def _dt_from_name(name: str) -> datetime:
        m = re.search(r"DJI_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})", name)
        return datetime(*(int(m.group(i)) for i in range(1, 6)))

    start_dt = convert_gps_time(_dt_from_name(os.path.basename(mrk_path)))
    end_dt   = convert_gps_time(_dt_from_name(jpg_files[-1]))

    buffer_min = 10
    duration = ceil((end_dt - start_dt).total_seconds() / 60 + 2 * buffer_min)

    start_dt_earlier = start_dt - timedelta(minutes=buffer_min)
    formatted_date = start_dt_earlier.strftime("%d.%m.%Y")
    formatted_time = start_dt_earlier.strftime("%H:%M:%S")

    # coordinates & elevation
    with open(mrk_path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    def _lat_lon(line: str):
        parts = line.split()
        return float(parts[6].split(",")[0]), float(parts[7].split(",")[0])

    lat_first, lon_first = _lat_lon(lines[0])
    lat_last, lon_last   = _lat_lon(lines[-1])

    latitude  = (lat_first + lat_last) / 2
    longitude = (lon_first + lon_last) / 2
    elevation = round(float(lines[len(lines) // 2].split()[8].split(",")[0]))

    flight_name = os.path.basename(mrk_path).split("_")[3]

    sapos_str = (
        f"{str(latitude).replace('.', ',')}   "
        f"{str(longitude).replace('.', ',')}   "
        f"{elevation}   {formatted_date}   {formatted_time}   {duration}   1   R3   {flight_name}"
    )

    sapos_file = os.path.join(path, "@sapos_query.txt")
    with open(sapos_file, "w", encoding="utf-8") as fh:
        fh.write(sapos_str.strip())

    print("📄", sapos_str)
    print("✅ SAPOS query written to", sapos_file)
    return sapos_str


# ── New “EXIF‐based v2” helper ────────────────────────────────────────────────
def process_mrk_file_and_jpg_v2(mrk_path: str, flight_dir: str) -> str:
    """
    EXIF‐based v2 helper that treats `flight_dir` itself as the flight folder.
    Steps:
      1) Validate that `flight_dir` is indeed a directory.
      2) Find any MRK under flight_dir (mrk_path is that file).
      3) Gather all JPGs under flight_dir (no matter how deep).
      4) Read the first & last JPG’s EXIF DateTimeOriginal → naive Berlin time.
      5) Convert both to GPS‐UTC via convert_gps_time_v2.
      6) Buffer by 10 min, compute duration.
      7) Read MRK for lat/lon/elev (first, last, middle‐line).
      8) Write @sapos_query.txt into flight_dir.
      9) Use flight_dir.name as the SAPOS “flight” field.
    """
    flight_folder = Path(flight_dir)
    if not flight_folder.is_dir():
        raise FileNotFoundError(f"{flight_folder} is not a directory")

    # 3) Gather all JPGs anywhere under flight_folder
    jpg_paths = sorted(flight_folder.rglob("*.jpg"))
    if not jpg_paths:
        raise FileNotFoundError(f"No JPG files found under flight folder: {flight_folder}")

    # 4) Read EXIF DateTimeOriginal from first & last JPG
    def _get_exif_datetime(jpg_path: Path) -> datetime:
        with open(jpg_path, "rb") as f:
            tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal")
        dto = tags.get("EXIF DateTimeOriginal")
        if dto is None:
            raise ValueError(f"No EXIF DateTimeOriginal in: {jpg_path}")
        naive = datetime.strptime(str(dto), "%Y:%m:%d %H:%M:%S")
        return naive  # Berlin local time

    start_naive = _get_exif_datetime(jpg_paths[0])
    end_naive   = _get_exif_datetime(jpg_paths[-1])

    # 5) Convert both to GPS‐UTC via v2 converter
    start_dt = convert_gps_time(start_naive)
    end_dt   = convert_gps_time(end_naive)

    # 6) Buffer and compute duration (minutes)
    buffer_min = 10
    duration = ceil((end_dt - start_dt).total_seconds() / 60 + 2 * buffer_min)

    start_dt_earlier = start_dt - timedelta(minutes=buffer_min)
    formatted_date  = start_dt_earlier.strftime("%d.%m.%Y")
    formatted_time  = start_dt_earlier.strftime("%H:%M:%S")

    # 7) Read MRK file (mrk_path) for coords & elevation
    with open(mrk_path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    if not lines:
        raise ValueError(f"MRK file is empty: {mrk_path}")

    def _lat_lon(line: str):
        parts = line.split()
        return float(parts[6].split(",")[0]), float(parts[7].split(",")[0])

    lat_first, lon_first = _lat_lon(lines[0])
    lat_last, lon_last   = _lat_lon(lines[-1])
    latitude  = (lat_first + lat_last) / 2
    longitude = (lon_first + lon_last) / 2
    elevation = round(float(lines[len(lines) // 2].split()[8].split(",")[0]))

    # 8) Flight name is flight_folder.name
    flight_name = flight_folder.name

    sapos_str = (
        f"{str(latitude).replace('.', ',')}   "
        f"{str(longitude).replace('.', ',')}   "
        f"{elevation}   {formatted_date}   {formatted_time}   {duration}   1   R3   {flight_name}"
    )

    # 9) Write into flight_folder/@sapos_query.txt
    sapos_file = flight_folder / "@sapos_query.txt"
    with open(sapos_file, "w", encoding="utf-8") as fh:
        fh.write(sapos_str.strip())

    print("📄", sapos_str)
    print("✅ SAPOS query written to", sapos_file)
    return sapos_str

