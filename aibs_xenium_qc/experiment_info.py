from pathlib import Path
import json
import os
from typing import Union
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
        barcode = experiment_id
    barcode = str(barcode)

    experiment_path = Path(config['xenium_output_dir'], experiment_id)

    # Experiment outputs
    paths_dict['experiment_path'] = Path(experiment_path)
    paths_dict['transcripts_path'] = Path(experiment_path, 'transcripts.parquet')
    paths_dict['high_res_dapi_image_path'] = Path(experiment_path, 'morphology.ome.tif')

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
        barcode = experiment_id
    barcode = str(barcode)

    info_dict['barcode'] = barcode
    info_dict['experiment_id'] = experiment_id
    info_dict['species'] = species if species != "" else get_species(gene_panel)
    info_dict['gene_panel'] = gene_panel
    # n_genes is computed from filtered transcripts by xenquaco (XeniumExperiment.n_genes)
    # and copied onto the experiment in run_xenium_qc, so it is not set here.
    info_dict['xenium_instrument'] = get_xenium_instrument(paths_dict['experiment_path'])
    info_dict['imaging_date'] = None

    # Convert Path to str for JSON serialization
    for key, val in info_dict.items():
        if isinstance(val, Path):
            info_dict[key] = str(val)

    # Save info_dict as JSON
    with open(Path(paths_dict['qc_output_path'], 'info_dict.json'), 'w') as outfile:
        json.dump(info_dict, outfile, indent=4)

    return info_dict


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
