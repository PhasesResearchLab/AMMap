from pycalphad import Database, equilibrium, variables as v
from pycalphad.core.utils import instantiate_models, filter_phases, unpack_components
from pycalphad.codegen.callables import build_phase_records
import numpy as np
import math

dbf = Database("{tdb_file}")

T = np.array({temperature_list}, dtype=float)
elementalSpaceComponents = {elements}

phases = list(set(dbf.phases.keys()))
comps = [s.upper() for s in elementalSpaceComponents] + ['VA']

# Limit phases to feasible_phases if specified
feasible_phases = {feasible_phases}
# Calculate equilibrium for ALL phases (don't filter here)
phases_filtered = [p for p in filter_phases(dbf, unpack_components(dbf, comps), phases)]

models = instantiate_models(dbf, comps, phases_filtered)
phase_records = build_phase_records(dbf, comps, phases_filtered, {{v.N, v.P, v.T}}, models=models)

expected_conds = [v.T] + [v.X(el) for el in comps[:-2]]
default_conds = {{v.P: {pressure}, v.N: 1.0}}

def equilibrium_callable(elP):
    # Vectorized & safe rounding/clipping of compositions
    elP_arr = np.array(elP)
    elP_round = np.clip(np.round(elP_arr - 1e-6, 6), 1e-7, None)

    conds = {{**default_conds, v.T: T}}
    for idx, el in enumerate(comps[:-2]):
        conds[v.X(el)] = float(elP_round[idx])

    eq_res = equilibrium(
        dbf, comps, phases_filtered,
        conds, model=models, phase_records=phase_records,
        calc_opts=dict(pdens=200)
    )

    n_temps = len(T)
    output = []

    # Handle the case where eq_res has shape (1, 1, n_temps, ...)
    # We need to access the temperature dimension correctly
    if eq_res.Phase.data.shape[0] == 1:
        # Single composition result, temperatures are in dimension 2
        for i in range(n_temps):
            try:
                # Access temperature data correctly: [0, 0, i, ...]
                phase_data = eq_res.Phase.data[0, 0, i].flatten()
                np_data = eq_res.NP.data[0, 0, i].flatten()
                phasePresentList = [str(pn) for pn in phase_data if pn != '']
                pFracPresent = [float(pn) for pn in np_data if not math.isnan(pn)]
                output.append({{
                    'Temperature': float(T[i]),
                    'Phases': phasePresentList,
                    'PhaseFraction': pFracPresent
                }})
            except IndexError:
                # Skip temperatures that don't have results
                continue
    else:
        # Original code for when we have multiple composition results
        for i in range(min(n_temps, eq_res.Phase.data.shape[0])):
            try:
                phase_data = eq_res.Phase.data[i].flatten()
                np_data = eq_res.NP.data[i].flatten()
                phasePresentList = [str(pn) for pn in phase_data if pn != '']
                pFracPresent = [float(pn) for pn in np_data if not math.isnan(pn)]
                output.append({{
                    'Temperature': float(T[i]),
                    'Phases': phasePresentList,
                    'PhaseFraction': pFracPresent
                }})
            except IndexError:
                continue
    
    return output

if __name__ == "__main__":
    # Test example (remove or comment for production)
    # print(equilibrium_callable([0.25, 0.25, 0.25, 0.25]))
    pass