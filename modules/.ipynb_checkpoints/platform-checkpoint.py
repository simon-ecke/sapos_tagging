######### DJI Zenmuse L2 Functions ##########################################

def find_mrk_file(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.mrk'):
                return os.path.join(root, file)
    return None

def get_sorted_jpg_files(directory):
    jpgs = [f for f in os.listdir(directory) if f.lower().endswith('.jpg')]
    jpgs.sort()
    return jpgs

def convert_gps_time(gps_time_berlin):
    """Convert a naive Berlin‑time datetime (GPS) → UTC datetime, accounting for leap seconds."""
    gps_epoch = datetime(1980, 1, 6, tzinfo=pytz.utc)
    leap_seconds = 18

    berlin = pytz.timezone('Europe/Berlin')
    gps_time_berlin = berlin.localize(gps_time_berlin) if gps_time_berlin.tzinfo is None else gps_time_berlin.astimezone(berlin)
    gps_time_utc = gps_time_berlin.astimezone(pytz.utc)

    delta = gps_time_utc - gps_epoch
    return gps_epoch + timedelta(seconds=delta.total_seconds() - leap_seconds)

def process_mrk_file_and_jpg(mrk_path):
    """Process a DJI *.MRK file + JPGs → print & write SAPOS query string."""
    path = os.path.dirname(mrk_path)
    jpg_files = get_sorted_jpg_files(path)
    if not jpg_files:
        raise FileNotFoundError('No JPG files found next to the MRK file.')

    # --- start / end timestamps (UTC) ---------------------------------------
    def _ts_from_name(name):
        m = re.search(r'DJI_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})', name)
        return datetime(*(int(m.group(i)) for i in range(1, 6)))

    start_dt = convert_gps_time(_ts_from_name(os.path.basename(mrk_path)))
    end_dt   = convert_gps_time(_ts_from_name(jpg_files[-1]))

    buffer_min = 10
    duration = ceil((end_dt - start_dt).total_seconds() / 60 + 2 * buffer_min)

    start_dt_earlier = start_dt - timedelta(minutes=buffer_min)
    formatted_time = start_dt_earlier.strftime('%H:%M:%S')
    formatted_date = start_dt_earlier.strftime('%d.%m.%Y')

    # --- coordinates & elevation -------------------------------------------
    with open(mrk_path, 'r', encoding='utf-8') as fh:
        lines = fh.readlines()

    def _lat_lon(line):
        parts = line.split()
        return float(parts[6].split(',')[0]), float(parts[7].split(',')[0])

    lat_first, lon_first = _lat_lon(lines[0])
    lat_last , lon_last  = _lat_lon(lines[-1])
    latitude  = (lat_first + lat_last) / 2
    longitude = (lon_first + lon_last) / 2
    elevation = round(float(lines[len(lines)//2].split()[8].split(',')[0]))

    flight_name = os.path.basename(mrk_path).split('_')[3]

    sapos_str = f"""{str(latitude).replace('.', ',')}   {str(longitude).replace('.', ',')}   {elevation}   {formatted_date}   {formatted_time}   {duration}   1   R3   {flight_name}"""
    sapos_file = os.path.join(path, '@sapos_query.txt')
    with open(sapos_file, 'w', encoding='utf-8') as fh:
        fh.write(sapos_str.strip())

    print('📄', sapos_str)
    print('✅ SAPOS query written to', sapos_file)
