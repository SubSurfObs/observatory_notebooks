# Subsurface Observatory — Notebooks

Jupyter notebooks demonstrating data access and analysis using the Subsurface Observatory
infrastructure. Each notebook is self-contained in its own subfolder with its own conda
environment.

## Structure

```
01_vw_waveform_analysis/
    index.ipynb        ← notebook (outputs committed; run for latest data)
    environment.yml    ← conda env for this notebook
```

## Running locally

```bash
cd 01_vw_waveform_analysis
conda env create -f environment.yml
conda activate obs-nb-vw-waveforms
jupyter lab index.ipynb
```

## Running on Colab

Each notebook has a Colab badge in the first cell. Click it to open with live data.
Dependencies are installed automatically inside the notebook.

## How outputs stay current

A GitHub Actions workflow executes all notebooks on push to `main` and commits the
updated outputs back to the repository. The Subsurface Observatory website then picks
up the latest outputs via a git submodule update.
