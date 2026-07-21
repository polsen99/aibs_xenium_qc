from typing import Union
from pathlib import Path
import numpy as np
import json
import matplotlib.pyplot as plt
from xenquaco.experiment import XeniumExperiment
import aibs_xenium_qc.experiment_info as experiment_info
from aibs_xenium_qc.experiment_info import config
import aibs_xenium_qc.metadata_tracking as metadata_tracking
import aibs_xenium_qc.figures as figures


class AIBSXeniumExperiment():

    def __init__(self, experiment_id: Union[str, int],
                 barcode: Union[str, int] = None,
                 species: str = "", gene_panel: str = "",
                 force_mask: bool = False):
        """
        Initialize an AIBSXeniumExperiment which wraps xenquaco's XeniumExperiment
        with AIBS-specific path resolution and metadata tracking
        """
        if barcode is None:
            barcode = experiment_info.get_barcode(experiment_id)
            print(f"Barcode not provided. Calculated from experiment_id: {barcode}")
        barcode = str(barcode)

        # Get paths and info dicts
        paths_dict = experiment_info.get_paths_dict(experiment_id, barcode, species, gene_panel)
        info_dict = experiment_info.get_info_dict(paths_dict, experiment_id, barcode, species, gene_panel)

        # Unpack into self attributes
        for key, val in paths_dict.items():
            setattr(self, key, val)
        for key, val in info_dict.items():
            setattr(self, key, val)

        # Create xenquaco XeniumExperiment
        self.xenquaco_experiment = XeniumExperiment(
            self.transcripts_path,
            self.ilastik_program_path,
            self.high_res_dapi_image_path,
            self.qc_output_path,
            force_mask=force_mask
        )

    def run_xenium_qc(self, run_pixel_classification: bool = True,
                      plot_figures: bool = True):
        """
        Run QC pipeline on AIBS Xenium experiment
        """
        self.xenquaco_experiment.run_all_qc(run_pixel_classification, plot_figures)

        # Copy attributes from xenquaco_experiment to self
        for attr in dir(self.xenquaco_experiment):
            if not attr.startswith('__') and not callable(getattr(self.xenquaco_experiment, attr)):
                setattr(self, attr, getattr(self.xenquaco_experiment, attr))

        # Build metadata dict
        md_dict = {}
        md_dict_keys = config['md_dict_keys']
        for key in md_dict_keys:
            md_dict[key] = getattr(self, key, np.nan)

        # Write to metadata tracker
        metadata_tracking.write_to_metadata_tracker(self.qc_metadata_tracker, md_dict)

        # Plot distribution figures
        if plot_figures:
            rounded_ts_density = "{:.3g}".format(self.transcript_density_um2_per_gene)

            damage_pct = getattr(self, 'damage_percent', np.nan)
            detachment_pct = getattr(self, 'detachment_percent', np.nan)

            qc_data = [len(self.filtered_transcripts), rounded_ts_density,
                       damage_pct, detachment_pct]

            try:
                figures.plot_qc_dists(
                    self.qc_metadata_tracker,
                    self.transcript_density_um2_per_gene,
                    self.barcode,
                    qc_data,
                    damage_percent=damage_pct if not np.isnan(damage_pct) else None,
                    detachment_percent=detachment_pct if not np.isnan(detachment_pct) else None,
                    species=self.species if self.species else None,
                    out_file=Path(self.qc_output_path, "qc_distributions.png")
                )
            except Exception as e:
                print(f"Could not plot distributions (likely not enough historical data): {e}")

            if run_pixel_classification:
                try:
                    if not np.isnan(damage_pct):
                        fig, (damage_ax, detachment_ax) = plt.subplots(1, 2, figsize=(15, 4))
                        figures.plot_damage_distribution(
                            self.qc_metadata_tracker, damage_pct,
                            self.species, self.barcode, damage_ax)
                        full_fig_outfile = Path(self.qc_output_path, "damage_detachment_dist.png")
                    else:
                        fig, detachment_ax = plt.subplots(figsize=(7, 6))
                        full_fig_outfile = ""

                    figures.plot_detachment_distribution(
                        self.qc_metadata_tracker, detachment_pct,
                        self.species, self.barcode, detachment_ax)

                    if full_fig_outfile != "":
                        plt.savefig(full_fig_outfile, dpi=100)
                except Exception as e:
                    print(f"Could not plot pixel classification distributions: {e}")
