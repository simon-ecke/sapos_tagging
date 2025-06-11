def generate_sapos_query(data_dir):
    """Detect Wingtra vs. DJI L2 in *data_dir* and generate SAPOS query."""
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"Directory not found: {data_dir}")

    json_fp = find_json_file(data_dir)
    if json_fp:
        # --- Wingtra --------------------------------------------------------
        print('🛩 Detected Wingtra dataset')
        lat, lon, alt = extract_coordinates(json_fp)
        alt += 120  # raise virtual station to flight height
        start_ts, end_ts = extract_timestamps(json_fp)
        start_ts -= 300_000  # −5 min buffer
        end_ts   += 300_000  # +5 min buffer
        duration = int(round((end_ts - start_ts) / 1000 / 60 + 1))
        datetime_str = gps_time_to_utc(start_ts)
        flight_name = '_'.join(os.path.basename(os.path.dirname(os.path.dirname(json_fp))).split())
        sapos_str = f"{lat:.6f} {lon:.6f} {int(alt)} {datetime_str} {duration} 1 R3 {flight_name}"
        sapos_file = os.path.join(data_dir, '@sapos_query.txt')
        with open(sapos_file, 'w', encoding='utf-8') as fh:
            fh.write(sapos_str)
        print('📄', sapos_str)
        print('✅ SAPOS query written to', sapos_file)
    else:
        # --- DJI L2 ---------------------------------------------------------
        mrk_fp = find_mrk_file(data_dir)
        if mrk_fp is None:
            raise FileNotFoundError('No Wingtra JSON or DJI MRK file found.')
        print('🚁 Detected DJI Zenmuse L2 dataset')
        process_mrk_file_and_jpg(mrk_fp)
