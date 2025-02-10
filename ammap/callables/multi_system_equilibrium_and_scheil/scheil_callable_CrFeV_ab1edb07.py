from scheil import simulate_scheil_solidification
from pycalphad import Database, variables as v
from pycalphad.core.utils import instantiate_models, filter_phases, unpack_components
from pycalphad.codegen.callables import build_phase_records
import pandas as pd
import math

dbf = Database("ammap/databases/Co-Cr-Fe-Ni-V_choi2019.TDB")
T = 2500
elementalSpaceComponents = ['Cr', 'Fe', 'V']

phases = list(set(dbf.phases.keys()))
comps = [s.upper() for s in elementalSpaceComponents] + ['VA']
phases_filtered = filter_phases(dbf, unpack_components(dbf, comps), phases)
models = instantiate_models(dbf, comps, phases_filtered)
phase_records = build_phase_records(dbf, comps, phases_filtered, {v.N, v.P, v.T}, models=models)

liquid_phase_name = 'LIQUID'
step_temperature = 1

def scheil_callable(elP):
    elP_round = [round(v-0.000001, 6) if v>0.000001 else 0.0000001 for v in elP]
    initial_composition = dict(zip([v.X(el) for el in comps[:-2]], elP_round))
    
    sol_res = simulate_scheil_solidification(
        dbf, comps, phases_filtered,
        initial_composition, T, step_temperature=step_temperature)

    phaseFractions = {}
    for phase, amounts in sol_res.cum_phase_amounts.items():
        finalAmount = round(amounts[-1], 6)
        if finalAmount > 0:
            phaseFractions[phase] = finalAmount
    
    test = sol_res.cum_phase_amounts
    Lfrac = sol_res.fraction_liquid
    Sfrac = sol_res.fraction_solid
    scheilT = sol_res.temperatures
    solT = scheilT[-1]
    ddict = sol_res.x_phases
    
    keys_to_remove_from_ddict = []
    for ddict_key, dict_value in ddict.items():
        keys_to_remove_from_dict = [key for key, value in dict_value.items() if pd.isna(value).all()]
        for key in keys_to_remove_from_dict:
            del dict_value[key]   
        if not dict_value:
            keys_to_remove_from_ddict.append(ddict_key)
    
    for key in keys_to_remove_from_ddict:
        del ddict[key]
    
    yPhase = sol_res.Y_phases
    liqT = next((temp for temp, frac in zip(scheilT, Lfrac) if frac < 1), scheilT[-1])
    
    return {
        'scheilT': scheilT,
        'finalPhase': phaseFractions,
        'Lfrac': Lfrac,
        'Sfrac': Sfrac,
        'solT': solT,
        'liqT': liqT,
        'phaseFractions': test,
        'xPhase': ddict
    }

if __name__ == "__main__":
    pass