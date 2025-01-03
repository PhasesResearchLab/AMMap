#!/bin/bash

set -e

echo "Updating git submodules..."
git submodule update --init --recursive
echo "Git submodules updated successfully."

echo "Compiling nimplex..."
nim c --d:release --threads:on --app:lib --out:nimplex.so nimplex/src/nimplex.nim
echo "nimplex compiled successfully."

echo "Compiling plotting utility..."
nim c --d:release --threads:on --app:lib --out:utils/plotting.so nimplex/src/nimplex/utils/plotting.nim
echo "Plotting utility compiled successfully."

echo "Compiling stitching utility..."
nim c --d:release --threads:on --app:lib --out:utils/stitching.so nimplex/src/nimplex/utils/stitching.nim
echo "Stitching utility compiled successfully."

echo "Verifying installations..."
command -v nim >/dev/null 2>&1 || { echo >&2 "nim is not installed. Aborting."; exit 1; }
command -v python >/dev/null 2>&1 || { echo >&2 "python is not installed. Aborting."; exit 1; }
python -c "import numpy, pandas, plotly, sklearn" || { echo >&2 "Required Python packages are not installed. Aborting."; exit 1; }

echo "All installations and compilations completed successfully."
