import yaml

def update_feasible_phases_in_yaml(yaml_file, phase_list=None, constraint_types=['equilibrium', 'scheil'], overwrite=True):
    """
    Update feasiblePhases in YAML constraints to include a list of common names for HCP, FCC, and BCC phases, the standard "feasible" phases.
    
    Parameters:
    yaml_file: path to YAML file
    phase_list: list of phases to set (if None, uses default list)
    constraint_types: list of constraint types to update ('equilibrium', 'scheil', or both)
    overwrite: if True, replaces existing phases; if False, only adds if feasiblePhases doesn't exist
    """
    
    # Default phase list from your code
    if phase_list is None:
        phase_list = [
            'FCC_A1', 'BCC_A2', 'HCP_A3', 'B2_BCC', 'A2_FCC', 
            'L12_FCC', 'BCC2', 'A1', 'A2', 'A3', 'FCC4'
        ]
    
    # Load YAML file
    with open(yaml_file, 'r') as f:
        yaml_content = yaml.safe_load(f)
    
    # Track changes made
    changes_made = False
    
    # Update constraints
    for constraint in yaml_content.get('constraints', []):
        constraint_type = constraint.get('type', '').lower()
        
        if constraint_type in constraint_types:
            # Check if we should update
            should_update = False
            
            if overwrite:
                should_update = True
                action = "Updated"
            else:
                if 'feasiblePhases' not in constraint:
                    should_update = True
                    action = "Added"
            
            if should_update:
                constraint['feasiblePhases'] = phase_list.copy()
                changes_made = True
                print(f"{action} feasiblePhases for {constraint_type} constraint")
    
    # Save updated YAML file if changes were made
    if changes_made:
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f, default_flow_style=False, sort_keys=False)
        print(f"Updated {yaml_file} with feasiblePhases")
    else:
        print("No changes made to YAML file")
    
    return changes_made

# Example usage:

# Update both equilibrium and scheil constraints (default behavior)
update_feasible_phases_in_yaml('CONICRFE_input.yaml')

# Update only equilibrium constraints
# update_feasible_phases_in_yaml('CONICRFE_input.yaml', constraint_types=['equilibrium'])

# Update only scheil constraints  
# update_feasible_phases_in_yaml('CONICRFE_input.yaml', constraint_types=['scheil'])

# Only add if feasiblePhases doesn't exist (don't overwrite)
# update_feasible_phases_in_yaml('CONICRFE_input.yaml', overwrite=False)

# Use custom phase list
# custom_phases = ['FCC_A1', 'BCC_A2', 'HCP_A3']
# update_feasible_phases_in_yaml('CONICRFE_input.yaml', phase_list=custom_phases)