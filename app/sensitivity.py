"""Sensitivity analysis for circuit parameters"""
import math
from typing import Dict


class SensitivityAnalysis:
    """First-order sensitivity analysis for educational insights"""
    
    @staticmethod
    def analyze_rc_filter_sensitivity(
        r_value: float,
        c_value: float,
        fc_nominal: float
    ) -> Dict:
        """Sensitivity of cutoff frequency to R and C variations"""
        
        # For fc = 1/(2πRC), we have:
        # ∂fc/∂R = -1/(2πR²C) = -fc/R
        # ∂fc/∂C = -1/(2πRC²) = -fc/C
        
        # Sensitivity: S_x_y = (∂y/∂x) * (x/y)
        # S_fc_R = -1 (magnitude)
        # S_fc_C = -1 (magnitude)
        
        s_fc_r = -1.0  # 1% change in R → -1% change in fc
        s_fc_c = -1.0  # 1% change in C → -1% change in fc
        
        # Normalized sensitivities (partial derivatives normalized by operating point)
        partial_fc_r = -fc_nominal / r_value
        partial_fc_c = -fc_nominal / c_value
        
        return {
            "circuit_type": "RC Filter",
            "operating_point": {
                "resistor_ohms": r_value,
                "capacitor_farads": c_value,
                "cutoff_frequency_hz": fc_nominal,
                "time_constant_s": r_value * c_value
            },
            "sensitivities": {
                "cutoff_frequency_to_resistor": {
                    "sensitivity_factor": s_fc_r,
                    "interpretation": "1% increase in R → 1% decrease in fc",
                    "partial_derivative": partial_fc_r,
                    "magnitude": abs(s_fc_r)
                },
                "cutoff_frequency_to_capacitor": {
                    "sensitivity_factor": s_fc_c,
                    "interpretation": "1% increase in C → 1% decrease in fc",
                    "partial_derivative": partial_fc_c,
                    "magnitude": abs(s_fc_c)
                }
            }
        }
    
    @staticmethod
    def analyze_opamp_gain_sensitivity(
        rin: float,
        rf: float,
        gain_nominal: float,
        is_non_inverting: bool = True
    ) -> Dict:
        """Sensitivity of op-amp gain to Rf and Rin variations"""
        
        if is_non_inverting:
            # Gain = 1 + Rf/Rin
            # ∂Gain/∂Rf = 1/Rin
            # ∂Gain/∂Rin = -Rf/Rin²
            
            partial_gain_rf = 1 / rin
            partial_gain_rin = -rf / (rin ** 2)
            
            s_gain_rf = partial_gain_rf * (rf / gain_nominal)
            s_gain_rin = partial_gain_rin * (rin / gain_nominal)
            
            circuit_type = "Non-Inverting Op-Amp"
            formula = "Gain = 1 + Rf/Rin"
        else:
            # Gain = -Rf/Rin
            # ∂Gain/∂Rf = -1/Rin
            # ∂Gain/∂Rin = Rf/Rin²
            
            partial_gain_rf = -1 / rin
            partial_gain_rin = rf / (rin ** 2)
            
            s_gain_rf = partial_gain_rf * (rf / gain_nominal)
            s_gain_rin = partial_gain_rin * (rin / gain_nominal)
            
            circuit_type = "Inverting Op-Amp"
            formula = "Gain = -Rf/Rin"
        
        return {
            "circuit_type": circuit_type,
            "formula": formula,
            "operating_point": {
                "rin_ohms": rin,
                "rf_ohms": rf,
                "gain": abs(gain_nominal)
            },
            "sensitivities": {
                "gain_to_rf": {
                    "sensitivity_factor": s_gain_rf,
                    "partial_derivative": partial_gain_rf
                },
                "gain_to_rin": {
                    "sensitivity_factor": s_gain_rin,
                    "partial_derivative": partial_gain_rin
                }
            }
        }
