# The Role of Sufficiency Measures in a Decarbonizing Europe

## Overview

This repository accompanies the paper **"The Role of Sufficiency Measures in a Decarbonizing Europe"** and includes all code, data, and configurations used in the analysis. The study explores how various sufficiency measures can impact carbon reduction across Europe.

The repository extensively utilizes the **MARIO** software package (https://github.com/it-is-me-mario/MARIO), which serves as the primary analytical tool. To facilitate running the analysis on your system, MARIO and other dependencies can be installed using the `environment.yml` file provided in this repository.

## Repository Structure

### Root Directory
The root directory contains the main scripts and configuration files for running and managing the analysis.

- **`Path.json`**: Configuration file where paths to required external files are specified. These files include necessary datasets, such as the original Exiobase Hybrid database, which must be obtained separately.
  
- **`Main.py`**: The primary script for running all scenarios considered in the paper. This script coordinates the execution of the main analyses and outputs all required results for reproducing the findings.
  
- **Ancillary Scripts**: Additional scripts for other part of the pipeline such as **Results Analysis** (provides code to analyze and interpret the outputs from `Main.py`) and **Shock File Construction** (includes code for building shock files).

### Folders
This repository is organized into subfolders containing input and output files generated by the model:

- **`Files for Shock`**: Contains all contextual and specific data relevant to sufficiency initiatives discussed in Chapter 3. It includes detailed input files required for each scenario and the sufficiency measures analyzed.

## Installation and Setup

1. **Set up the Environment**: Use the `environment.yml` file to create a consistent environment with all necessary dependencies, including MARIO.
   ```bash
   conda env create -f environment.yml
   conda activate fulfill