#!/usr/bin/env python
"""
Run the AIBS Xenium QC pipeline for a single experiment.

Intended to run on the cluster, where the xenquaco package, the ilastik
binary, and the /allen paths in metadata/config.json are available.

Examples
--------
# First-time setup only: create the empty metadata tracker (header row),
# then run. After the tracker exists, drop --init-tracker.
python scripts/run_xenium_qc.py \
    --experiment-id output-XETG00044__0003191__Region_1__20230216__044341 \
    --species mouse --gene-panel DQPQP4 --init-tracker

# Normal run (tracker already exists)
python scripts/run_xenium_qc.py \
    --experiment-id <output_folder_name> --gene-panel DQPQP4
"""
import argparse
import os
import sys


def init_tracker_if_missing(tracker_path, columns):
    """Create the metadata tracker CSV with just a header row if it does not exist.

    The pipeline intentionally refuses to auto-create the tracker at write time
    (a missing file usually means a bad path). This is the one deliberate,
    one-time seeding step for a fresh deployment.
    """
    import pandas as pd

    if os.path.exists(tracker_path):
        print(f"[init] Tracker already exists, leaving as-is: {tracker_path}")
        return
    os.makedirs(os.path.dirname(tracker_path), exist_ok=True)
    pd.DataFrame(columns=columns).to_csv(tracker_path, index=False)
    print(f"[init] Created empty tracker with {len(columns)} columns: {tracker_path}")


def main():
    parser = argparse.ArgumentParser(description="Run AIBS Xenium QC for one experiment")
    parser.add_argument("--experiment-id", required=True,
                        help="Xenium output folder name (under config xenium_output_dir)")
    parser.add_argument("--barcode", default=None,
                        help="Barcode; defaults to experiment-id")
    parser.add_argument("--species", default="",
                        help="Override species; otherwise resolved from gene-panel via panel_mapping.json")
    parser.add_argument("--gene-panel", default="",
                        help="Gene panel key (e.g. DQPQP4); used for species lookup")
    parser.add_argument("--force-mask", action="store_true",
                        help="Force regeneration of ilastik masks")
    parser.add_argument("--no-pixel-classification", action="store_true",
                        help="Skip ilastik pixel classification (damage/detachment)")
    parser.add_argument("--no-figures", action="store_true",
                        help="Skip distribution/figure plotting")
    parser.add_argument("--init-tracker", action="store_true",
                        help="One-time: create the metadata tracker CSV header if missing, then run")
    args = parser.parse_args()

    # Imported here so --help works even if heavy deps are unavailable
    from aibs_xenium_qc.aibs_experiment import AIBSXeniumExperiment
    from aibs_xenium_qc.experiment_info import config
    from pathlib import Path

    if args.init_tracker:
        tracker_path = str(Path(config["qc_dir"], "qc_metadata_trackers",
                                "xenium_qc_metadata_tracker.csv"))
        init_tracker_if_missing(tracker_path, config["md_dict_keys"])

    print(f"[run] experiment_id={args.experiment_id} barcode={args.barcode} "
          f"species={args.species!r} gene_panel={args.gene_panel!r}")

    exp = AIBSXeniumExperiment(
        args.experiment_id,
        barcode=args.barcode,
        species=args.species,
        gene_panel=args.gene_panel,
        force_mask=args.force_mask,
    )
    exp.run_xenium_qc(
        run_pixel_classification=not args.no_pixel_classification,
        plot_figures=not args.no_figures,
    )

    print("\n[done] QC metrics:")
    print(f"  Filtered transcripts:  {getattr(exp, 'filtered_transcript_count', 'NA'):,}"
          if isinstance(getattr(exp, 'filtered_transcript_count', None), int)
          else f"  Filtered transcripts:  {getattr(exp, 'filtered_transcript_count', 'NA')}")
    print(f"  Transcript density:    {getattr(exp, 'transcript_density_um2_per_gene', 'NA')} per um2 per gene")
    print(f"  Damage %:              {getattr(exp, 'damage_percent', 'NA')}")
    print(f"  Detachment %:          {getattr(exp, 'detachment_percent', 'NA')}")
    print(f"  Output dir:            {getattr(exp, 'qc_output_path', 'NA')}")


if __name__ == "__main__":
    sys.exit(main())
