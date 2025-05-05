# The Role of Sufficiency Measures in a Decarbonizing Europe

This repository accompanies the paper:

> **"The Role of Sufficiency Measures in a Decarbonizing Europe"**  
> *Published: 29 April 2025, Ecological Economics*  
> DOI: [10.1016/j.ecolecon.2025.108645](https://doi.org/10.1016/j.ecolecon.2025.108645)

---

## Overview

This repository provides all code, data, and instructions required to reproduce the scenarios and results presented in the paper. The analysis is based on the [MARIO](https://github.com/it-is-me-mario/MARIO) software package, which is used for environmentally extended input-output modeling.

All data and results are also available on Zenodo:  
🔗 **[Zenodo Repository](https://doi.org/10.5281/zenodo.15070606)**

---

## Repository Structure

```
.
├── 1. Database building.ipynb     # Builds and prepares Exiobase database with new technologies required
├── 2. Shock building.ipynb        # Constructs scenario-specific shock files 
├── 3. Model run.ipynb             # Runs all scenarios and exports results
├── Data/                          # Contains input databases and raw files (it's created while running the notebooks)
├── Shocks/                        # Templates, mappings, and filled shock files
└── Outputs/                       # Results and aggregated outputs (it's filled while running the notebooks)
```

---

## Getting Started

### 1. Environment Setup

Install all dependencies using the provided Conda environment file:

```bash
conda env create -f _environment.yml
conda activate fulfill_env

```

### 2. Data Download

All required data can be downloaded automatically by running the notebooks in sequence.

Alternatively, you can manually download the full dataset from [Zenodo](https://doi.org/10.5281/zenodo.15070606) and extract the contents into the appropriate folders (`Data/`, `Shocks/`, etc.) as described in each notebook.


## Workflow 
### Step 1: Database Preparation

Run `1. Database building.ipynb` to:

- Download and extract the Exiobase v3.3.18 database in MARIO format.  
- Parse and aggregate the database using MARIO.  
- Add new supply chains and performs other minor manipulations to the database where needed.  
- Save the processed database for scenario analysis.
- This step runs in 5-10 minutes on a MacBook Pro M3 Pro 18 GB RAM


### Step 2: Build Shock Files

Run `2. Shock building.ipynb` to:

- Download and extract all supporting files for shock construction.  
- Build scenario-specific shock files for all combinations of background, measure, and year.  
- Save the resulting files in `Shocks/filled_files/`.
- This step runs in around 10 minutes on a MacBook Pro M3 Pro 18 GB RAM

### Step 3: Run Model Scenarios

Run `3. Model run.ipynb` to:

- Parse the prepared MARIO-formatted database.  
- Loop through each scenario, run shock calculations, and export results.  
- Aggregate and merge outputs for analysis.
- This step runs in approximately 8 hours on a MacBook Pro M3 Pro 18 GB RAM. 

### Outputs

All scenario results are saved in:

- `Outputs/Results/`: Scenario outputs, organized by matrix and scenario.  
- `Outputs/Results/Merged/`: Merged results for each matrix, ready for analysis.


---

### Citation

If you use this repository, code, or data, please cite:
Golinucci, N., Rocco, M. V., Prina, M. G., Beltrami, F., Rinaldi, L., Schau, E. M., & Sparber, W. (2025). The role of sufficiency measures in a decarbonizing Europe. *Ecological Economics, 235*, 108645. [https://doi.org/10.1016/j.ecolecon.2025.108645](https://doi.org/10.1016/j.ecolecon.2025.108645)

```bash
Golinucci, N. et al (2025). The role of sufficiency measures in a decarbonizing Europe. Ecological Economics, 235, 108645. https://doi.org/10.1016/j.ecolecon.2025.108645
```
