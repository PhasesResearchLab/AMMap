import numpy as np
import pandas as pd
import math
from scheil import simulate_scheil_solidification
from pycalphad import Database, equilibrium, variables as v
from pycalphad.core.utils import filter_phases, instantiate_models, unpack_components
from pycalphad.codegen.callables import build_phase_records

dbf = Database("{dbf_path}")

T = {start_temp}
elementalSpaceComponents = {elements}  # Ensure this is formatted as a Python list
phases = list(set(dbf.phases.keys()))
comps = [s.upper() for s in elementalSpaceComponents] + ['VA']
phases_filtered = filter_phases(dbf, unpack_components(dbf, comps), phases)
models = instantiate_models(dbf, comps, phases_filtered)

phase_records = build_phase_records(
    dbf, comps, phases_filtered,
    {{v.N, v.P, v.T}},
    models=models
)

liquid_phase_name = '{liquid_phase}'
step_temperature = {step_temp}
temp_min = {temp_min}
temp_max = {temp_max}
temp_step = {temp_step}

def hybrid_scheil_callable(elP):
    # Use the same composition handling as scheil_callable
    elP_round = [round(v-0.000001, 6) if v>0.000001 else 0.0000001 for v in elP]
    initial_composition = dict(zip([v.X(el) for el in comps[:-2]], elP_round))

    # Run Scheil simulation with configurable density
    try:
        sol_res = simulate_scheil_solidification(
            dbf, comps, phases_filtered,
            initial_composition, T, step_temperature=step_temperature)
    except Exception as e:
        return {{
            'scheil_result': None,
            'equilibrium_results': [],
            'error': str(e)
        }}

    # Extract solidification path data
    scheilT = sol_res.temperatures
    Sfrac = sol_res.fraction_solid
    x_phases = sol_res.x_phases  # Phase compositions
    cum_phase_amounts = sol_res.cum_phase_amounts  # Cumulative phase amounts
    
    # Calculate local compositions with HIGH DENSITY (~200 solid fraction points)
    local_compositions = []
    
    # Use high density - aim for ~200 composition points
    total_points = len(Sfrac)
    target_points = 200
    step_interval = max(1, total_points // target_points)  # This gives ~200 points
    
    for index in range(0, len(Sfrac), step_interval):
        if Sfrac[index] > 0.01:  # Consider very small solid fractions
            
            # Calculate incremental phase amounts (following temp_hybrid logic)
            phase_amounts_incremental = {{}}
            total_solid_incremental = 0
            
            for phase_name in cum_phase_amounts.keys():
                if phase_name != liquid_phase_name:
                    if index == 0:
                        phase_amount = cum_phase_amounts[phase_name][index] if index < len(cum_phase_amounts[phase_name]) else 0
                    else:
                        phase_amount_curr = cum_phase_amounts[phase_name][index] if index < len(cum_phase_amounts[phase_name]) else 0
                        phase_amount_prev = cum_phase_amounts[phase_name][index-1] if (index-1) < len(cum_phase_amounts[phase_name]) else 0
                        phase_amount = phase_amount_curr - phase_amount_prev
                    
                    if phase_amount > 1e-12:  # Lower threshold for more points
                        phase_amounts_incremental[phase_name] = phase_amount
                        total_solid_incremental += phase_amount
            
            if total_solid_incremental > 0:
                # Calculate weighted average composition
                local_comp = {{}}
                
                # Only use independent components (excluding last element which is dependent)
                independent_elements = elementalSpaceComponents[:-1]
                for el in independent_elements:
                    total_weighted_comp = 0
                    
                    for phase_name in phase_amounts_incremental.keys():
                        if phase_name in x_phases:
                            phase_fraction = phase_amounts_incremental[phase_name] / total_solid_incremental
                            
                            # Get element composition in this phase
                            el_comp = None
                            for el_key in [el.upper(), el.lower(), el.capitalize()]:
                                if el_key in x_phases[phase_name] and index < len(x_phases[phase_name][el_key]):
                                    comp_val = x_phases[phase_name][el_key][index]
                                    if not pd.isna(comp_val):
                                        el_comp = float(comp_val)
                                        break
                            
                            if el_comp is not None:
                                total_weighted_comp += phase_fraction * el_comp
                            else:
                                # Fallback to initial composition
                                el_idx = elementalSpaceComponents.index(el)
                                total_weighted_comp += phase_fraction * elP_round[el_idx]
                    
                    local_comp[v.X(el.upper())] = total_weighted_comp
                
                # More lenient validation for more data points
                total_comp = sum(local_comp.values())
                if 0.01 <= total_comp <= 0.99:  # Very broad range
                    local_compositions.append({{
                        'solid_fraction': Sfrac[index],
                        'temperature': scheilT[index],
                        'composition': local_comp,
                        'total_solid': total_solid_incremental,
                        'index': index
                    }})
    
    # Fallback if no local compositions found
    if not local_compositions:
        fallback_comp = {{}}
        for i, el in enumerate(elementalSpaceComponents[:-1]):
            fallback_comp[v.X(el.upper())] = elP_round[i]
        
        local_compositions = [{{
            'solid_fraction': 1.0,
            'temperature': scheilT[-1] if scheilT else T,
            'composition': fallback_comp,
            'total_solid': 1.0,
            'index': len(Sfrac)-1 if Sfrac else 0
        }}]
    
    # Perform equilibrium calculations at configurable temperature range
    T_eq_array = np.arange(temp_min, temp_max + temp_step, temp_step)  # Include endpoint
    eq_results = []
    
    for T_eq in T_eq_array:
        phase_fractions_at_T = []
        successful_calcs = 0
        
        # Run equilibrium with ALL local compositions
        for local_data in local_compositions:
            try:
                # Set up equilibrium conditions
                conds = {{v.T: float(T_eq), v.P: 101325, v.N: 1.0}}
                conds.update(local_data['composition'])
                
                # Run equilibrium calculation
                eq = equilibrium(
                    dbf, comps, phases_filtered,
                    conds, model=models, phase_records=phase_records
                )
                
                # Extract phase fractions
                if eq is not None and hasattr(eq, 'NP'):
                    np_data = eq.NP.data.flatten()
                    phase_data = eq.Phase.data.flatten()
                    
                    valid_phases = [str(p) for p in phase_data if str(p) != '']
                    valid_amounts = [float(a) for a in np_data if not math.isnan(a)]
                    
                    if valid_phases and valid_amounts:
                        phase_fractions_at_T.append({{
                            'phases': valid_phases,
                            'amounts': valid_amounts,
                            'weight': local_data['solid_fraction'],
                            'composition': local_data['composition']
                        }})
                        successful_calcs += 1
                    
            except Exception:
                continue
        
        # Integration across ALL solid fraction points
        if phase_fractions_at_T:
            # Calculate weighted average of phase fractions across ALL local compositions
            all_phases = set()
            for pf in phase_fractions_at_T:
                all_phases.update(pf['phases'])
            
            integrated_phases = {{}}
            total_weight = sum(pf['weight'] for pf in phase_fractions_at_T)
            
            for phase in all_phases:
                weighted_sum = 0
                contributing_weight = 0
                
                for pf in phase_fractions_at_T:
                    if phase in pf['phases']:
                        phase_idx = pf['phases'].index(phase)
                        if phase_idx < len(pf['amounts']):
                            phase_fraction = pf['amounts'][phase_idx]
                            weight = pf['weight']
                            weighted_sum += phase_fraction * weight
                            contributing_weight += weight
                
                if contributing_weight > 0:
                    integrated_phases[phase] = weighted_sum / contributing_weight
            
            # Normalize phase fractions
            total_phase_fraction = sum(integrated_phases.values())
            if total_phase_fraction > 0:
                for phase in integrated_phases:
                    integrated_phases[phase] /= total_phase_fraction
            
            eq_results.append({{
                'Temperature': float(T_eq),
                'PhaseFractions': integrated_phases,
                # 'SuccessfulCalculations': successful_calcs,
                # 'TotalLocalCompositions': len(local_compositions)
            }})
    
    return {{
        'scheil_result': sol_res,
        'equilibrium_results': eq_results,
        'local_compositions_count': len(local_compositions),
        'temperature_range': (temp_min, temp_max, temp_step)
    }}

if __name__ == "__main__":
    pass
