import numpy as np
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

# Triple braces for Python set literal
phase_records = build_phase_records(
    dbf, comps, phases_filtered,
    {{v.N, v.P, v.T}},  # Escaped set
    models=models
)

liquid_phase_name = '{liquid_phase}'
step_temperature = {step_temp}
temp_min = {temp_min}
temp_max = {temp_max}
temp_step = {temp_step}

def hybrid_scheil_callable(elP):
    elP_round = [round(v - 0.000001, 6) if v > 0.000001 else 0.0000001 for v in elP]
    initial_composition = dict(zip([v.X(el) for el in comps[:-2]], elP_round))

    # Run Scheil simulation
    scheil_result = simulate_scheil_solidification(
        dbf, comps, phases_filtered,
        initial_composition, T, step_temperature=step_temperature
    )

    # Extract solidification path data
    solid_path = []
    for idx, temp in enumerate(scheil_result.temperatures):
        if scheil_result.fraction_liquid[idx] < 1.0:
            # Double braces for dict literal
            solid_comp = {{
                el: scheil_result.x_phases[liquid_phase_name][el][idx]
                for el in elementalSpaceComponents
            }}
            solid_path.append({{
                'temp': temp,
                'solid_fraction': scheil_result.fraction_solid[idx],
                'composition': solid_comp
            }})

    # Perform equilibrium calculations at each temperature
    eq_results = []
    for T_eq in np.arange(temp_min, temp_max, temp_step):
        phase_fracs = []
        for step in solid_path:
            # Get local composition from Scheil
            local_comp = step['composition']
            
            # Triple braces for equilibrium conditions
            eq = equilibrium(
                dbf, comps, phases_filtered,
                {{{{{{v.T: T_eq, v.P: 101325, **local_comp}}}}}},
                model=models
            )

            # Store phase fractions
            phase_fracs.append({{
                'temp': T_eq,
                'solid_frac': step['solid_fraction'],
                'phases': eq.Phase.values.squeeze(),
                'amounts': eq.NP.values.squeeze()
            }})

        # Integrate results across solidification path
        integrated = _integrate_phase_fractions(phase_fracs)
        eq_results.append(integrated)

    return {{
        'scheil_result': scheil_result,
        'equilibrium_results': eq_results
    }}

def _integrate_phase_fractions(phase_data):
    """Integrate phase amounts using trapezoidal rule"""
    sf = np.array([x['solid_frac'] for x in phase_data])
    amounts = np.array([x['amounts'] for x in phase_data])
    weights = np.diff(sf, prepend=0)
    weighted_avg = np.sum(amounts * weights[:, None], axis=0)
    return weighted_avg / weighted_avg.sum()

if __name__ == "__main__":
    pass
