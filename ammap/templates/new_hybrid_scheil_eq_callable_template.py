import numpy as np
import pandas as pd
import math
from scheil import simulate_scheil_solidification
from pycalphad import Database, equilibrium, variables as v
from pycalphad.core.utils import filter_phases, instantiate_models, unpack_components
from pycalphad.codegen.callables import build_phase_records

# --- Constants and placeholders defined at module level ---
DBF_PATH = "{dbf_path}"
ELEMENTAL_SPACE_COMPONENTS = {elements}
LIQUID_PHASE_NAME = '{liquid_phase}'
START_TEMP = {start_temp}
STEP_TEMPERATURE = {step_temp}
TEMP_MIN = {temp_min}
TEMP_MAX = {temp_max}
TEMP_STEP = {temp_step}

# --- Module-level cache to store initialized objects ---
# This dictionary is unique to each generated callable module.
_thermo_cache = {{}}

def _initialize_thermo_objects():
    """
    Initializes all necessary pycalphad objects and stores them in the
    module's private cache. This runs only once per worker process for this module.
    """
    dbf = Database(DBF_PATH)
    phases = list(set(dbf.phases.keys()))
    comps = [s.upper() for s in ELEMENTAL_SPACE_COMPONENTS] + ['VA']
    phases_filtered = filter_phases(dbf, unpack_components(dbf, comps), phases)
    models = instantiate_models(dbf, comps, phases_filtered)
    phase_records = build_phase_records(
        dbf, comps, phases_filtered,
        {{v.N, v.P, v.T}},
        models=models
    )
    # Populate the cache
    _thermo_cache['dbf'] = dbf
    _thermo_cache['comps'] = comps
    _thermo_cache['phases_filtered'] = phases_filtered
    _thermo_cache['models'] = models
    _thermo_cache['phase_records'] = phase_records


def hybrid_scheil_callable(elP):
    """
    Main callable function for Scheil and equilibrium calculations.
    It ensures thermodynamic objects are initialized before running simulations.
    """
    # If the cache is empty, this is the first time this callable
    # is being run in this worker process. Initialize everything.
    if not _thermo_cache:
        _initialize_thermo_objects()

    # Retrieve the required objects from the cache
    dbf = _thermo_cache['dbf']
    comps = _thermo_cache['comps']
    phases_filtered = _thermo_cache['phases_filtered']
    models = _thermo_cache['models']
    phase_records = _thermo_cache['phase_records']

    elP_round = [round(v - 0.000001, 6) if v > 0.000001 else 0.0000001 for v in elP]
    initial_composition_dict = dict(zip([v.X(el) for el in comps[:-2]], elP_round))

    # --- DIAGNOSTIC STEP: Check if the initial state is fully liquid ---
    try:
        conds = {{v.T: START_TEMP, v.P: 101325, v.N: 1.0}}
        conds.update(initial_composition_dict)
        eq_start = equilibrium(dbf, comps, phases_filtered, conds, model=models)
        
        phases_present = [str(p) for p in eq_start.Phase.values.flatten() if p]

        if [LIQUID_PHASE_NAME] != phases_present:
             return {{
                'scheil_result': None,
                'equilibrium_results': [],
                'error': 'Initial state at ' + str(START_TEMP) + 'K is not 100% liquid. Phases found: ' + str(phases_present)
            }}
            
    except Exception as e:
        return {{
            'scheil_result': None,
            'equilibrium_results': [],
            'error': 'Equilibrium check failed at start temp: ' + str(e)
        }}

    # --- Run Scheil simulation ---
    try:
        sol_res = simulate_scheil_solidification(
            dbf, comps, phases_filtered,
            initial_composition_dict, START_TEMP, step_temperature=STEP_TEMPERATURE)
    except Exception as e:
        return {{
            'scheil_result': None,
            'equilibrium_results': [],
            'error': 'Scheil simulation crashed: ' + str(e)
        }}

    if sol_res is None or LIQUID_PHASE_NAME not in sol_res.cum_phase_amounts:
        return {{
            'scheil_result': None,
            'equilibrium_results': [],
            'error': "Scheil simulation did not produce a valid solidification path."
        }}

    # Extract the required data from the sol_res object
    Sfrac = sol_res.fraction_solid.flatten()
    scheilT = sol_res.temperatures.flatten()
    cum_phase_amounts = sol_res.cum_phase_amounts
    x_phases = sol_res.x_phases

    # Extract solidification path data and convert to serializable format
    scheil_result_serializable = {{
        'temperatures': sol_res.temperatures.tolist() if sol_res.temperatures is not None else [],
        'fraction_solid': sol_res.fraction_solid.tolist() if sol_res.fraction_solid is not None else [],
        'x_phases': {{phase: {{el: comp.tolist() for el, comp in x.items()}} for phase, x in sol_res.x_phases.items()}},
        'cum_phase_amounts': {{phase: amount.tolist() for phase, amount in sol_res.cum_phase_amounts.items()}}
    }}

    # Calculate local compositions with HIGH DENSITY (~200 solid fraction points)
    local_compositions = []
    
    total_points = len(Sfrac)
    if total_points == 0:
        local_compositions.append({{
            'solid_fraction': 1.0,
            'temperature': START_TEMP,
            'composition': {{v.X(el.upper()): elP_round[i] for i, el in enumerate(ELEMENTAL_SPACE_COMPONENTS[:-1])}},
            'total_solid': 1.0,
            'index': 0
        }})
    else:
        target_points = 200
        step_interval = max(1, total_points // target_points)

    for index in range(0, len(Sfrac), step_interval):
        if Sfrac[index] > 0.01:  # Consider very small solid fractions
            
            phase_amounts_incremental = {{}}
            total_solid_incremental = 0
            
            for phase_name in cum_phase_amounts.keys():
                if phase_name != LIQUID_PHASE_NAME:
                    if index == 0:
                        phase_amount = cum_phase_amounts[phase_name][index] if index < len(cum_phase_amounts[phase_name]) else 0
                    else:
                        phase_amount_curr = cum_phase_amounts[phase_name][index] if index < len(cum_phase_amounts[phase_name]) else 0
                        phase_amount_prev = cum_phase_amounts[phase_name][index-1] if (index-1) < len(cum_phase_amounts[phase_name]) else 0
                        phase_amount = phase_amount_curr - phase_amount_prev
                    
                    if phase_amount > 1e-12:
                        phase_amounts_incremental[phase_name] = phase_amount
                        total_solid_incremental += phase_amount
            
            if total_solid_incremental > 0:
                local_comp = {{}}
                independent_elements = ELEMENTAL_SPACE_COMPONENTS[:-1]
                for el in independent_elements:
                    total_weighted_comp = 0
                    
                    for phase_name in phase_amounts_incremental.keys():
                        if phase_name in x_phases:
                            phase_fraction = phase_amounts_incremental[phase_name] / total_solid_incremental
                            
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
                                el_idx = ELEMENTAL_SPACE_COMPONENTS.index(el)
                                total_weighted_comp += phase_fraction * elP_round[el_idx]
                    
                    local_comp[v.X(el.upper())] = total_weighted_comp
                
                total_comp = sum(local_comp.values())
                if 0.01 <= total_comp <= 0.99:
                    local_compositions.append({{
                        'solid_fraction': Sfrac[index],
                        'temperature': scheilT[index],
                        'composition': local_comp,
                        'total_solid': total_solid_incremental,
                        'index': index
                    }})
    
    if not local_compositions:
        fallback_comp = {{}}
        for i, el in enumerate(ELEMENTAL_SPACE_COMPONENTS[:-1]):
            fallback_comp[v.X(el.upper())] = elP_round[i]
        
        local_compositions = [{{
            'solid_fraction': 1.0,
            'temperature': scheilT[-1] if len(scheilT) > 0 else START_TEMP,
            'composition': fallback_comp,
            'total_solid': 1.0,
            'index': len(Sfrac)-1 if len(Sfrac) > 0 else 0
        }}]
    
    # Perform equilibrium calculations at configurable temperature range
    T_eq_array = np.arange(TEMP_MIN, TEMP_MAX + TEMP_STEP, TEMP_STEP)  # Include endpoint
    eq_results = []
    
    for T_eq in T_eq_array:
        phase_fractions_at_T = []
        successful_calcs = 0
        
        for local_data in local_compositions:
            try:
                conds = {{v.T: float(T_eq), v.P: 101325, v.N: 1.0}}
                conds.update(local_data['composition'])
                
                eq = equilibrium(
                    dbf, comps, phases_filtered,
                    conds, model=models, phase_records=phase_records
                )
                
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
        
        if phase_fractions_at_T:
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
            
            total_phase_fraction = sum(integrated_phases.values())
            if total_phase_fraction > 0:
                for phase in integrated_phases:
                    integrated_phases[phase] /= total_phase_fraction
            
            eq_results.append({{
                'Temperature': float(T_eq),
                'PhaseFractions': integrated_phases,
                'SuccessfulCalculations': successful_calcs,
                'TotalLocalCompositions': len(local_compositions)
            }})
    
    return {{
        'scheil_result': scheil_result_serializable,
        'equilibrium_results': eq_results,
        'local_compositions_count': len(local_compositions),
        'temperature_range': (TEMP_MIN, TEMP_MAX, TEMP_STEP)
    }}

if __name__ == "__main__":
    pass