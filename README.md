# AMMap
## Additive Manufacturing Mapping of Thermodynamic, Analytical, and Artificial Intelligence Models

AMMap utilizes the newly developed [nimplex](https://github.com/amkrajewski/nimplex/tree/main), a high-performance Nim library for generation of simplex grids to describe the complex space that represents the design space possible for alloys made with additive manufacturing.

`AMMap` uses several different CALPHAD based methods out-of-the-box. These include thermodynamic equlibrium calculations, [Scheil-Gulliver solidification](https://en.wikipedia.org/wiki/Scheil_equation), and 5 different models for predicting cracking susceptibility.

These methods can then be considered to find optimal paths in the space using any python compatible path tool.

GitHub Codespaces can be used for all parts, but lacks the computational strength for Scheil-Gulliver. These jobs require external computational time to calculate. Scheil results can be 
analysed in Codespaces

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/PhasesResearchLab/AMMap?quickstart=1)

## Installation
### `nimplex`
The primary installation requirement is *nimplex*, which only requirement is [Nim](https://nim-lang.org/)
([Installation Instructions](https://nim-lang.org/install.html)) which can be done with a single command on most Unix (Linux/MacOS) systems:
- with your distribution's package manager, for instance on Ubuntu/Debian **Linux**:
  ```cmd
  apt-get install nim
  ```
- on **MacOS**, assuming you have [Homebrew](https://brew.sh/) installed:
  ```cmd
  brew install nim
  ```
- using [**conda**](https://docs.conda.io/en/latest/) cross-platform package manager:
  ```cmd
  conda install -c conda-forge nim
  ```

Then, you can use the boundeled [Nimble](https://github.com/nim-lang/nimble) tool (pip-like package manager for Nim) to install two top-level dependencies: 
[arraymancer](https://github.com/mratsim/Arraymancer), which is a powerful N-dimensional array library, and [nimpy](https://github.com/yglukhov/nimpy) which 
helps with the Python bindings. You can do it with a single command:
```cmd
nimble install  -y arraymancer nimpy
```

Finally, you can clone the repository and compile the library with:
```cmd
git clone https://github.com/amkrajewski/nimplex
cd nimplex
nim c -r -d:release nimplex.nim --benchmark
```
which will compile the library and run a few benchmarks to make sure everything runs smoothly. You should then see a compiled binary file `nimplex` in the current directory which exposes the CLI tool.

If you want to use the **Python bindings**, you can compile the library with slightly different flags (depending on your system configuration) like so for Linux/MacOS:
```cmd
nim c --d:release --threads:on --app:lib --out:nimplex.so nimplex
```
and you should see a compiled library file `nimplex.so` in the current directory which can be immediately imported and used in Python.

### `python`
It is recommended to use new environements for all python projects, this can be done as follows:
```cmd
conda create -n AMMAP python=3.11 liblapack jupyter numpy pandas plotly scikit-learn
conda activate AMMAP
```
The required python requirements, if the environment is already existing:
```cmd
conda install -y python=3.11 liblapack jupyter numpy pandas plotly scikit-learn
```
### `CALPHAD`
Done using [pycalphad](https://pycalphad.org/docs/latest/) and a forked version of a python package for [scheil](https://github.com/pycalphad/scheil) found here: [scheil](https://github.com/HUISUN24/scheil)

```cmd
pip install git+https://github.com/HUISUN24/scheil.git
pip install pycalphad
```
### Optional Pathfinding used in Example
```cmd
pip install pqam-rmsadtandoc2023 pathfinding
```
