import os
import sys
import hashlib
from ruamel.yaml import YAML
from pathlib import Path

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
    with open('ammap/templates/hybrid_scheil_eq_callable_template.py', 'r') as f:
        template = f.read()
    
    # Find hybrid-scheil constraint
    hybrid_constraint = None
    for constraint in data['constraints']:
        if constraint['type'] == 'hybrid-scheil':
            hybrid_constraint = constraint
            break
    
    if not hybrid_constraint:
        raise ValueError("No hybrid-scheil constraint found in YAML")
    
    # Process each elemental space
    for elem_space in data['elementalSpaces']:
        name = elem_space['name']
        tdb_file = elem_space['tdb']
        elements = sorted(elem_space['elements'])  
        
        # Extract parameters from hybrid constraint
        liquid_phase = hybrid_constraint['liquidPhase']
        start_temp = hybrid_constraint['startTemperature']
        step_temp = hybrid_constraint['step_temperature']
        temp_min = hybrid_constraint['temp_min']
        temp_max = hybrid_constraint['temp_max']
        temp_step = hybrid_constraint['temp_step']
        
        # Generate a unique identifier based on elements and TDB file 
        unique_id = hashlib.sha256(f"{'-'.join(elements)}_{tdb_file}".encode()).hexdigest()[:8]
        
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
        output_file = f"{output_dir}/hybrid_callable_{name}_{unique_id}.py"
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"Hybrid callable constructed: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python construct_callables.py <yaml_file>")
        sys.exit(1)
    
    construct_callables(sys.argv[1])