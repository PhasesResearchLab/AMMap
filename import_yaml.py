import yaml
import re
import argparse

parser = argparse.ArgumentParser(description='Process a YAML file.')  
parser.add_argument('filename', type=str, help='Path to the input YAML file')  
args = parser.parse_args() 

# Load the YAML file
with open(args.filename, 'r') as file:
    yaml_content = yaml.safe_load(file)

# Extract the designSpaces and elementalSpaces keys
design_spaces = yaml_content['designSpaces']
elemental_spaces = yaml_content['elementalSpaces']

# Combine all the names of each entry in designSpaces
# attainableSpaceComponents = []
# for entry in design_spaces:
#     components = re.findall(r'[A-Z][a-z]*', entry['name'])
#     attainableSpaceComponents.extend(components)
attainableSpaceComponents = [
    component
    for entry in design_spaces
    for component in re.findall(r'[A-Z][a-z]*', entry['name'])
]

# Remove duplicates and sort the list
attainableSpaceComponents = sorted(set(attainableSpaceComponents))

# Create a mapping of elemental spaces to their components
elemental_space_map = {space['name']: space['elements'] for space in elemental_spaces}

# Generate attainableSpaceComponentPositions
attainableSpaceComponentPositions = []
for entry in design_spaces:
    elemental_space = elemental_space_map[entry['elementalSpace']]
    position = [0] * len(attainableSpaceComponents)
    for i, component in enumerate(re.findall(r'[A-Z][a-z]*', entry['name'])):
        index = attainableSpaceComponents.index(component)
        for j, elem in enumerate(elemental_space):
            if elem == component:
                position[index] = entry['components'][i][j]
    attainableSpaceComponentPositions.append(position)

# Expand positions to match the order of attainableSpaceComponents
expanded_positions = []
for position in attainableSpaceComponentPositions:
    expanded_position = [0] * len(attainableSpaceComponents)
    for i, value in enumerate(position):
        expanded_position[i] = value
    expanded_positions.append(expanded_position)

print(attainableSpaceComponents)
print(expanded_positions)