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
    
    # Create a single directory based on the name given in the YAML
    output_dir = f"ammap/callables/{base_name}"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        Path(f"{output_dir}/__init__.py").touch()
    
    # Read template files
    with open('ammap/templates/equilibrium_callable_template.py', 'r') as f:
        eq_template = f.read()
    
    with open('ammap/templates/scheil_callable_template.py', 'r') as f:
        scheil_template = f.read()
    
    # Read hybrid template if it exists
    hybrid_template = None
    hybrid_template_path = 'ammap/templates/hybrid_scheil_eq_callable_template.py'
    if os.path.exists(hybrid_template_path):
        with open(hybrid_template_path, 'r') as f:
            hybrid_template = f.read()
    
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
            temp_config = eq_constraint.get('temperature', 1000)
            
            # Check if temperature is a list [maxT, step_temperature, minT]
            if isinstance(temp_config, list) and len(temp_config) == 3:
                base_temp, step_temp, min_temp = temp_config
            else:
                # Fallback to single temperature value
                base_temp = temp_config if isinstance(temp_config, (int, float)) else 1000
                step_temp = None
                min_temp = base_temp

            if step_temp is not None:
                temp_list = list(range(base_temp, min_temp - 1, -step_temp))
                if not temp_list or temp_list[-1] > min_temp:
                    temp_list.append(min_temp)
            else:
                temp_list = [base_temp]

            eq_content = eq_template.format(
                tdb_file=tdb_file,
                temperature_list=temp_list,  # Will become np.array([...]) in template
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
        
        # Construct hybrid callable if constraint exists and template is available
        if hybrid_constraint and hybrid_template:
            hybrid_content = hybrid_template.format(
                dbf_path=tdb_file,
                elements=elements,
                liquid_phase=hybrid_constraint.get('liquidPhase', 'LIQUID'),
                start_temp=hybrid_constraint.get('startTemperature', 2500),
                step_temp=hybrid_constraint.get('step_temperature', 10),
                temp_min=hybrid_constraint.get('temp_min', 600),
                temp_max=hybrid_constraint.get('temp_max', 1200),
                temp_step=hybrid_constraint.get('temp_step', 50)
            )
            
            hybrid_output_file = f"{output_dir}/hybrid_callable_{name}_{unique_id}.py"
            with open(hybrid_output_file, 'w') as f:
                f.write(hybrid_content)
            
            print(f"Hybrid callable constructed: {hybrid_output_file}")
        elif hybrid_constraint and not hybrid_template:
            print(f"Warning: hybrid-scheil constraint found but template not available at {hybrid_template_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python construct_callables.py <yaml_file>")
        sys.exit(1)
    
    construct_callables(sys.argv[1])