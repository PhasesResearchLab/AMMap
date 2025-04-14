import numpy as np
from scheil import simulate_scheil_solidification
from pycalphad import Database, equilibrium, variables as v
from pycalphad.core.utils import filter_phases, instantiate_models

class HybridCalculator:
    def __init__(self, dbf_path="{dbf_path}", elements={elements}, liquid_phase="{liquid_phase}"):
        self.dbf = Database(dbf_path)
        self.elements = [el.upper() for el in elements]
        self.comps = self.elements + ['VA']
        self.liquid_phase = liquid_phase
        
        # Initialize phase models
        self.phases = list(self.dbf.phases.keys())
        self.filtered_phases = filter_phases(self.dbf, self.comps, self.phases)
        self.models = instantiate_models(self.dbf, self.comps, self.filtered_phases)
        
    def run_scheil(self, composition, start_temp={start_temp}, step_temp={step_temp}):
        """Run Scheil simulation and return structured results"""
        scheil_result = simulate_scheil_solidification(
            self.dbf, self.comps, self.filtered_phases,
            composition, start_temp, step_temp=step_temp
        )
        
        # Extract solidification path data
        solid_path = []
        for idx, temp in enumerate(scheil_result.temperatures):
            if scheil_result.fraction_liquid[idx] < 1.0:
                solid_comp = {
                    el: scheil_result.x_phases[self.liquid_phase][el][idx]
                    for el in self.elements
                }
                solid_path.append({
                    'temp': temp,
                    'solid_fraction': scheil_result.fraction_solid[idx],
                    'composition': solid_comp
                })
                
        return solid_path

    def hybrid_calculation(self, initial_comp, temps=np.arange({temp_min}, {temp_max}, {temp_step})):
        """Main hybrid workflow"""
        # 1. Run Scheil simulation
        solid_path = self.run_scheil(initial_comp)
        
        # 2. Perform equilibrium calculations at each temperature
        eq_results = []
        for T in temps:
            phase_fracs = []
            for step in solid_path:
                # 3. Get local composition from Scheil
                local_comp = step['composition']
                
                # 4. Equilibrium calculation at T
                eq = equilibrium(
                    self.dbf, self.comps, self.filtered_phases,
                    {v.T: T, v.P: 101325, **local_comp},
                    model=self.models
                )
                
                # Store phase fractions
                phase_fracs.append({
                    'temp': T,
                    'solid_frac': step['solid_fraction'],
                    'phases': eq.Phase.values.squeeze(),
                    'amounts': eq.NP.values.squeeze()
                })
            
            # 5. Integrate results across solidification path
            integrated = self._integrate_phase_fractions(phase_fracs)
            eq_results.append(integrated)
            
        return eq_results

    def _integrate_phase_fractions(self, phase_data):
        """Integrate phase amounts using trapezoidal rule"""
        sf = np.array([x['solid_frac'] for x in phase_data])
        amounts = np.array([x['amounts'] for x in phase_data])
        
        # Calculate weighted average
        weights = np.diff(sf, prepend=0)
        weighted_avg = np.sum(amounts * weights[:, None], axis=0)
        return weighted_avg / weighted_avg.sum()
