"""This module is a script that reads the AMMap configuration YAML file and if it detects ``type: LC density`` under 
the ``constraints`` key, it will proceed further. It will read the ``name`` key, append it with truncated (6 
characters) hash of the YAML file, append it with list of elements forming the elemental spcae, and use it as the 
name and if the directory with the name does not exist under the ``ammap/callables`` directory, it will create one 
and also create a ``__init__.py`` file to make it a package. It will then read the ``ammap/templates/LCdensity.py``, 
prepend it with constants based on the YAML file, and write it to the output directory.
"""
from ruamel.yaml import YAML
import os
import hashlib
from pathlib import Path
import sys

# Read the AMMap configuration YAML file in a safe way
yaml = YAML(typ='safe')
with open(sys.argv[1], 'r') as f:
    data = yaml.load(f)

def constructCallable(name: str, hash: str, data: dict):
    """Constructs the callable based on the name, hash, and data.

    Args:
        name: The name of the callable extracted from the YAML file.
        hash: The truncated hash of the YAML file. Uses the default hashlib hashing algorithm (SHA256).
        data: The data from the YAML file needed to set up the callable, including the elemental space components
            and constraint min / max values to be enforced when evaluating the feasibility of a point.
    """
    # Extract the elements from the data and verify compliance
    elements = data['elements']
    assert isinstance(elements, list), 'Elements key must be a list'
    assert all(isinstance(element, str) for element in elements), 'Elements key must be a list of strings'
    assert len(elements) > 0, 'Elements key must have at least one element'

    # Construct the output directory name
    output = f"{name}_{hash}_{''.join(elements)}"
    print(f"Constructing the callable: {output}")
    
    # Check if the directory exists, if not create it
    if not os.path.exists(f'ammap/callables/{output}'):
        os.makedirs(f'ammap/callables/{output}')
        Path(f'ammap/callables/{output}/__init__.py').touch()

    # Read the template file
    with open('ammap/templates/EqScheil.py', 'r') as f:
        template = f.read()

    # Prepend the template with the constants based on the YAML file
    constantsPayload = "# Constants based on the YAML file\n"
    if 'elements' not in data:
        raise ValueError('No elements key found in the YAML file')
    else:
        constantsPayload += f"ELEMENTS = {elements}\n"
    
    headerPayload = f'"""Linear Combination (atomic-fraction based) of elemental densities in {"-".join(elements)} system with constraints: '
    
    if 'min' in data:
        constantsPayload += f"MIN = {data['min']}\n"
        headerPayload += f"{data['min']}g/cm^3 < d"
    if 'max' in data:
        constantsPayload += f"MAX = {data['max']}\n"
        if 'min' in data:
            headerPayload += ' and '
        headerPayload += f"d < {data['max']}g/cm^3"

    headerPayload += '"""\n'
    
    payload = headerPayload + constantsPayload + '\n' + template

    # Create the output file and write the payload
    with open(f'ammap/callables/{output}/LCdensity.py', 'w') as f:
        f.write(payload)

# Check if the constraints key is present in the YAML file. Exit happily if not found.
if 'constraints' not in data:
    print('No constraints key found in the YAML file')
    sys.exit(0)

# Check if the LC density constraint is present in the YAML file. Exit happily if not found but raise an error if more than one is found.
constraintMatch = [constraint['type'].lower().replace(' ', '') == 'lcdensity' for constraint in data['constraints']]
if not any(constraintMatch):
    print('No LC density constraint found in the YAML file')
    sys.exit(0)
elif sum(constraintMatch) > 1:
    raise ValueError('More than one LC density constraint found in the YAML file')
else:
    pass

# Check if the `elementalSpaces` list is present, is a list, and has at least one element. Exit with an error if not.
if 'elementalSpaces' not in data:
    raise ValueError('No elementalSpaces key found in the YAML file')
elif not isinstance(data['elementalSpaces'], list):
    raise ValueError('elementalSpaces key must be a list')
elif len(data['elementalSpaces']) == 0:
    raise ValueError('elementalSpaces key must have at least one element')

# For each item under the `elementalSpaces` key, extract key information, elements, and construct the callable.
constraintIndex = constraintMatch.index(True)
constraint = data['constraints'][constraintIndex]
name = data['name']
hash = hashlib.sha256(str(data).encode()).hexdigest()[:6]

for es in data['elementalSpaces']:
    data = {'elements': es['elements']}
    if 'min' in constraint:
        data.update({'min': constraint['min']})
    if 'max' in constraint:
        data.update({'max': constraint['max']})
    constructCallable(name, hash, data)


        
