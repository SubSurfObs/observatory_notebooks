# Subsurface Observatory — Notebooks

Worked examples for accessing and analysing seismic data from the
[University of Melbourne Subsurface Observatory](https://subsurface.science.unimelb.edu.au).

Each notebook is self-contained in its own folder with its own conda environment.
Notebooks are embedded in the Observatory website and can also be run interactively
on Google Colab — no local installation required.

---

## Notebooks

| # | Topic | Colab |
|---|---|---|
| [01](01_fdsn_access/) | Multi-network FDSN data access | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/SubSurfObs/observatory_notebooks/blob/main/01_fdsn_access/index.ipynb) |
| [02](02_phase_picking/) | Automated phase picking with SeisBench | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/SubSurfObs/observatory_notebooks/blob/main/02_phase_picking/index.ipynb) |
| 03 | Earthquake location *(in preparation)* | — |
| 04 | Instrument correction & magnitude *(in preparation)* | — |

---

## Running locally

```bash
cd 01_fdsn_access
conda env create -f environment.yml
conda activate obs-nb-fdsn-access
jupyter lab index.ipynb
```

Each notebook has its own `environment.yml` — create and activate it before launching.

---

## Repository structure

```
utils.py                      shared utilities (FDSN clients, plotting, catalog I/O)
01_fdsn_access/
    index.ipynb               notebook
    environment.yml           conda environment
02_phase_picking/
    index.ipynb
    environment.yml
    data/                     committed example data (ex01.mseed, ex01.xml)
```

`utils.py` is shared across all notebooks. It contains:
- `FDSN_UOM`, `FDSN_AUSPASS` — endpoint constants
- `collect_stations_and_waveforms()` — multi-provider FDSN resolver
- `convert_to_catalog()` — SeisBench DataFrame → ObsPy Catalog
- `plot_station_picks_panel()` — waveform + pick visualisation

---

## Integration with the Observatory website

This repository is embedded in the
[SubSurfObs/SubsurfaceObservatory](https://github.com/SubSurfObs/SubsurfaceObservatory)
Quarto site as a **git submodule** at `notebooks/`. The site renders each
`index.ipynb` as a static page using the committed cell outputs.

**How outputs stay current:**
A GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push to `main`.
It executes each notebook in its own conda environment and commits the updated outputs
back to this repository with `[skip ci]` in the commit message.

**To update the website after pushing here:**
Someone with access to the site repo runs:
```bash
git -C notebooks pull origin main
git add notebooks
git commit -m "Update notebooks submodule"
```

**To add a new notebook:**
1. Create a new folder (e.g. `03_earthquake_location/`)
2. Add `index.ipynb` and `environment.yml`
3. Commit and push — CI will execute it automatically
4. Update the submodule pointer in the site repo (step above)

---

## Data

Notebook 01 fetches data live from the UoM FDSNWS at runtime.
Notebook 02 loads from `data/ex01.mseed` and `data/ex01.xml` (committed) — a
Mw ~3 earthquake near Moe, Victoria, recorded on 3 February 2026.

**Data source:** University of Melbourne Seismic Network (VW),
DOI [10.7914/8csc-8z27](https://doi.org/10.7914/8csc-8z27).
Licence: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
