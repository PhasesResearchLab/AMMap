# AMMap
## Additive Manufacturing Mapping of Thermodynamic, Analytical, and Artificial Intelligence Models

AMMap utilizes the newly developed [nimplex](https://github.com/amkrajewski/nimplex/tree/main), a high-performance Nim library for generation of simplex grids to describe the complex space that represents the design space possible for alloys made with additive manufacturing.

`AMMap` uses several different methods out-of-the-box. These include thermodynamic equlibrium calculations, [Scheil-Gulliver solidification](https://en.wikipedia.org/wiki/Scheil_equation), and 5 different models for predicting cracking susceptibility.


## Installation
The primary installation requirement is *nimplex*, and can be installed via