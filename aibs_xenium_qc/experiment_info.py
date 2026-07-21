from pathlib import Path
import json
import os
import re
from datetime import datetime
from typing import Union
import pandas as pd
import xenquaco.data_processing as data_processing


metadata_dir = os.path.join(os.path.dirname(__file__), '..', 'metadata')

config = data_processing.process_input(Path(metadata_dir, "config.json"))
panel_mapping = data_processing.process_input(Path(metadata_dir, 'panel_mapping.json'))
xenium_mapping = data_processing.process_input(Path(metadata_dir, 'xenium_mapping.json'))


def get_paths_dict(experiment_id: Union[str, int],
                   barcode: Union[str, int] = None,
                   species: str = "",
                   gene_panel: str = "",
                   config: dict = config):
    """
    Creates dictionary with all relevant paths for a Xenium experiment
    """
    experiment_id = str(experiment_id)
    paths_dict = {}

    if barcode is None:
        barcode = get_barcode(experiment_id)
    barcode = str(barcode)

    experiment_path = Path(config['xenium_output_dir'], experiment_id)

    # Experiment outputs
    paths_dict['experiment_path'] = Path(experiment_path)
    paths_dict['transcripts_path'] = Path(experiment_path, 'transcripts.parquet')
    paths_dict['high_res_dapi_image_path'] = Path(experiment_path, 'morphology.ome.tif')
    paths_dict['metrics_summary_path'] = Path(experiment_path, 'metrics_summary.csv')

    # QC output paths
    paths_dict['qc_metadata_tracker'] = Path(config['qc_dir'], 'qc_metadata_trackers',
                                             'xenium_qc_metadata_tracker.csv')
    paths_dict['qc_output_path'] = Path(config['qc_dir'], 'qc_data', barcode)

    # Ilastik
    paths_dict['ilastik_program_path'] = Path(config['ilastik_program_path'])

    # Convert Path to str for JSON serialization
    for key, val in paths_dict.items():
        if isinstance(val, Path):
            paths_dict[key] = str(val)

    # Create QC output directory
    Path(paths_dict['qc_output_path']).mkdir(parents=True, exist_ok=True)

    # Save paths_dict as JSON
    with open(Path(paths_dict['qc_output_path'], 'paths.json'), 'w') as outfile:
        json.dump(paths_dict, outfile, indent=4)

    return paths_dict


def get_info_dict(paths_dict: dict,
                  experiment_id: Union[str, int] = '',
                  barcode: Union[str, int] = None,
                  species: str = "",
                  gene_panel: str = "",
                  panel_mapping: dict = panel_mapping):
    """
    Creates dictionary with experiment information/metadata
    """
    experiment_id = str(experiment_id)
    info_dict = {}

    if barcode is None:
        barcode = get_barcode(experiment_id)
    barcode = str(barcode)

    info_dict['barcode'] = barcode
    info_dict['experiment_id'] = experiment_id
    # gene_panel: use the provided value, else read panel_design from metrics_summary.csv
    if gene_panel == "":
        gene_panel = get_gene_panel(paths_dict['experiment_path'])
    info_dict['gene_panel'] = gene_panel
    info_dict['species'] = species if species != "" else get_species(gene_panel)
    # n_genes is computed from filtered transcripts by xenquaco (XeniumExperiment.n_genes)
    # and copied onto the experiment in run_xenium_qc, so it is not set here.
    info_dict['xenium_instrument'] = get_xenium_instrument(paths_dict['experiment_path'])
    info_dict['imaging_date'] = get_imaging_date(paths_dict['experiment_path'])

    # Convert Path to str for JSON serialization
    for key, val in info_dict.items():
        if isinstance(val, Path):
            info_dict[key] = str(val)

    # Save info_dict as JSON
    with open(Path(paths_dict['qc_output_path'], 'info_dict.json'), 'w') as outfile:
        json.dump(info_dict, outfile, indent=4)

    return info_dict


def get_barcode(experiment_id: Union[str, int]):
    """
    Extracts the barcode from a Xenium output folder name: the token immediately
    preceding the __YYYYMMDD__HHMMSS timestamp. e.g.
    'output-XETG00210__0072047__1449878532__20250717__201323' -> '1449878532'.
    Falls back to the full experiment_id if the timestamp pattern is not found.
    """
    folder = Path(str(experiment_id)).name
    match = re.search(r'__([^_]+(?:_[^_]+)*)__\d{8}__\d{6}(?:$|__)', folder)
    if match:
        return match.group(1)
    return str(experiment_id)


def get_gene_panel(experiment_path: Union[str, Path]):
    """
    Reads the panel design ID from the Xenium metrics_summary.csv in the
    experiment output folder. Used as the gene_panel key into panel_mapping.json
    so the panel can be detected automatically instead of passed in by hand.

    Returns '' if metrics_summary.csv or the panel design column is not found.
    """
    metrics_path = Path(experiment_path, 'metrics_summary.csv')
    if not os.path.exists(metrics_path):
        print(f"metrics_summary.csv not found at {metrics_path}; gene_panel not auto-detected.")
        return ''

    metrics = pd.read_csv(metrics_path)
    if len(metrics) > 0:
        for col in ('panel_design', 'panel_design_id'):
            if col in metrics.columns:
                return str(metrics[col].iloc[0])

    print(f"No panel design column in {metrics_path}; gene_panel not auto-detected.")
    return ''


def get_species(gene_panel: str = "", panel_mapping: dict = panel_mapping):
    """
    Gets species from panel_mapping using gene panel name
    """
    if gene_panel != "" and gene_panel in panel_mapping:
        return panel_mapping[gene_panel].get('species', '')
    return ''


def get_xenium_instrument(experiment_path: Union[str, Path],
                          xenium_mapping: dict = xenium_mapping):
    """
    Attempts to identify Xenium instrument from experiment directory or metadata
    """
    experiment_path = str(experiment_path)

    # Check for instrument identifier in the experiment directory name
    for instrument_id, instrument_name in xenium_mapping.items():
        if instrument_id in experiment_path:
            return instrument_name

    return None


def get_imaging_date(experiment_path: Union[str, Path]):
    """
    Extracts imaging date (YYYY-MM-DD) from the Xenium output folder name.

    Xenium output folders follow the convention
    ``output-XETG#####__<slide>__<region>__<YYYYMMDD>__<HHMMSS>``,
    so the date is the 8-digit token preceding the 6-digit time stamp.

    Returns None if no valid date token is found.
    """
    folder = Path(experiment_path).name

    match = re.search(r'__(\d{8})__(\d{6})(?:$|__)', folder)
    if match is not None:
        try:
            return datetime.strptime(match.group(1), '%Y%m%d').strftime('%Y-%m-%d')
        except ValueError:
            pass

    # Fallback: first 8-digit segment that parses as a valid date
    for token in folder.split('__'):
        if len(token) == 8 and token.isdigit():
            try:
                return datetime.strptime(token, '%Y%m%d').strftime('%Y-%m-%d')
            except ValueError:
                continue

    return None
