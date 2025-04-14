import os
import sys
import hashlib
from ruamel.yaml import YAML
from pathlib import Path

# name: hybrid_scheil_eq_callables
# callables:
#   - name: example_callable
#     tdb: "path/to/database.tdb"
#     elements: ["AL", "CU", "MG"]
#     liquid_phase: "LIQUID"
#     start_temp: 1000
#     step_temp: 10
#     temp_min: 500
#     temp_max: 1000
#     temp_step: 50

def construct_callables(yaml_file):
    yaml = YAML(typ='safe')
    with open(yaml_file, 'r') as f:
        data = yaml.load(f)
    
    # Extract common information from YAML
    base_name = data['name']
    output_dir = f"ammap/callables/{base_name}"
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        Path(f"{output_dir}/__init__.py").touch()
    
    # Read the hybrid Scheil-equilibrium template file
    with open('ammap/templates/hybrid_scheil_eq_callable_template_perp.py', 'r') as f:
        template = f.read()
    
    # Process each callable configuration in the YAML file
    for callable_config in data['callables']:
        name = callable_config['name']
        tdb_file = callable_config['tdb']
        elements = callable_config['elements']
        liquid_phase = callable_config['liquid_phase']
        start_temp = callable_config['start_temp']
        step_temp = callable_config['step_temp']
        temp_min = callable_config['temp_min']
        temp_max = callable_config['temp_max']
        temp_step = callable_config['temp_step']
        
        # Generate a unique identifier for the callable
        unique_id = hashlib.sha256(f"{name}_{tdb_file}_{elements}".encode()).hexdigest()[:8]
        
        # Substitute placeholders in the template
        content = template.format(
            dbf_path=tdb_file,
            elements=elements,
            liquid_phase=liquid_phase,
            start_temp=start_temp,
            step_temp=step_temp,
            temp_min=temp_min,
            temp_max=temp_max,
            temp_step=temp_step
        )
        
        # Write the resulting script to a new file
        output_file = f"{output_dir}/{name}_{unique_id}.py"
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"Callable constructed: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python construct_callables.py <yaml_file>")
        sys.exit(1)
    
    construct_callables(sys.argv[1])