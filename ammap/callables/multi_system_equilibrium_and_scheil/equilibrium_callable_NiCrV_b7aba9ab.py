from pycalphad import Database, equilibrium, variables as v
from pycalphad.core.utils import instantiate_models, filter_phases, unpack_components
from pycalphad.codegen.callables import build_phase_records
import math

dbf = Database("ammap/databases/Co-Cr-Fe-Ni-V_choi2019.TDB")
T = 1000
elementalSpaceComponents = ['Cr', 'Ni', 'V']

phases = list(set(dbf.phases.keys()))
comps = [s.upper() for s in elementalSpaceComponents]+['VA']
phases_filtered = filter_phases(dbf, unpack_components(dbf, comps), phases)
models = instantiate_models(dbf, comps, phases_filtered)
phase_records = build_phase_records(dbf, comps, phases_filtered, {v.N, v.P, v.T}, models=models)

expected_conds=[v.T]+[v.X(el) for el in comps[:-2]]
default_conds={v.P: 101325, v.N: 1.0}

# Generate feasible phases list
feasible_phases = ['FCC_A1', 'BCC_A2', 'HCP_A3']

def equilibrium_callable(elP):
    elP_round = [round(v-0.000001, 6) if v>0.000001 else 0.0000001 for v in elP]
    conds = {**default_conds, **dict(zip(expected_conds, [T] + elP_round))}
    eq_res = equilibrium(
        dbf, comps, phases_filtered,
        conds, model=models, phase_records=phase_records, calc_opts=dict(pdens=2000))
    
    nPhases = eq_res.Phase.data.shape[-1]
    phaseList = list(eq_res.Phase.data.reshape([nPhases]))
    phasePresentList = [pn for pn in phaseList if pn!='']
    
    if len(phasePresentList)==0:
        pass
    
    pFrac=eq_res.NP.data.shape[-1]
    pFracList=list(eq_res.NP.data.reshape([nPhases]))
    pFracPresent= [pn for pn in pFracList if not math.isnan(pn)]
    
    return{
        'Phases':phasePresentList,
        'PhaseFraction':pFracPresent
    }

if __name__ == "__main__":
    pass