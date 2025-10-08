from pycalphad import Database, equilibrium, variables as v
from pycalphad.core.utils import instantiate_models, filter_phases, unpack_components
from pycalphad.codegen.callables import build_phase_records
import math

dbf = Database("{tdb_file}")
T = {temperature_list}
elementalSpaceComponents = {elements}

phases = list(set(dbf.phases.keys()))
comps = [s.upper() for s in elementalSpaceComponents]+['VA']
phases_filtered = filter_phases(dbf, unpack_components(dbf, comps), phases)
models = instantiate_models(dbf, comps, phases_filtered)
phase_records = build_phase_records(dbf, comps, phases_filtered, {{v.N, v.P, v.T}}, models=models)

expected_conds=[v.T]+[v.X(el) for el in comps[:-2]]
default_conds={{v.P: {pressure}, v.N: 1.0}}

# Generate feasible phases list
feasible_phases = {feasible_phases}

def equilibrium_callable(elP):
    elP_round = [round(v-0.000001, 6) if v>0.000001 else 0.0000001 for v in elP]
    
    # Handle single temperature vs multiple temperatures
    if isinstance(T, list) and len(T) > 1:
        # Multiple temperatures - run separate calculations
        results = []
        for temp in T:
            conds = {{**default_conds, **dict(zip(expected_conds, [temp] + elP_round))}}
            eq_res = equilibrium(
                dbf, comps, phases_filtered,
                conds, model=models, phase_records=phase_records, calc_opts=dict(pdens=5000))
            
            nPhases = eq_res.Phase.data.shape[-1]
            phaseList = list(eq_res.Phase.data.reshape([nPhases]))
            pFracList = list(eq_res.NP.data.reshape([nPhases]))
            
            phasePresentList = [pn for pn in phaseList if pn != '']
            pFracPresent = [pn for pn in pFracList if not math.isnan(pn)]
            
            results.append({{
                'Temperature': temp,
                'Phases': phasePresentList,
                'PhaseFraction': pFracPresent
            }})
        return results
    else:
        # Single temperature - original logic
        temp = T[0] if isinstance(T, list) else T
        conds = {{**default_conds, **dict(zip(expected_conds, [temp] + elP_round))}}
        eq_res = equilibrium(
            dbf, comps, phases_filtered,
            conds, model=models, phase_records=phase_records, calc_opts=dict(pdens=5000))
        
        nPhases = eq_res.Phase.data.shape[-1]
        phaseList = list(eq_res.Phase.data.reshape([nPhases]))
        phasePresentList = [pn for pn in phaseList if pn!='']
        
        if len(phasePresentList)==0:
            pass
        
        pFrac=eq_res.NP.data.shape[-1]
        pFracList=list(eq_res.NP.data.reshape([nPhases]))
        pFracPresent= [pn for pn in pFracList if not math.isnan(pn)]
        
        return{{
            'Phases':phasePresentList,
            'PhaseFraction':pFracPresent
        }}

if __name__ == "__main__":
    pass