
import os
import re
import pandas as pd

def extract_and_dump_fplans(
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
        Path to the SAPOS queries file (currently unused but kept for consistency).
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
