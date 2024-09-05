# Template code requireing constants to be defined by the user or AMMap callable builder

from pymatgen.core.periodic_table import Element
from typing import List

def run(point: List[float], verbose: bool = False) -> bool:
    """
    Check if the point is feasible based on the LC density constraint (MIN/MAX), expressed in g/cm^3, and elemental space it exists in.
    """
    assert 'ELEMENTS' in globals(), 'ELEMENTS has to be defined'
    assert 'MAX' in globals() or 'MIN' in globals(), 'Either MAX or MIN has to be defined. Both can be defined too'
    assert len(point) == len(ELEMENTS), 'The length of the point must match the number of elements'
    
    total = sum(point)
    weightedDensities = [Element(ELEMENTS[i]).density_of_solid * frac * 0.001 for i, frac in enumerate(point)]
    density = round(sum(weightedDensities) / total, 6)
    if verbose: print(f"LC density: {density}")

    # Check if the LC density is within the bounds
    if 'MAX' in globals():
        if density > MAX:
            return False
    if 'MIN' in globals():
        if density < MIN:
            return False

    return True

if __name__ == '__main__':
    # Example usage
    MIN = 7
    MAX = 8
    ELEMENTS = ['Ni', 'Cr', 'Fe', 'V']
    points = [
        [0.25, 0.25, 0.25, 0.25],
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ]
    print(f"\nChecking points for feasibility in the elemental space: {ELEMENTS} with LC density between {MIN} and {MAX}")
    for point in points:
        print(run(point, verbose=True))