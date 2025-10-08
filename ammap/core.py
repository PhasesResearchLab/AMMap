import yaml
import numpy as np
import pandas as pd


import nimplex
from utils import plotting

class Task:
    def __init__(self, config_path):
        # Load YAML configuration
        with open(config_path, 'r') as f:
            self.yaml_content = yaml.safe_load(f)

        # Validate the YAML content
        self._validate_yaml_content()

        # Extract master list of elements from elementalSpaces
        self.elementalSpaceComponents = sorted(
            set(
                el
                for entry in self.yaml_content['elementalSpaces']
                for el in entry['elements']
            )
        )

        # Build dictionary mapping elemental space name to element list
        self.elementalSpaceComponents_by_name = {
            entry['name']: entry['elements']
            for entry in self.yaml_content['elementalSpaces']
        }

        # Build designSpaces dictionary with elements and components (expand components later)
        self.designSpaces_by_name = {}
        designSpace_master_elements = set()
        for entry in self.yaml_content['designSpaces']:
            name = entry['name']
            elemental_space_name = entry.get('elementalSpace', name)
            elemental_elements = self.elementalSpaceComponents_by_name[elemental_space_name]
            components = entry.get('components', [])
            if not components:
                components = np.eye(len(elemental_elements)).tolist()
            self.designSpaces_by_name[name] = {
                'elements': elemental_elements,
                'components': components
            }
            # Collect all unique elements in design space components
            for comp in components:
                for idx, val in enumerate(comp):
                    if val != 0:
                        designSpace_master_elements.add(elemental_elements[idx])
        self.designSpace_master_elements = sorted(designSpace_master_elements)

        # Expand design space components to full master element list dimension
        self._expand_components_to_master()

        # Generate compositional graphs for each design space
        self.compositional_graphs_by_design_space = {}
        self._generate_compositional_graphs()

    # Flesh out this.
    def _validate_yaml_content(self):
        """
        Validate YAML content to ensure compatibility with AMMap requirements.
        Checks for mandatory fields and validates optional fields when present.
        """
        # Top-level mandatory fields
        required_top_level = ['name', 'nDivisionsPerDimension', 'elementalSpaces', 'designSpaces']
        
        for key in required_top_level:
            if key not in self.yaml_content:
                raise ValueError(f"Missing required top-level key: {key}")
        
        # Validate nDivisionsPerDimension is a positive integer
        if not isinstance(self.yaml_content['nDivisionsPerDimension'], int) or self.yaml_content['nDivisionsPerDimension'] <= 0:
            raise ValueError("nDivisionsPerDimension must be a positive integer")
        
        # Validate elementalSpaces
        if not isinstance(self.yaml_content['elementalSpaces'], list) or not self.yaml_content['elementalSpaces']:
            raise ValueError("elementalSpaces must be a non-empty list")
        
        elemental_space_names = set()
        for i, space in enumerate(self.yaml_content['elementalSpaces']):
            if not isinstance(space, dict):
                raise ValueError(f"elementalSpaces[{i}] must be a dictionary")
            
            # Required fields for each elemental space
            required_elemental = ['name', 'elements']
            for key in required_elemental:
                if key not in space:
                    raise ValueError(f"Missing required key '{key}' in elementalSpaces[{i}]")
            
            # Validate name is unique
            if space['name'] in elemental_space_names:
                raise ValueError(f"Duplicate elemental space name: {space['name']}")
            elemental_space_names.add(space['name'])
            
            # Validate elements is a non-empty list
            if not isinstance(space['elements'], list) or not space['elements']:
                raise ValueError(f"elementalSpaces[{i}]['elements'] must be a non-empty list")
            
            # Validate all elements are strings
            for j, element in enumerate(space['elements']):
                if not isinstance(element, str):
                    raise ValueError(f"elementalSpaces[{i}]['elements'][{j}] must be a string")
            
            # If tdb is present, validate it's a string
            if 'tdb' in space and not isinstance(space['tdb'], str):
                raise ValueError(f"elementalSpaces[{i}]['tdb'] must be a string")
        
        # Validate designSpaces
        if not isinstance(self.yaml_content['designSpaces'], list) or not self.yaml_content['designSpaces']:
            raise ValueError("designSpaces must be a non-empty list")
        
        design_space_names = set()
        for i, space in enumerate(self.yaml_content['designSpaces']):
            if not isinstance(space, dict):
                raise ValueError(f"designSpaces[{i}] must be a dictionary")
            
            # Required field for each design space
            if 'name' not in space:
                raise ValueError(f"Missing required key 'name' in designSpaces[{i}]")
            
            # Validate name is unique
            if space['name'] in design_space_names:
                raise ValueError(f"Duplicate design space name: {space['name']}")
            design_space_names.add(space['name'])
            
            # If elementalSpace is specified, validate it exists
            if 'elementalSpace' in space:
                if space['elementalSpace'] not in elemental_space_names:
                    raise ValueError(f"designSpaces[{i}]['elementalSpace'] '{space['elementalSpace']}' not found in elementalSpaces")
            else:
                # If not specified, the name should match an elemental space
                if space['name'] not in elemental_space_names:
                    raise ValueError(f"designSpaces[{i}]['name'] '{space['name']}' not found in elementalSpaces and no elementalSpace specified")
            
            # If components is present, validate it
            if 'components' in space:
                if not isinstance(space['components'], list):
                    raise ValueError(f"designSpaces[{i}]['components'] must be a list")
                
                # Get the corresponding elemental space to validate component dimensions
                elemental_space_name = space.get('elementalSpace', space['name'])
                elemental_space = next(es for es in self.yaml_content['elementalSpaces'] if es['name'] == elemental_space_name)
                expected_length = len(elemental_space['elements'])
                
                for j, component in enumerate(space['components']):
                    if not isinstance(component, list):
                        raise ValueError(f"designSpaces[{i}]['components'][{j}] must be a list")
                    if len(component) != expected_length:
                        raise ValueError(f"designSpaces[{i}]['components'][{j}] must have {expected_length} elements to match elemental space")
                    
                    # Validate all component values are numbers
                    for k, val in enumerate(component):
                        if not isinstance(val, (int, float)):
                            raise ValueError(f"designSpaces[{i}]['components'][{j}][{k}] must be a number")
        
        # Validate optional constraints section
        if 'constraints' in self.yaml_content:
            self._validate_constraints()
        
        # Validate optional pathPlan section
        if 'pathPlan' in self.yaml_content:
            self._validate_path_plan()

    def _validate_constraints(self):
        """Validate the constraints section if present."""
        constraints = self.yaml_content['constraints']
        if not isinstance(constraints, list):
            raise ValueError("constraints must be a list")
        
        for i, constraint in enumerate(constraints):
            if not isinstance(constraint, dict):
                raise ValueError(f"constraints[{i}] must be a dictionary")
            
            if 'type' not in constraint:
                raise ValueError(f"Missing required key 'type' in constraints[{i}]")
            
            constraint_type = constraint['type'].lower()
            
            if constraint_type == 'equilibrium':
                # Required: temperature, pressure, feasiblePhases
                required_eq = ['temperature', 'pressure', 'feasiblePhases']
                for key in required_eq:
                    if key not in constraint:
                        raise ValueError(f"Missing required key '{key}' in equilibrium constraint[{i}]")
                
                # Validate temperature format
                temp = constraint['temperature']
                if not (isinstance(temp, (int, float)) or 
                    (isinstance(temp, list) and len(temp) == 3 and all(isinstance(x, (int, float)) for x in temp))):
                    raise ValueError(f"constraints[{i}]['temperature'] must be a number or [maxT, step, minT] list")
                
                # Validate feasiblePhases is a list
                if not isinstance(constraint['feasiblePhases'], list):
                    raise ValueError(f"constraints[{i}]['feasiblePhases'] must be a list")
            
            elif constraint_type == 'scheil':
                # Required: startTemperature, liquidPhase
                required_scheil = ['startTemperature', 'liquidPhase']
                for key in required_scheil:
                    if key not in constraint:
                        raise ValueError(f"Missing required key '{key}' in scheil constraint[{i}]")
                
                if not isinstance(constraint['startTemperature'], (int, float)):
                    raise ValueError(f"constraints[{i}]['startTemperature'] must be a number")
            
            elif constraint_type == 'cracking':
                # Required: criteria
                if 'criteria' not in constraint:
                    raise ValueError(f"Missing required key 'criteria' in cracking constraint[{i}]")
                
                if not isinstance(constraint['criteria'], list):
                    raise ValueError(f"constraints[{i}]['criteria'] must be a list")

    def _validate_path_plan(self):
        """Validate the pathPlan section if present."""
        path_plan = self.yaml_content['pathPlan']
        if not isinstance(path_plan, list):
            raise ValueError("pathPlan must be a list")
        
        design_space_names = {ds['name'] for ds in self.yaml_content['designSpaces']}
        
        for i, step in enumerate(path_plan):
            if not isinstance(step, dict):
                raise ValueError(f"pathPlan[{i}] must be a dictionary")
            
            if 'designSpace' in step:
                if step['designSpace'] not in design_space_names:
                    raise ValueError(f"pathPlan[{i}]['designSpace'] '{step['designSpace']}' not found in designSpaces")
                
                if 'composition' in step:
                    if not isinstance(step['composition'], list):
                        raise ValueError(f"pathPlan[{i}]['composition'] must be a list")
                    
                    # Validate composition values are numbers
                    for j, val in enumerate(step['composition']):
                        if not isinstance(val, (int, float)):
                            raise ValueError(f"pathPlan[{i}]['composition'][{j}] must be a number")

    def __str__(self):
        """
        String representation of the Task object.
        Print out the important information Task generates in a nicely
        formatted way.
        """
        result = "Task Information:\n"
        result += f"  - Number of elemental spaces: {len(self.elementalSpaceComponents)}\n"
        result += f"  - Number of design spaces: {len(self.designSpaces_by_name)}\n"
        result += f"  - Master elements: {self.elementalSpaceComponents}\n"
        result += f"  - Design space master elements: {self.designSpace_master_elements}"
        return result

    def _expand_components_to_master(self):
        for name, ds in self.designSpaces_by_name.items():
            elements = ds['elements']
            components = ds['components']
            idx_map = [self.elementalSpaceComponents.index(el) for el in elements]
            expanded_components = []
            for comp in components:
                expanded = [0] * len(self.elementalSpaceComponents)
                for local_idx, val in enumerate(comp):
                    master_idx = idx_map[local_idx]
                    expanded[master_idx] = val
                expanded_components.append(expanded)
            ds['components_master'] = expanded_components

    def _generate_compositional_graphs(self):
        ndiv = self.yaml_content.get('nDivisionsPerDimension', 6)
        for name, ds in self.designSpaces_by_name.items():
            components_master = ds['components_master']
            dim = len(components_master)
            gridAtt, nList = nimplex.simplex_graph_py(dim, ndiv)
            edges = []
            for i in range(len(gridAtt)):
                for n in nList[i]:
                    edges.append((i, n))

            gridAttTemp, gridElTemp = nimplex.embeddedpair_simplex_grid_fractional_py(components_master, ndiv)
            self.compositional_graphs_by_design_space[name] = {
                "edges": edges,
                "graphN": nList,
                "compositions": gridElTemp,
                "gridAtt": gridAtt,
                "components_master": components_master
            }

    def get_compositional_graph(self, design_space_name=None):
        if design_space_name is None:
            design_space_name = list(self.compositional_graphs_by_design_space.keys())[0]
        return self.compositional_graphs_by_design_space[design_space_name]

    def get_hover_formulas(self, design_space_name=None):
        if design_space_name is None:
            design_space_name = list(self.compositional_graphs_by_design_space.keys())[0]
        comp_graph = self.get_compositional_graph(design_space_name)
        compositions = comp_graph['compositions']
        formulas = []
        for i, comp in enumerate(compositions):
            formula = (f"({i:>3}) " +
                       "".join(f"{el}{100 * v:.1f} " if v > 0 else ""
                               for el, v in zip(self.elementalSpaceComponents, comp))
                       )
            formulas.append(formula)
        return formulas

    def get_projected_grid_df(self, design_space_name=None):
        if design_space_name is None:
            design_space_name = list(self.compositional_graphs_by_design_space.keys())[0]
        comp_graph = self.get_compositional_graph(design_space_name)
        gridAtt = comp_graph['gridAtt']
        df = pd.DataFrame(plotting.simplex2cartesian_py(gridAtt), columns=['x', 'y', 'z'])
        return df

    def get_pure_component_labels(self, design_space_name=None):
        if design_space_name is None:
            design_space_name = list(self.compositional_graphs_by_design_space.keys())[0]
        comp_graph = self.get_compositional_graph(design_space_name)
        dim = len(comp_graph['components_master'])
        ndiv = self.yaml_content.get('nDivisionsPerDimension', 6)
        attainableSpaceComponents = self.designSpaces_by_name[design_space_name]['elements']
        pureComponentIndices = nimplex.pure_component_indexes_py(dim, ndiv)
        labels = [''] * len(comp_graph['gridAtt'])
        for comp, idx in zip(attainableSpaceComponents, pureComponentIndices):
            labels[idx] = "<b>" + comp + "</b>"
        return labels