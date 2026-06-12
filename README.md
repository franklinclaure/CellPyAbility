# CellPyAbility [![Tests](https://github.com/bindralab/CellPyAbility/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/bindralab/CellPyAbility/actions/workflows/tests.yml) [![PyPI version](https://img.shields.io/pypi/v/CellPyAbility.svg?logo=pypi&logoColor=white)](https://pypi.org/project/CellPyAbility/) [![Bioconda](https://img.shields.io/conda/vn/bioconda/cellpyability?logo=anaconda&color=green)](https://anaconda.org/bioconda/cellpyability) [![License](https://img.shields.io/pypi/l/CellPyAbility)](https://github.com/bindralab/CellPyAbility/blob/main/LICENSE.txt)

CellPyAbility is an open-source cell viability and dose-response analysis tool that seamlessly integrates with our provided [protocols](protocol.pdf). Please review our [license](LICENSE.txt) prior to use. The software can be run from the command line as a [Python package](#command-line-interface-cli) or with a code-free [Windows application](#windows-application). 

## Table of Contents
- [Quick Start](#quick-start): minimal step-by-step guide for running CellPyAbility

- [Abstract](#abstract): overview of the method and software

- [Requirements](#requirements): necessary steps before running the software

- [Command Line Interface](#command-line-interface-cli): modern CLI for automated workflows and testing

- [Code-Free Application](#running-the-code-free-application): code-free application for macOS and Windows

- [Example Outputs](#example-outputs): examples of figures and tables for each module

- [Modifying the CellProfiler Pipeline](#modifying-the-cellprofiler-pipeline): guidelines for custom CellProfiler analysis integration

- [Testing](#testing): automated tests and example data for validation

- [Contributing](#contributing): guidelines for development installation

- [Acknowledgements](#acknowledgements): who did what

## Quick Start
### CellProfiler
CellProfiler must be installed because CellPyAbility uses it as a subprocess. 

CellPyAbility automatically searches default CellProfiler install locations based on your OS. If it cannot be found, you will be prompted to provide the path on your first run, which is then saved to cellprofiler_path.txt for future runs. 

See [Requirements](#requirements) for more information.

### Installation (CLI)
Install CellPyAbility from PyPI or Bioconda. If using Bioconda, we recommend creating a dedicated environment:

**PyPI**:
```bash
# Install from PyPI
pip install cellpyability
```

**Bioconda**:
```bash
# Create a Conda environment and install CellPyAbility
conda create --name cellpyability -c conda-forge -c bioconda cellpyability "python>=3.8,<=3.11"

# Activate the new environment
conda activate cellpyability
```

### Running an Analysis (CLI)

**Growth Delay Assay (GDA)**
```bash
# Run a growth delay assay (GDA) analysis 
cellpyability gda \
  --title "MyExperiment" \
  --upper-name "Cell Line A" \
  --lower-name "Cell Line B" \
  --top-conc 0.000001 \
  --dilution 3 \
  --image-dir /path/to/your/images \
  --output-dir /path/to/results # Optional
```

**Synergy**
```bash
cellpyability synergy \
  --title "20250101_Synergy" \
  --x-drug "Drug_A" \
  --x-top-conc 0.0004 \
  --x-dilution 4 \
  --y-drug "Drug_B" \
  --y-top-conc 0.0001 \
  --y-dilution 4 \
  --image-dir /path/to/images \
  --output-dir /path/to/results  # Optional
```

For command information while in the CLI, run `cellpyability --help` or `cellpyability <module> --help`.

## Code-Free Application

Standalone executable applications are available for macOS and Windows. 

📥 **[Download the latest release here](https://github.com/bindralab/cellpyability/releases/latest)**

Navigate to the bottom of the release notes and download the `.zip` file for your respective operating system.

### Test Data
- Download the [example GDA images](https://github.com/bindralab/CellPyAbility/tree/main/example/example_gda)
- Download the [example synergy images](https://github.com/bindralab/CellPyAbility/tree/main/example/example_synergy)
- Compare outputs to [expected outputs](https://github.com/bindralab/CellPyAbility/tree/main/example/example_expected_outputs)

## Abstract

Nuclei counting provides a low-cost, metabolic-independent alternative to ATP- or
tetrazolium-based cell viability assays. However, the fragmentation of image processing, normalization, and statistical modeling across multiple software platforms hinders high-throughput adoption. 

We present CellPyAbility, a Python-based suite that automates image processing, dose-response fitting, and synergy analysis. It converts unedited whole-well images into publication-ready graphics in under one minute per 96-well plate on standard desktop hardware.

## Requirements

### Data Requirements

Reading the [protocols](protocol.pdf) first may aid in understanding the default data requirements.

- Only the inner 60 wells of a 96-well plate (B-G, 2-11) should be used

- Image file names must contain their corresponding well
  - B2, ImageB2, DAPI-B2-(362), etc. for the image file of the B2 well in the 96-well plate

- The GDA module requires a directory of 60 images 
  - B-D: Cell Line A in triplicate | E-G: Cell Line B in triplicate

- The synergy module requires a directory of 180 images
  - Wells of the same name (B2, ...) across three plates are triplicates

### Code-Free Application Requirements

- The user must have CellProfiler (tested on versions 4.2.5-4.2.8, though others may work)
- CellProfiler can be downloaded for macOS, Windows, and Linux [here](https://cellprofiler.org/releases).


## Command Line Interface (CLI)

The CellPyAbility CLI provides a modern, scriptable interface for automated workflows, batch processing, and continuous integration testing.

### Basic Usage

The CLI provides three subcommands corresponding to the three analysis modules:

```bash
cellpyability --help          # Show available modules
cellpyability gda --help      # Show GDA module options
cellpyability synergy --help  # Show synergy module options  
cellpyability simple --help   # Show simple module options
```

### GDA Module

Analyze dose-response experiments with two cell conditions and one drug gradient:

```bash
cellpyability gda \
  --title "20250101_Experiment" \
  --upper-name "HCT116_WT" \
  --lower-name "HCT116_KO" \
  --top-conc 0.000001 \
  --dilution 3 \
  --image-dir /path/to/images \
  --output-dir /path/to/results  # Optional
```

**Parameters:**
- `-t, --title`: Experiment title (used for output file names)
- `-u, --upper-name`: Name for cell condition in rows B-D
- `-l, --lower-name`: Name for cell condition in rows E-G
- `-c, --top-conc`: Top drug concentration in molar (e.g., 0.000001 for 1 µM)
- `-d, --dilution`: Dilution factor between columns (e.g., 3 for 3-fold dilution)
- `-i, --image-dir`: Directory containing 60 well images
- `-n, --no-plot`: (Optional) Skip displaying plot window
- `-f, --counts-file`: (Optional) Use pre-existing counts CSV for testing
- `-o, --output-dir`: (Optional) Custom output directory (default: `./cellpyability_output/`)

**Outputs** (saved to `./cellpyability_output/gda_output/` by default):
- `{title}_gda_Stats.csv`: Dose-response statistics
- `{title}_gda_ViabilityMatrix.csv`: Normalized viability matrix
- `{title}_gda_plot.png`: Publication-ready dose-response plot
- `{title}_gda_counts.csv`: Raw nuclei counts

### Synergy Module

Analyze drug combination experiments with two drug gradients:

```bash
cellpyability synergy \
  --title "20250101_Synergy" \
  --x-drug "Drug_A" \
  --x-top-conc 0.0004 \
  --x-dilution 4 \
  --y-drug "Drug_B" \
  --y-top-conc 0.0001 \
  --y-dilution 4 \
  --image-dir /path/to/images \
  --output-dir /path/to/results  # Optional
```

**Parameters:**
- `-t, --title`: Experiment title
- `-x, --x-drug`: Name of horizontal gradient drug
- `-c, --x-top-conc`: Horizontal top concentration in molar
- `-d, --x-dilution`: Horizontal dilution factor
- `-y, --y-drug`: Name of vertical gradient drug
- `-C, --y-top-conc`: Vertical top concentration in molar
- `-D, --y-dilution`: Vertical dilution factor
- `-i, --image-dir`: Directory containing images
- `-n, --no-plot`: (Optional) Skip displaying plot
- `-f, --counts-file`: (Optional) Use pre-existing counts CSV
- `-o, --output-dir`: (Optional) Custom output directory (default: `./cellpyability_output/`)

### Simple Module

Generate a nuclei count matrix without further analysis:

```bash
cellpyability simple \
  --title "20250101_Counts" \
  --image-dir /path/to/images \
  --output-dir /path/to/results  # Optional
```

**Parameters:**
- `-t, --title`: Experiment title
- `-i, --image-dir`: Directory containing well images
- `-f, --counts-file`: (Optional) Use pre-existing CellProfiler counts CSV
- `-o, --output-dir`: (Optional) Custom output directory (default: `./cellpyability_output/`)

**Outputs** (saved to `./cellpyability_output/simple_output/` by default):
- `{title}_simple_CountMatrix.csv`: 96-well nuclei count matrix

### Batch Module

The batch module enables automated processing of multiple experiments from a single CSV configuration file. It acts as a job manager, automatically detecting whether a row requires GDA or Synergy analysis.

[config.csv file template](config.csv)

```bash
# Process multiple experiments using a CSV config file
cellpyability batch --input-file path/to/config.csv --no-plot
```

**Parameters:**
- `-i, --input-file`: Path to the batch configuration CSV file
- `-n, --no-plot`: (Optional) Skip displaying plots (still saves them)
- `-o, --output-dir`: (Optional) Custom output directory

**Config CSV Schema:**
The configuration file should contain a `module` column to specify the analysis type (`gda` or `synergy`), followed by the required parameters for that module.

| Column | Description |
| --- | --- |
| `module` | `gda` or `synergy` |
| `dir` | Directory containing images |
| `title` | Experiment title |
| `upper` | (GDA) Name for cell condition in rows B-D |
| `lower` | (GDA) Name for cell condition in rows E-G |
| `conc` | (GDA) Top drug concentration in molar |
| `dil` | (GDA) Dilution factor |
| `xdrug` | (Synergy) Name of horizontal gradient drug |
| `xconc` | (Synergy) Horizontal top concentration |
| `xdil` | (Synergy) Horizontal dilution factor |
| `ydrug` | (Synergy) Name of vertical gradient drug |
| `yconc` | (Synergy) Vertical top concentration |
| `ydil` | (Synergy) Vertical dilution factor |

Note: You can leave columns blank if they do not apply to the specific module for that row.

### Output Locations

By default, analysis modules create output in `./cellpyability_output/` (in your current working directory):
- GDA: `./cellpyability_output/gda_output/`
- Synergy: `./cellpyability_output/synergy_output/`
- Simple: `./cellpyability_output/simple_output/`

You can customize the output location using the `--output-dir` flag:
```bash
cellpyability gda --output-dir /path/to/results ...
```

This ensures the package works correctly whether installed via PyPI or in development mode.

## Running the Code-Free Application
Running the code-free application requires no programming experience, Python environment, or dependencies. It contains all three modules with graphical user interfaces (GUIs) for user inputs.

📥 **[Download the latest release here](https://github.com/bindralab/cellpyability/releases/latest)**

Navigate to the bottom of the release notes and download the `.zip` file for your respective operating system.

After opening the .zip files, the CellPyAbility application can be run.

**Note for macOS users**

Because this application is an open-source tool and not signed via the paid Apple Developer program, macOS Gatekeeper will automatically quarantine the downloaded `.zip` file.

To run the application, extract the folder, open your Terminal, and run the following command to clear the quarantine flag before double-clicking the app:

```bash
xattr -dr com.apple.quarantine /path/to/extracted/CellPyAbility_Folder

```

Once running, a GUI prompts the user to choose from the three modules or the batch feature. Hovering over each button will give a description of its uses:

- **GDA**: dose-response analysis of two cell lines in response to one treatment

- **synergy**: dose-response analysis of one cell line in response to two treatments in combination

- **simple**: nuclei count matrix in a 96-well format

- **batch**: use the provided config.csv to run multiple jobs in a batch

After selecting a module, the application will look for CellProfiler in the default save locations:
- Windows
  - "C:\Program Files\CellProfiler\CellProfiler.exe"
  - "C:\Program Files (x86)\CellProfiler\CellProfiler.exe"
- MacOS
  - "/Applications/CellProfiler.app/Contents/MacOS/cp"

If CellProfiler cannot be found, the user will be prompted to input the path to the CellProfiler file via a dialog box. The path is saved to a .txt file within the directory for future reference, so subsequent runs will proceed directly to the next step.

A GUI specific to each module will prompt the user for experimental details. Using the GDA module as an example:
- title of the experiment (e.g. 20250101_CellLine_Drug)

- name of the cell condition in rows B-D (e.g. Cell Line Wildtype)

- name of the cell condition in rows E-G (e.g. Cell Line Gene A KO)

- top on-cell concentration in molar (if cells in column 11 are in 1 uM of drug: 0.000001)

- the dilution factor between columns (if 3-fold dilutions between each column: 3)

- a file browser to select the directory containing the 60 images

After submitting the GUI, a terminal window will open to track CellProfiler's image analysis progress. Once all images are counted, subsequent analysis is almost instant. All figures and tabular results will be in a subdirectory named after the module (e.g. gda_output). See [Example Outputs](#example-outputs).

A small GUI window will then prompt the user if they would like to run another experiment. If "yes", the initial module selection GUI will prompt the user again. If "no", the application will close.

A log file with detailed logging is written to the directory. If the application fails at any point, it may be useful to consult the log for critical messages or to identify the last step to succeed.

## Example Outputs
### GDA Module
The GDA module outputs three tabular files with increasing degrees of analysis:
- [raw nuclei counts](example/example_expected_outputs/test_gda_counts.csv)

- [normalized cell viability matrix](example/example_expected_outputs/test_gda_ViabilityMatrix.csv)

- [cell viability statistics](example/example_expected_outputs/test_gda_Stats.csv)

Additionally, the script generates a plot with 5-parameter logistic curves:

![GDA plot](example/example_expected_outputs/test_gda_plot.png)
### Synergy Module
The synergy module outputs four tabular files:
- [raw nuclei counts](example/example_expected_outputs/test_synergy_counts.csv)

- [normalized cell viability matrix](example/example_expected_outputs/test_synergy_ViabilityMatrix.csv)

- [cell viability statistics](example/example_expected_outputs/test_synergy_stats.csv)

- [Bliss synergy matrix](example/example_expected_outputs/test_synergy_BlissMatrix.csv)

Additionally, the script generates an interactive [3D surface map](example/example_expected_outputs/test_synergy_plot.html) in HTML with synergy as heat:

![synergy plot](example/example_expected_outputs/test_synergy_plot_static.png)

### Simple Module
Finally, the simple module outputs nuclei counts in a 96-well matrix format. This offers maximum flexibility but does not provide any analysis.
- [count matrix](example/example_expected_outputs/test_simple_CountMatrix.csv)

## Modifying the CellProfiler Pipeline

Across multiple cell lines and densities, our provided [CellProfiler Pipeline](src/cellpyability/CellPyAbility.cppipe) appears robust. However, if the user wishes to make any changes, a few guidelines must be followed to maintain compatibility with the scripts as written:
- The module output names must remain as:
  - Count_nuclei
  - FileName_images

- The CellProfiler output CSV file name must remain as:
  - path/to/src/cellpyability/cp_output/CellPyAbilityImage.csv

The modularity of the Python scripts and CellProfiler pipeline may prove useful. For example, if the user wishes to use all 96 wells instead of 60, minor Python knowledge and effort would be needed to enact this change. As another example, the user could analyze microscope images of 10x magnification instead of 4x magnification by increasing the expected pixel ranges for nuclei in the [CellProfiler pipeline](src/cellpyability/CellPyAbility.cppipe).

## Testing

CellPyAbility includes comprehensive testing infrastructure for both automated validation and manual verification.

### Automated Tests

Run the automated test suite to verify all modules produce expected outputs:

```bash
# Install the package if not already installed
pip install -e .

# Run all module tests
python tests/test_module_outputs.py
```

The test suite validates that each module (GDA, Synergy, Simple) produces output matching expected results when processing test data. All tests should pass before using CellPyAbility for your experiments.

**Test Results:**
- ✅ GDA Module: Verifies dose-response analysis accuracy
- ✅ Synergy Module: Verifies drug combination and Bliss independence calculations  
- ✅ Simple Module: Verifies nuclei count matrix generation

Test data is located in `tests/data/` and includes:
- `test_gda_counts.csv`: Pre-counted nuclei for gda test
- `test_synergy_counts.csv`: Pre-counted nuclei for synergy test
- `test_*_Stats.csv`: Expected analysis outputs for validation

### Manual Testing with Example Data

For manual verification, the `example/` directory contains real experimental data that you can process yourself to verify you get identical results:

1. **Download Example Data:**
   ```bash
   git lfs pull  # Downloads large image files
   ```

2. **Run GDA Example:**
   ```bash
   cellpyability gda \
     --title test \
     --upper-name "Cell Line A" \
     --lower-name "Cell Line B" \
     --top-conc 0.000001 \
     --dilution 3 \
     --image-dir example/example_gda
   ```

3. **Compare Your Results:**
   - Your outputs in `src/cellpyability/gda_output/`
   - Expected outputs in `example/example_expected_outputs/`
   - [Test parameters](example/example_params.txt) used to generate examples

**Available Example Datasets:**
- [GDA test data](example/example_gda/): 60 well images for dose-response analysis
- [Synergy test data](example/example_synergy/): 180 well images for drug combination analysis
- [Expected outputs](example/example_expected_outputs/): Reference results for validation

This dual approach ensures both automated validation (for development/CI) and manual verification (to confirm your specific environment is working correctly).

**Note:** We have not tested the analysis scripts on protocols other than those provided. For best results, please follow the provided [protocol](protocol.pdf).

## Contributing
### Development Installation
Clone the repository for development and access to example data:

```bash
# Clone the repository
git clone https://github.com/bindralab/CellPyAbility
cd CellPyAbility

# Install in editable mode
pip install -e .

# Download example data (requires Git LFS)
git lfs pull

# Run GDA analysis with example data
cellpyability gda \
  --title "MyExperiment" \
  --upper-name "Cell Line A" \
  --lower-name "Cell Line B" \
  --top-conc 0.000001 \
  --dilution 3 \
  --image-dir example/example_gda

# Or test without CellProfiler using pre-counted data
cellpyability gda \
  --title test \
  --upper-name "Cell Line A" \
  --lower-name "Cell Line B" \
  --top-conc 0.000001 \
  --dilution 3 \
  --image-dir /tmp \
  --counts-file tests/data/test_gda_counts.csv \
  --no-plot
```

### Reporting Issues
If you encounter a bug or have a feature request, please open an issue on our [GitHub Issues](https://github.com/bindralab/CellPyAbility/issues) page. When reporting a bug, please include:
- Operating system with version
- Python and CellProfiler versions
- Exact command ran
- Full error traceback

### Submitting a Pull Request
We welcome community contributions! To submit a change:
1. Fork the repository and create a new branch for your feature/fix (`git checkout -b feature/feature-name`)
2. Ensure your code is readable and well-documented
3. Run the automated test suite (`python tests/test_module_outputs.py`) to ensure all tests pass
4. Commit your changes with a clear message and push them to your fork
5. Open a Pull Request against our `main` branch

## Acknowledgements
Summary information regarding the authors:
- James Elia (Yale Department of Pathology): lead developer and author.

- Sam Friedman, MS (Yale Center for Research Computing): programming mentorship.

- Ranjit Bindra, MD, PhD (Yale Department of Therapeutic Radiology): scientific mentorship and principal investigator.

- GitHub Copilot: assisted automated testing development and restructuring the repository for PyPI.

## Comments or Questions?
Please contact me at james.elia@yale.edu
