import os
import pandas as pd
from pathlib import Path
from typing import Union


def read_metadata(metadata_path: Union[str, Path]) -> pd.DataFrame:
    """
    Read metadata tracker CSV

    Returns
    -------
    pd.DataFrame

    Raises
    ------
    FileNotFoundError
        If metadata tracker CSV not found
    """
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f'File {metadata_path} does not exist')

    try:
        return pd.read_csv(metadata_path)
    except pd.errors.ParserError:
        raise ValueError(f'Error parsing CSV file at {metadata_path}')


def write_to_metadata_tracker(metadata_path: Union[str, Path], qc_dict: dict, metadata: pd.DataFrame = None):
    """
    Append or update QC metrics in metadata tracker CSV
    """
    if metadata is None:
        try:
            metadata = read_metadata(metadata_path)
        except FileNotFoundError as e:
            # Never auto-create the tracker: a missing file almost always means a
            # misconfigured path, and silently creating a new CSV would orphan the
            # run instead of appending to the canonical tracker.
            raise FileNotFoundError(
                f"Metadata tracker not found at {metadata_path}. The tracker is not "
                f"auto-created; verify config['qc_dir'] points to the existing tracker "
                f"before running QC."
            ) from e

    barcode = qc_dict['barcode']
    barcode_row = metadata[metadata['barcode'] == barcode]

    if not barcode_row.empty:
        idx = barcode_row.index[0]
        for key, val in qc_dict.items():
            if key in metadata.columns:
                if key == 'barcode' or val is None or pd.isna(val):
                    continue
                if pd.isna(metadata.loc[idx, key]):
                    metadata.loc[idx, key] = val

        save_metadata_csv(metadata, metadata_path)
    else:
        try:
            metadata.loc[len(metadata)] = qc_dict
            save_metadata_csv(metadata, metadata_path)
        except Exception as e:
            print(f'Error writing to metadata tracker: {e}')
            return


def update_column(metadata_path: Union[str, Path], barcode: str, column: str, value, metadata: pd.DataFrame = None):
    """
    Update a specific column for a given barcode
    """
    if metadata is None:
        metadata = read_metadata(metadata_path)

    barcode_row = metadata[metadata['barcode'] == barcode]

    if not barcode_row.empty:
        idx = barcode_row.index[0]
        metadata.loc[idx, column] = value
        save_metadata_csv(metadata, metadata_path)
    else:
        print(f'Barcode {barcode} not found in metadata tracker')


def save_metadata_csv(metadata: pd.DataFrame, metadata_path: Union[str, Path]):
    """
    Save metadata DataFrame as CSV
    """
    Path(metadata_path).parent.mkdir(parents=True, exist_ok=True)
    metadata.reset_index(drop=True, inplace=True)
    metadata.drop_duplicates(inplace=True)
    metadata.to_csv(metadata_path, index=False)


def get_metadata(metadata_path: Union[str, Path], species: str = "", project: str = ""):
    """
    Get filtered subset of metadata by species or project
    """
    metadata = read_metadata(metadata_path)

    if species != "":
        return metadata[metadata['species'] == species.lower()]
    elif project != "":
        return metadata[metadata['project'] == project.lower()]
    else:
        return metadata
