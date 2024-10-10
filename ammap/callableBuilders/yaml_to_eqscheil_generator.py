#This script will read the input yaml file, and if it requests equilibrium or scheil calculation, it will generate
#the corresponding python script. The script will be saved in the ammap/callables directory. The script will be based on
#the template from ammap/templates/EqScheil.py. The script will be generated with the name and of the yaml file and a uniquely
# generated hash.

import yaml
import hashlib
import os
from pathlib import Path
import sys
import re

def generate_eqscheil_script(yaml_file_path, template_file_path):
    # Read the YAML file
    with open(yaml_file_path, 'r') as yaml_file:
        data = yaml.safe_load(yaml_file)
    
    # Read the template file
    with open(template_file_path, 'r') as template_file:
        template = template_file.read()
    
    # Extract necessary information from YAML
    name = data.get('name', 'unnamed')
    database = data.get('database', '')
    temperature = data.get('temperature', 1000)
    elements = data.get('elementalSpaceComponents', [])
    scheil_start_temperature = data.get('scheilStartTemperature', 2000)
    liquid_phase_name = data.get('liquidPhaseName', 'LIQUID')
    pressure = data.get('pressure')  # Get pressure if it exists
    
    # Generate a hash for the YAML file content
    yaml_hash = hashlib.sha256(str(data).encode()).hexdigest()[:6]
    
    # Construct the output directory and file name
    yaml_file_name = os.path.splitext(os.path.basename(yaml_file_path))[0]
    output_dir = f"ammap/callables/{yaml_file_name}_{yaml_hash}_{''.join(elements)}"
    output_file = f"{output_dir}/{yaml_file_name}_EqScheil.py"
    
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    Path(f'{output_dir}/__init__.py').touch()
    
    # Replace variables in the template
    script_content = template
    script_content = script_content.replace("Database(\"ammap/databases/TDB\")", f"Database(\"{database}\")")
    script_content = script_content.replace("T = 'TEMPERATURE'", f"T = {temperature}")
    script_content = script_content.replace("elementalSpaceComponents = 'ELEMENTS'", f"elementalSpaceComponents = {elements}")
    script_content = script_content.replace("scheil_start_temperature = 'startTemperature'", f"scheil_start_temperature = {scheil_start_temperature}")
    script_content = script_content.replace("liquid_phase_name = 'LIQUIDPHASE'", f"liquid_phase_name = '{liquid_phase_name}'")
    
    # Update default_conds with pressure if provided
    if pressure is not None:
        script_content = script_content.replace("default_conds={v.P: 101325, v.N: 1.0}", f"default_conds={{v.P: {pressure}, v.N: 1.0}}")
    
    # Update the comment about the number of elements
    num_elements = len(elements)
    script_content = re.sub(r'# Problem Specific setup for our \d+-element space exploration', 
                            f'# Problem Specific setup for our {num_elements}-element space exploration', 
                            script_content)
    
    # Write the generated Python script to a file
    with open(output_file, 'w') as output_file:
        output_file.write(script_content)

    print(f"EqScheil script generated and saved to {output_file}")

def main(yaml_file_path):
    # Check if the YAML file exists
    if not os.path.exists(yaml_file_path):
        print(f"Error: YAML file '{yaml_file_path}' not found.")
        sys.exit(1)
    
    # Read the YAML file
    with open(yaml_file_path, 'r') as yaml_file:
        data = yaml.safe_load(yaml_file)
    
    # Check if constraints key exists
    if 'constraints' not in data:
        print("No constraints found in the YAML file.")
        sys.exit(0)
    
    # Check for equilibrium or scheil constraints
    equilibrium_constraint = any(constraint.get('type', '').lower() == 'equilibrium' for constraint in data['constraints'])
    scheil_constraint = any(constraint.get('type', '').lower() == 'scheil' for constraint in data['constraints'])
    
    if not (equilibrium_constraint or scheil_constraint):
        print("No equilibrium or scheil constraint found in the YAML file.")
        sys.exit(0)
    
    # If we reach here, we have either equilibrium or scheil constraint (or both)
    template_file_path = 'ammap/templates/EqScheil_template.py'
    if not os.path.exists(template_file_path):
        print(f"Error: Template file '{template_file_path}' not found.")
        sys.exit(1)
    
    generate_eqscheil_script(yaml_file_path, template_file_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <path_to_yaml_file>")
        sys.exit(1)
    
    yaml_file_path = sys.argv[1]
    main(yaml_file_path)