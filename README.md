# aibs_xenium_qc

QC pipeline for 10x Xenium spatial transcriptomics experiments, using AIBS file
storage conventions. It is a thin wrapper around the
[`xenquaco`](https://github.com/polsen99/xenquaco) library that adds AIBS-specific
path resolution, metadata tracking, and figures.

For each experiment it computes QC metrics (filtered transcript count, transcript
density per gene, tissue damage/detachment via ilastik pixel classification),
appends them to a shared metadata tracker, and writes a per-experiment output
folder with a QC distribution figure.

---

## Requirements

This pipeline is designed to run **on the HPC/cluster**, because it needs:

- Read access to the Xenium output share (`xenium_output_dir` in the config).
- Read/write access to the QC output share (`qc_dir`).
- The shared **ilastik** program (`ilastik_program_path`) for pixel classification.

All three locations are set in [`metadata/config.json`](metadata/config.json).

## Installation

```bash
git clone https://github.com/polsen99/aibs_xenium_qc.git
cd aibs_xenium_qc

# Create the `xenquaco` conda env (Python + deps + the xenquaco library)
conda env create -f environment.yaml
conda activate xenquaco

# Install this package (editable). This also resolves the xenquaco dependency.
pip install -e .

# Sanity check that the library imports
python -c "import xenquaco; from xenquaco.experiment import XeniumExperiment; print('ok')"
```

## Configuration

All environment-specific settings live in [`metadata/config.json`](metadata/config.json):

| Key | What it is |
| --- | --- |
| `xenium_output_dir` | Base dir containing Xenium output folders (one per experiment) |
| `qc_dir` | Base dir for QC outputs: the metadata tracker and per-experiment `qc_data/` |
| `ilastik_program_path` | Path to `run_ilastik.sh` |
| `md_dict_keys` | Columns recorded in the metadata tracker |
| `title_dict` | Human-readable titles for metric columns in figures |

Two lookup files map experiment identifiers to metadata:

- [`metadata/panel_mapping.json`](metadata/panel_mapping.json) — gene-panel code → `{species}`
- [`metadata/xenium_mapping.json`](metadata/xenium_mapping.json) — instrument serial (`XETG…`) → nickname

## Usage

### Notebook (recommended)

Open [`notebooks/xenium_qc.ipynb`](notebooks/xenium_qc.ipynb) with the `xenquaco`
kernel and run top to bottom:

1. **One-time setup** — seeds the metadata tracker CSV. Run once per deployment.
   The pipeline will **not** auto-create the tracker (a missing file usually
   means a bad path), so this must exist before the first QC run.
2. **Set parameters** — set `experiment_id` to the Xenium output **folder name**.
   Leave `barcode`, `gene_panel`, and `species` at their defaults to auto-resolve
   (see below).
3. **Sanity check: paths** — prints every resolved path with an `[OK]`/`[MISSING]`
   flag. Check this before the (slow) run.
4. **Run single experiment** — runs the full QC pipeline.
5. **Inspect results** — prints the key metrics.

### Command line

```bash
# First run on a fresh deployment (seeds the tracker, then runs):
python scripts/run_xenium_qc.py --experiment-id <output_folder_name> --init-tracker

# Subsequent runs:
python scripts/run_xenium_qc.py --experiment-id <output_folder_name>
```

Run `python scripts/run_xenium_qc.py --help` for all options (`--species`,
`--gene-panel`, `--no-pixel-classification`, `--no-figures`, …).

## What gets auto-detected

You normally only need to provide `experiment_id`. The rest is derived:

- **barcode** — the 10-digit token before the timestamp in the output folder name,
  e.g. `output-XETG00210__0072047__1449878532__20250717__201323` → `1449878532`.
- **gene_panel** — read from `panel_design` in the bundle's `metrics_summary.csv`.
- **species** — looked up from the gene panel in `panel_mapping.json`.
- **instrument** — matched from the `XETG…` serial in the folder name via
  `xenium_mapping.json`.
- **imaging_date** — parsed from the `YYYYMMDD` in the folder name.

Any of these can be overridden by passing the value explicitly.

## Outputs

Per experiment, written to `qc_dir/qc_data/<barcode>/`:

- `paths.json`, `info_dict.json` — resolved paths and experiment metadata
- `qc_distributions.png` — transcript-density distribution (all species as curves,
  with this experiment marked)
- mask/image tiffs from pixel classification

Metrics are also appended as a row to the shared tracker at
`qc_dir/qc_metadata_trackers/xenium_qc_metadata_tracker.csv`. Re-running an existing
barcode only fills previously-empty fields; it never overwrites existing values.

## Extending

- **New gene panel** — add a `"<panel_design>": {"species": "<species>"}` entry to
  [`metadata/panel_mapping.json`](metadata/panel_mapping.json). `panel_design` must
  match the value in that panel's `metrics_summary.csv` exactly (case-sensitive).
- **New instrument** — add a `"XETG00###": "<nickname>"` entry to
  [`metadata/xenium_mapping.json`](metadata/xenium_mapping.json).

## Gotchas

- **The metadata tracker must already exist.** The first run on a new deployment
  needs `--init-tracker` (CLI) or the notebook's one-time setup cell. Otherwise it
  raises `FileNotFoundError` rather than silently starting a new tracker.
- **`gene_panel` must match a `panel_mapping.json` key** exactly, or `species`
  comes back empty. Use the sanity-check cell to confirm the detected panel.
- **DAPI image filename.** The wrapper reads `morphology.ome.tif`
  ([`experiment_info.py`](aibs_xenium_qc/experiment_info.py)). If your bundles use
  `morphology_focus.ome.tif`, update that path (the sanity-check cell will flag it
  as `[MISSING]`).
- **n_genes is computed, not configured.** It comes from the count of unique genes
  in the filtered transcripts (in xenquaco), so it does not need to be stored per
  panel.

## Repository layout

```
aibs_xenium_qc/
  aibs_experiment.py      # AIBSXeniumExperiment: wraps xenquaco + tracking + figures
  experiment_info.py      # path/metadata resolution (barcode, panel, species, dates)
  metadata_tracking.py    # read/append the shared metadata tracker CSV
  figures.py              # QC distribution figures
metadata/
  config.json             # environment paths and settings
  panel_mapping.json      # gene panel -> species
  xenium_mapping.json     # instrument serial -> nickname
notebooks/xenium_qc.ipynb # main entry point
scripts/run_xenium_qc.py  # command-line entry point
environment.yaml          # conda env named `xenquaco`
```
