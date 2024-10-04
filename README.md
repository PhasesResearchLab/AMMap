# AMMap
## `A`dditive `M`anufacturing `Map`ping of Compositional Spaces with Thermodynamic, Analytical, and Artificial Intelligence Models

`AMMap` tool utilizes novel [`nimplex`](https://github.com/amkrajewski/nimplex/tree/main) high-performance Nim library for generation of simplex graphs, developed in our recent paper ([10.48550/arXiv.2402.03528](https://doi.org/10.48550/arXiv.2402.03528)), to describe the complex space that represents the design space possible for alloys made with additive manufacturing.

`AMMap` implements callables for several different CALPHAD based methods out-of-the-box and is set to grow rapidly in the near future. These include thermodynamic equlibrium calculations with `pycalphad`, [Scheil-Gulliver solidification](https://en.wikipedia.org/wiki/Scheil_equation) with `scheil`, and 5 different models for predicting cracking susceptibility. These methods are discussed in [this publication](https://doi.org/10.1016/j.addma.2023.103672) on *Design methodology for functionally graded materials: Framework for considering cracking*.

Results coming from these methods are used to establish feasible subspace, which is then used to find optimal paths in the space using any path planning tool with Python or CLI interface.

For user convenience, cloud-based GitHub Codespaces can be used for all `Jupyter` notebook exercises. However, one should note Codespaces lack the computational strength to perform Scheil-Gulliver sufficiently fast; thus we recommend running them on an HPC node, submitting for external evaluation with a tool like `papermill`, or persisting the result (see [`scheilmap.json`](scheilmap.json)) to then be analysed in Codespaces.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/PhasesResearchLab/AMMap?quickstart=1)

## Capabilities
***Note*** Full technical discussions will be in upcoming manuscript. Section below is a short highlights of tool ability. Visual representations of capabilities for example systems can be seen at end of README below
1. **Simplex/Compositional Graph Generation** to allow for compositionally complex materials with high order of possible combinations to be fully considered
2. **Stitching of elemental spaces from different thermodynamic databases into singular traversable graph** to allow for path planning across multiple composition regions from incompatible databases due to model differences
3. **Material Information Generation** Thermodynamic (Equilibrium and Scheil-Gulliver) information about the material at any given graph point calculated to determine phase composition to avoid undesired phase formation in path planning. Thermodynamic information can then be used to determine the hot-cracking susceptibility of a point to further inform material design.
4. **Infeasibility Gliding** Detects infeasible regions and avoids uneccessary calculations of interior points to reduce total computational cost
5. **Path Planning Compatibility** Deployment of any graph algorithms on created design space and highly compatible with backends of choice. Currently finds the shortest path which can be stretched. Found path can then be simplified to change from point-to-point path to generalized format

<div align="center">
  <img src="https://github.com/PhasesResearchLab/AMMap/blob/main/utils/images/ThreeTernary.png?raw=true" alt="alt text" width="800">
</div>

*Path planning across  elemental spaces from seperate thermodynamic databases demonstrated in the path planning from SS304L to pure Ti*

### Planned
1. **YAML format input** for human readable definition of design space, constraints, and objectives
2. **Expanded Property Models** More material properties that can be mapped onto compositional graphs are planned, e.g. elastic modulii
3. **Output of callables for Machine Learning**
4. **Path Planning Updates** to minimize the number of turns or more generally hyperplanes.
5. **Build Planning Algorithm** Collaboration to create algorithm to convert given path into physical AM build path for fabrication

## Installation

### Conda Environment and Installs
It is recommended to use new environements for all python projects, this can be done as follows:

```shell
conda create -n AMMAP python=3.11 liblapack jupyter numpy pandas plotly scikit-learn
```
```shell
conda activate AMMAP
```

Or, if your environment already exists, simply:
```shell
conda install -y python=3.11 liblapack jupyter numpy pandas plotly scikit-learn
```

### Clone repository
Clone the github repository in order to have the jupyter notebook and callables
```shell
git clone https://github.com/PhasesResearchLab/AMMap.git
```

### `nimplex`
The primary installation requirement is `nimplex`, which requires the small and easy-to-install [Nim](https://nim-lang.org/)
([Installation Instructions](https://nim-lang.org/install.html)) compiler (assuming you already have a `C` compiler), which can be done with a single command on most **Unix** (Linux/MacOS) systems:
- using [**conda**](https://docs.conda.io/en/latest/) cross-platform package manager:
  ```shell
  conda install -c conda-forge nim
  ```
- on **MacOS**, assuming you have [Homebrew](https://brew.sh/) installed:
  ```shell
  brew install nim
  ```
- with your Linux distribution's package manager (note that it may be an outdated `nim` version, impacting performance), for instance on Ubuntu/Debian **Linux**:
  ```shell
  apt-get install nim
  ```

Then, you can use the boundeled [Nimble](https://github.com/nim-lang/nimble) tool (`pip`-like package manager for Nim) to install two top-level dependencies: 
[`arraymancer`](https://github.com/mratsim/Arraymancer), which is a powerful N-dimensional array library, and [`nimpy`](https://github.com/yglukhov/nimpy) which 
helps with the Python bindings. You can do it with a single command:
```shell
nimble install -y arraymancer nimpy
```

Now, you can update the `nimplex` submodule repository and compile it for `AMMap`. You want to do so in a way that creates its **Python bindings**. You will need slightly different flags depending on your system configuration, but for Unix (Linux/MacOS) you can do so with commands below, after making sure you are in the root `AMMap` directory:
```shell
git submodule update --init --recursive
nim c --d:release --threads:on --app:lib --out:nimplex.so nimplex/src/nimplex.nim
nim c --d:release --threads:on --app:lib --out:utils/plotting.so nimplex/src/nimplex/utils/plotting.nim
```

For Windows and other platforms, you should consult [`nimpy`](https://github.com/yglukhov/nimpy) instructions.


### CALPHAD Tools
When you are done, you should also install [pycalphad](https://pycalphad.org/docs/latest/) and a forked version of a python package for [`scheil`](https://github.com/pycalphad/scheil) found [here](https://github.com/HUISUN24/scheil)

```shell
pip install git+https://github.com/HUISUN24/scheil.git
pip install pycalphad
```

### Optional Pathfinding used in Example
```shell
pip install pqam-rmsadtandoc2023 pathfinding
```

### Other useful packages
To run `Jupyter` notebooks from the command line, especially useful on an HPC, you should install `papermill`:
```shell
pip install papermill
```

# Example Outputs 
## Equilibrium
<div align="center">
  
![alt text](https://github.com/PhasesResearchLab/AMMap/blob/main/utils/images/eqFrac.png?raw=true)
</div>

## Cracking Criteria
<div align="center">

![alt text](https://github.com/PhasesResearchLab/AMMap/blob/main/utils/images/iCSC.png?raw=true)
</div>

## Path Planning
<div align="center">

![alt text](https://github.com/PhasesResearchLab/AMMap/blob/main/utils/images/path2.png?raw=true)
</div>
