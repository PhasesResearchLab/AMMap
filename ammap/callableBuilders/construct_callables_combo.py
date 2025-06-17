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
    
    # Read template files
    with open('ammap/templates/equilibrium_callable_template.py', 'r') as f:
        eq_template = f.read()
    with open('ammap/templates/scheil_callable_template.py', 'r') as f:
        scheil_template = f.read()
    with open('ammap/templates/hybrid_scheil_eq_callable_template.py', 'r') as f:
        hybrid_template = f.read()
        # hybrid_template = f.read().replace('{', '{{').replace('}', '}}')
        # hybrid_template = hybrid_template.replace('{{{{', '{{').replace('}}}}', '}}')
    
    # Process constraints
    constraints = data.get('constraints', [])
    eq_constraint = next((c for c in constraints if c['type'].lower() == 'equilibrium'), None)
    scheil_constraint = next((c for c in constraints if c['type'].lower() == 'scheil'), None)
    hybrid_constraint = next((c for c in constraints if c['type'].lower() == 'hybrid-scheil'), None)
    
    for callable_config in data['elementalSpaces']:
        name = callable_config['name']
        tdb_file = callable_config['tdb']
        elements = sorted(callable_config['elements'])
        
        # Generate a unique identifier based on elements and TDB file
        unique_id = hashlib.sha256(f"{'-'.join(elements)}_{tdb_file}".encode()).hexdigest()[:8]
        
        # Construct equilibrium callable if constraint exists
        if eq_constraint:
            eq_content = eq_template.format(
                tdb_file=tdb_file,
                temperature=eq_constraint.get('temperature', 1000),
                elements=elements,
                pressure=eq_constraint.get('pressure', 101325),
                feasible_phases=eq_constraint.get('feasiblePhases', [])
            )
            eq_output_file = f"{output_dir}/equilibrium_callable_{name}_{unique_id}.py"
            with open(eq_output_file, 'w') as f:
                f.write(eq_content)
            print(f"Equilibrium callable constructed: {eq_output_file}")
        
        # Construct Scheil callable if constraint exists
        if scheil_constraint:
            scheil_content = scheil_template.format(
                tdb_file=tdb_file,
                elements=elements,
                scheil_start_temperature=scheil_constraint.get('startTemperature', 2500),
                liquid_phase_name=scheil_constraint.get('liquidPhase', 'LIQUID'),
                step_temperature=scheil_constraint.get('step_temperature', 1)
            )
            scheil_output_file = f"{output_dir}/scheil_callable_{name}_{unique_id}.py"
            with open(scheil_output_file, 'w') as f:
                f.write(scheil_content)
            print(f"Scheil callable constructed: {scheil_output_file}")
        
        # Construct hybrid-Scheil callable if constraint exists
        if hybrid_constraint:
            hybrid_content = hybrid_template.format(
                dbf_path=tdb_file,
                elements=elements,
                liquid_phase=hybrid_constraint.get('liquidPhase', 'LIQUID'),
                start_temp=hybrid_constraint.get('startTemperature', 2500),
                step_temp=hybrid_constraint.get('step_temperature', 1),
                temp_min=hybrid_constraint.get('temp_min', 500),
                temp_max=hybrid_constraint.get('temp_max', 1000),
                temp_step=hybrid_constraint.get('temp_step', 50)
            )
            hybrid_output_file = f"{output_dir}/hybrid_scheil_callable_{name}_{unique_id}.py"
            with open(hybrid_output_file, 'w') as f:
                f.write(hybrid_content)
            print(f"Hybrid-Scheil callable constructed: {hybrid_output_file}")
        
        # Note: If both Scheil and hybrid-Scheil are present, the Scheil results from the hybrid-Scheil callable
        # can be reused, so no duplicate Scheil calculations are performed.

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python construct_callables.py <yaml_file>")
        sys.exit(1)
    
    construct_callables(sys.argv[1])