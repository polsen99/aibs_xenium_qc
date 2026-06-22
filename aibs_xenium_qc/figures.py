import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.axes import Axes
import seaborn as sns
from pathlib import Path
from typing import Union
import aibs_xenium_qc.metadata_tracking as metadata_tracking
from aibs_xenium_qc.experiment_info import config


def plot_qc_table(data, ax=None):
    """
    Create table with key Xenium QC metrics

    Parameters
    ----------
    data : list
        [total_filtered_transcripts, transcript_density, damage_percent, detachment_percent]
    """
    if isinstance(data[0], (int, float)):
        data[0] = '{:,}'.format(data[0])

    columns = ['Filtered Transcripts', 'Transcript Density\n(per $\\mu m^2$ per gene)',
               'Damage %', 'Detachment %']

    if ax is None:
        _, ax = plt.subplots(figsize=(14, 2))
    ax.axis('tight')
    ax.axis('off')

    table = ax.table(cellText=[data], colLabels=columns, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    cellDict = table.get_celld()

    header_color = '#001F3F'
    header_font_color = '#D3D3D3'
    data_color = '#F5F5F5'
    data_font_color = '#000000'

    for j in range(len(columns)):
        cell = cellDict[(0, j)]
        cell.get_text().set_fontweight('bold')
        cell.get_text().set_color(header_font_color)
        cell.set_height(0.3)
        cell.set_facecolor(header_color)

        cell = cellDict[(1, j)]
        cell.get_text().set_fontweight('normal')
        cell.get_text().set_color(data_font_color)
        cell.set_height(0.3)
        cell.set_facecolor(data_color)


def plot_species_distribution(metadata_path: Union[str, Path], column: str,
                              species: str = None, value: float = None,
                              barcode: str = '', ax=None,
                              species_label_bool=False,
                              out_file: Union[str, Path] = None, dpi: int = 100):
    """
    KDE plot of a QC metric against distribution of previous experiments, split by species
    """
    if barcode != '':
        barcode = str(barcode)

    metadata = metadata_tracking.read_metadata(metadata_path)

    if column not in list(metadata):
        raise ValueError(f'Column "{column}" is not in metadata columns')

    mouse_md = metadata_tracking.get_metadata(metadata_path, species='mouse')
    human_md = metadata_tracking.get_metadata(metadata_path, species='human')
    macaque_md = metadata_tracking.get_metadata(metadata_path, species='macaque')

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))

    sns.set_style('white')
    sns.set_style('ticks')

    mouse_label = "Mouse" if species_label_bool else ""
    human_label = "Human" if species_label_bool else ""
    macaque_label = "Macaque" if species_label_bool else ""

    if species == "mouse":
        sns.kdeplot(data=mouse_md, x=column, fill=True, cut=0, label=mouse_label, alpha=0.1, ax=ax, warn_singular=False)
    elif species == "human":
        sns.kdeplot(data=human_md, x=column, fill=True, cut=0, label=human_label, alpha=0.1, ax=ax, warn_singular=False)
    elif species == "macaque":
        sns.kdeplot(data=macaque_md, x=column, fill=True, cut=0, label=macaque_label, alpha=0.1, ax=ax, warn_singular=False)
    else:
        sns.kdeplot(data=mouse_md, x=column, fill=True, cut=0, label=mouse_label, alpha=0.1, ax=ax, warn_singular=False)
        sns.kdeplot(data=human_md, x=column, fill=True, cut=0, label=human_label, alpha=0.1, ax=ax, warn_singular=False)
        sns.kdeplot(data=macaque_md, x=column, fill=True, cut=0, label=macaque_label, alpha=0.1, ax=ax, warn_singular=False)

    if value is not None:
        if barcode != '':
            ax.axvline(value, linestyle='dashed', color='k', label=barcode)
        else:
            ax.axvline(value, linestyle='dashed', color='k')

    ax.set(title=config['title_dict'].get(column, column), xlabel=column, ylabel='probability density')
    ax.legend()

    if out_file is not None:
        plt.savefig(out_file, dpi=dpi)


def plot_qc_dists(metadata_path: Union[str, Path],
                  ts_density: float, barcode: str, data: list,
                  damage_percent: float = None, detachment_percent: float = None,
                  species: str = None,
                  out_file: Union[str, Path] = None, dpi: int = 100):
    """
    Combined QC distribution figure: transcript density, damage, detachment + metrics table
    """
    n_plots = 1
    if damage_percent is not None:
        n_plots += 1
    if detachment_percent is not None:
        n_plots += 1

    _ = plt.figure(figsize=(6 * n_plots, 8))
    gs = gridspec.GridSpec(2, n_plots, height_ratios=[1, 0.4])

    col = 0
    ts_density_ax = plt.subplot(gs[col])
    plot_species_distribution(metadata_path, 'transcript_density_um2_per_gene',
                              species, ts_density, barcode,
                              ax=ts_density_ax, species_label_bool=True)
    col += 1

    if damage_percent is not None:
        damage_ax = plt.subplot(gs[col])
        plot_species_distribution(metadata_path, 'damage_percent',
                                  species, damage_percent, barcode,
                                  ax=damage_ax, species_label_bool=True)
        col += 1

    if detachment_percent is not None:
        detachment_ax = plt.subplot(gs[col])
        plot_species_distribution(metadata_path, 'detachment_percent',
                                  species, detachment_percent, barcode,
                                  ax=detachment_ax, species_label_bool=True)

    table_ax = plt.subplot(gs[n_plots:])
    plot_qc_table(data, ax=table_ax)

    plt.suptitle(barcode, fontsize=18)
    fig = plt.gcf()
    fig.patch.set_alpha(0)
    plt.tight_layout()

    if out_file is not None:
        plt.savefig(out_file, dpi=dpi)

    plt.show()
    plt.close()


def plot_damage_distribution(metadata_path: Union[str, Path], damage_value: float,
                             species: str = None, barcode: str = '',
                             ax: Axes = None, out_file: Union[str, Path] = None, dpi: int = 100):

    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 6))

    plot_species_distribution(metadata_path=metadata_path, column="damage_percent",
                              species=species, value=damage_value,
                              barcode=barcode, ax=ax, species_label_bool=True)

    if out_file is not None:
        plt.savefig(out_file, dpi=dpi)


def plot_detachment_distribution(metadata_path: Union[str, Path], detachment_value: float,
                                 species: str = None, barcode: str = '',
                                 ax: Axes = None, out_file: Union[str, Path] = None, dpi: int = 100):

    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 6))

    plot_species_distribution(metadata_path=metadata_path, column="detachment_percent",
                              species=species, value=detachment_value,
                              barcode=barcode, ax=ax, species_label_bool=True)

    if out_file is not None:
        plt.savefig(out_file, dpi=dpi)
