"""Worst-case analysis with corner variations"""
import math
from typing import Any, Dict, Optional


class WorstCaseAnalysis:
    """Deterministic worst-case corner analysis"""
    
    @staticmethod
    def _rc_lowpass_magnitude_response(frequency: float, fc: float) -> float:
        """Calculate magnitude response |H(jω)| for RC low-pass filter at given frequency.
        |H(jω)| = 1 / √(1 + (f/fc)²)
        """
        if frequency <= 0:
            return 1.0  # DC gain = 1
        ratio = frequency / fc if fc > 0 else 0
        return 1.0 / math.sqrt(1 + ratio**2)
    
    @staticmethod
    def _rc_highpass_magnitude_response(frequency: float, fc: float) -> float:
        """Calculate magnitude response |H(jω)| for RC high-pass filter at given frequency.
        |H(jω)| = (f/fc) / √(1 + (f/fc)²)
        """
        if frequency <= 0:
            return 0.0  # DC is blocked
        ratio = frequency / fc if fc > 0 else float('inf')
        return ratio / math.sqrt(1 + ratio**2)
    
    @staticmethod
    def _calculate_frequency_response_output(
        test_frequency: Optional[float],
        fc_nominal: float,
        fc_min: float,
        fc_max: float,
        vin_nominal: float,
        vin_min: float,
        vin_max: float,
        filter_type: str
    ) -> Optional[Dict]:
        """Calculate output voltage at given frequency across all component corner cases."""
        if not test_frequency or test_frequency <= 0:
            return None
        
        results = {
            "test_frequency": test_frequency,
            "filter_type": filter_type,
            "magnitude_response_corners": {}
        }
        
        if filter_type == "low_pass":
            mag_nominal = WorstCaseAnalysis._rc_lowpass_magnitude_response(test_frequency, fc_nominal)
            mag_at_fc_min = WorstCaseAnalysis._rc_lowpass_magnitude_response(test_frequency, fc_min)
            mag_at_fc_max = WorstCaseAnalysis._rc_lowpass_magnitude_response(test_frequency, fc_max)
        else:  # high_pass
            mag_nominal = WorstCaseAnalysis._rc_highpass_magnitude_response(test_frequency, fc_nominal)
            mag_at_fc_min = WorstCaseAnalysis._rc_highpass_magnitude_response(test_frequency, fc_min)
            mag_at_fc_max = WorstCaseAnalysis._rc_highpass_magnitude_response(test_frequency, fc_max)
        
        # Calculate output voltage at each corner
        vout_nominal = mag_nominal * vin_nominal
        vout_at_fc_min_vin_max = mag_at_fc_min * vin_max
        vout_at_fc_min_vin_min = mag_at_fc_min * vin_min
        vout_at_fc_max_vin_max = mag_at_fc_max * vin_max
        vout_at_fc_max_vin_min = mag_at_fc_max * vin_min
        
        all_vouts = [vout_at_fc_min_vin_max, vout_at_fc_min_vin_min, 
                     vout_at_fc_max_vin_max, vout_at_fc_max_vin_min]
        
        results.update({
            "magnitude_response_corners": {
                "at_fc_min": {"magnitude": mag_at_fc_min, "description": f"|H| at fc_min = {mag_at_fc_min:.4f}"},
                "at_fc_nominal": {"magnitude": mag_nominal, "description": f"|H| at fc_nominal = {mag_nominal:.4f}"},
                "at_fc_max": {"magnitude": mag_at_fc_max, "description": f"|H| at fc_max = {mag_at_fc_max:.4f}"}
            },
            "nominal_output": {
                "magnitude": mag_nominal,
                "voltage": vout_nominal,
                "equation": f"|H(j{test_frequency})| × V_in = {mag_nominal:.4f} × {vin_nominal:.3f}V = {vout_nominal:.4f}V"
            },
            "worst_case_output": {
                "minimum": min(all_vouts),
                "maximum": max(all_vouts),
                "min_corner": f"Occurs at: fc={'fc_min' if abs(vout_at_fc_min_vin_min - min(all_vouts)) < 1e-6 else 'fc_max'}, V_in={'min' if 'vin_min' in str(locals()) else 'max'}",
                "max_corner": f"Occurs at: fc={'fc_max' if abs(vout_at_fc_max_vin_max - max(all_vouts)) < 1e-6 else 'fc_min'}, V_in={'max' if 'vin_max' in str(locals()) else 'min'}",
                "all_corners": {
                    "fc_min_vin_max": vout_at_fc_min_vin_max,
                    "fc_min_vin_min": vout_at_fc_min_vin_min,
                    "fc_max_vin_max": vout_at_fc_max_vin_max,
                    "fc_max_vin_min": vout_at_fc_max_vin_min
                }
            }
        })
        
        return results
    
    @staticmethod
    def analyze_rc_low_pass(
        r_nominal: float,
        c_nominal: float,
        vin_nominal: float,
        r1_tolerance: float,
        capacitor_tolerance: float,
        line_fluctuation: float,
        voltage_type: str = "DC",
        test_frequency: float = None
    ) -> Dict:
        """Worst-case analysis for RC low-pass filter"""
        tol_r = r1_tolerance / 100.0
        tol_c = capacitor_tolerance / 100.0
        tol_vin = line_fluctuation / 100.0
        
        # Calculate extreme values
        r_min = r_nominal * (1 - tol_r)
        r_max = r_nominal * (1 + tol_r)
        c_min = c_nominal * (1 - tol_c)
        c_max = c_nominal * (1 + tol_c)
        vin_min = vin_nominal * (1 - tol_vin)
        vin_max = vin_nominal * (1 + tol_vin)
        
        # fc = 1/(2πRC), so fc is minimized when R and C are maximized, and vice versa
        fc_min = 1 / (2 * math.pi * r_max * c_max)
        fc_max = 1 / (2 * math.pi * r_min * c_min)
        
        # Time constant τ = RC
        tau_min = r_min * c_min
        tau_max = r_max * c_max
        
        # Calculate output voltage at cutoff frequency (nominal fc)
        fc_nominal = 1 / (2 * math.pi * r_nominal * c_nominal)
        test_freq = test_frequency if test_frequency else fc_nominal
        
        # Magnitude response at each corner
        mag_nominal = WorstCaseAnalysis._rc_lowpass_magnitude_response(test_freq, fc_nominal)
        mag_at_fc_min = WorstCaseAnalysis._rc_lowpass_magnitude_response(test_freq, fc_min)
        mag_at_fc_max = WorstCaseAnalysis._rc_lowpass_magnitude_response(test_freq, fc_max)
        
        # Four corner cases for output voltage
        vout_1 = mag_at_fc_min * vin_max  # Highest attenuation + max input
        vout_2 = mag_at_fc_min * vin_min  # Highest attenuation + min input
        vout_3 = mag_at_fc_max * vin_max  # Lowest attenuation + max input
        vout_4 = mag_at_fc_max * vin_min  # Lowest attenuation + min input
        
        vout_min = min(vout_1, vout_2, vout_3, vout_4)
        vout_max = max(vout_1, vout_2, vout_3, vout_4)
        vout_nominal = mag_nominal * vin_nominal
        vout_abs_min = min(abs(vout_1), abs(vout_2), abs(vout_3), abs(vout_4))
        vout_abs_max = max(abs(vout_1), abs(vout_2), abs(vout_3), abs(vout_4))
        
        return {
            "resistor": {
                "nominal": r_nominal,
                "minimum": r_min,
                "maximum": r_max,
                "r1_tolerance_percent": r1_tolerance,
                "absolute_min": min(abs(r_min), abs(r_max)),
                "absolute_max": max(abs(r_min), abs(r_max))
            },
            "capacitor": {
                "nominal": c_nominal,
                "minimum": c_min,
                "maximum": c_max,
                "tolerance_percent": capacitor_tolerance,
                "absolute_min": min(abs(c_min), abs(c_max)),
                "absolute_max": max(abs(c_min), abs(c_max))
            },
            "input_voltage": {
                "nominal": vin_nominal,
                "minimum": vin_min,
                "maximum": vin_max,
                "tolerance_percent": line_fluctuation,
                "voltage_type": voltage_type
            },
            "cutoff_frequency": {
                "nominal": 1 / (2 * math.pi * r_nominal * c_nominal),
                "minimum": fc_min,
                "maximum": fc_max,
                "absolute_min": min(abs(fc_min), abs(fc_max)),
                "absolute_max": max(abs(fc_min), abs(fc_max))
            },
            "time_constant": {
                "nominal": r_nominal * c_nominal,
                "minimum": tau_min,
                "maximum": tau_max,
                "absolute_min": min(abs(tau_min), abs(tau_max)),
                "absolute_max": max(abs(tau_min), abs(tau_max))
            },
            "output_voltage": {
                "nominal": vout_nominal,
                "minimum": vout_min,
                "maximum": vout_max,
                "absolute_min": vout_abs_min,
                "absolute_max": vout_abs_max,
                "voltage_type": voltage_type,
                "test_frequency": test_freq,
                "explanation": f"Output voltage at f={test_freq:.1f}Hz: V_out = |H(jf)| × V_in, accounting for R,C tolerance effects on fc"
            },
            "frequency_response_output": WorstCaseAnalysis._calculate_frequency_response_output(
                test_frequency,
                1 / (2 * math.pi * r_nominal * c_nominal),
                fc_min,
                fc_max,
                vin_nominal,
                vin_min,
                vin_max,
                "low_pass"
            ) if test_frequency else None,
            "derivation": [
                f"Transfer Function: H(s) = 1 / (1 + sRC)",
                f"Magnitude Response: |H(jω)| = 1 / √(1 + (f/fc)²)",
                f"Output at frequency f: V_out(f) = |H(jf)| × V_in",
                f"Worst-case considers: V_in variation (min/max) × |H(jf)| at each corner fc",
                f"fc varies from {fc_min:.2f}Hz (R_max,C_max) to {fc_max:.2f}Hz (R_min,C_min)"
            ]
        }
    
    @staticmethod
    def analyze_rc_high_pass(
        r_nominal: float,
        c_nominal: float,
        vin_nominal: float,
        r1_tolerance: float,
        capacitor_tolerance: float,
        line_fluctuation: float,
        voltage_type: str = "DC",
        test_frequency: float = None
    ) -> Dict:
        """Worst-case analysis for RC high-pass filter"""
        
        tol_r = r1_tolerance / 100.0
        tol_c = capacitor_tolerance / 100.0
        tol_vin = line_fluctuation / 100.0
        
        r_min = r_nominal * (1 - tol_r)
        r_max = r_nominal * (1 + tol_r)
        c_min = c_nominal * (1 - tol_c)
        c_max = c_nominal * (1 + tol_c)
        vin_min = vin_nominal * (1 - tol_vin)
        vin_max = vin_nominal * (1 + tol_vin)
        
        fc_min = 1 / (2 * math.pi * r_max * c_max)
        fc_max = 1 / (2 * math.pi * r_min * c_min)
        
        # Calculate output voltage at cutoff frequency (nominal fc)
        fc_nominal = 1 / (2 * math.pi * r_nominal * c_nominal)
        test_freq = test_frequency if test_frequency else fc_nominal
        
        # Magnitude response at each corner
        mag_nominal = WorstCaseAnalysis._rc_highpass_magnitude_response(test_freq, fc_nominal)
        mag_at_fc_min = WorstCaseAnalysis._rc_highpass_magnitude_response(test_freq, fc_min)
        mag_at_fc_max = WorstCaseAnalysis._rc_highpass_magnitude_response(test_freq, fc_max)
        
        # Four corner cases for output voltage
        vout_1 = mag_at_fc_min * vin_max  # Highest attenuation + max input
        vout_2 = mag_at_fc_min * vin_min  # Highest attenuation + min input
        vout_3 = mag_at_fc_max * vin_max  # Lowest attenuation + max input
        vout_4 = mag_at_fc_max * vin_min  # Lowest attenuation + min input
        
        vout_min = min(vout_1, vout_2, vout_3, vout_4)
        vout_max = max(vout_1, vout_2, vout_3, vout_4)
        vout_nominal = mag_nominal * vin_nominal
        vout_abs_min = min(abs(vout_1), abs(vout_2), abs(vout_3), abs(vout_4))
        vout_abs_max = max(abs(vout_1), abs(vout_2), abs(vout_3), abs(vout_4))
        
        # Time constant τ = RC
        tau_min = r_min * c_min
        tau_max = r_max * c_max
        
        return {
            "resistor": {
                "nominal": r_nominal,
                "minimum": r_min,
                "maximum": r_max,
                "r1_tolerance_percent": r1_tolerance,
                "absolute_min": min(abs(r_min), abs(r_max)),
                "absolute_max": max(abs(r_min), abs(r_max))
            },
            "capacitor": {
                "nominal": c_nominal,
                "minimum": c_min,
                "maximum": c_max,
                "tolerance_percent": capacitor_tolerance,
                "absolute_min": min(abs(c_min), abs(c_max)),
                "absolute_max": max(abs(c_min), abs(c_max))
            },
            "input_voltage": {
                "nominal": vin_nominal,
                "minimum": vin_min,
                "maximum": vin_max,
                "tolerance_percent": line_fluctuation,
                "explanation": "Input voltage variation directly affects steady-state output."
            },
            "cutoff_frequency": {
                "nominal": 1 / (2 * math.pi * r_nominal * c_nominal),
                "minimum": fc_min,
                "maximum": fc_max,
                "absolute_min": min(abs(fc_min), abs(fc_max)),
                "absolute_max": max(abs(fc_min), abs(fc_max)),
                "voltage_type": voltage_type,
                "explanation": "Cutoff frequency fc = 1/(2πRC). Inverse relationship: smallest R,C give highest fc; largest R,C give lowest fc."
            },
            "time_constant": {
                "nominal": r_nominal * c_nominal,
                "minimum": tau_min,
                "maximum": tau_max,
                "absolute_min": min(abs(tau_min), abs(tau_max)),
                "absolute_max": max(abs(tau_min), abs(tau_max)),
                "explanation": "Time constant τ = RC determines settling time. Larger τ means slower rise time."
            },
            "output_voltage": {
                "nominal": vout_nominal,
                "minimum": vout_min,
                "maximum": vout_max,
                "absolute_min": vout_abs_min,
                "absolute_max": vout_abs_max,
                "voltage_type": voltage_type,
                "test_frequency": test_freq,
                "explanation": f"Output voltage at f={test_freq:.1f}Hz: V_out = |H(jf)| × V_in, accounting for R,C tolerance effects on fc"
            }
        }
    
    @staticmethod
    def analyze_rc_charging(
        r_nominal: float,
        c_nominal: float,
        vin_nominal: float,
        r1_tolerance: float,
        capacitor_tolerance: float,
        line_fluctuation: float,
        time_value: float = 1.0,
        voltage_type: str = "DC"
    ) -> Dict:
        """Worst-case analysis for RC charging circuit"""
        
        tol_r = r1_tolerance / 100.0
        tol_c = capacitor_tolerance / 100.0
        tol_vin = line_fluctuation / 100.0
        
        r_min = r_nominal * (1 - tol_r)
        r_max = r_nominal * (1 + tol_r)
        c_min = c_nominal * (1 - tol_c)
        c_max = c_nominal * (1 + tol_c)
        vin_min = vin_nominal * (1 - tol_vin)
        vin_max = vin_nominal * (1 + tol_vin)
        
        tau_max = r_max * c_max
        tau_min = r_min * c_min

        # V_c(t) = V_in * (1 - exp(-t/τ))
        vc_fastest = vin_max * (1 - math.exp(-time_value / tau_min))
        vc_slowest = vin_min * (1 - math.exp(-time_value / tau_max))

        return {
            "voltage_type": voltage_type,
            "resistor": {
                "nominal": r_nominal,
                "minimum": r_min,
                "maximum": r_max,
                "tolerance_percent": tol_r * 100,
                "absolute_min": min(abs(r_min), abs(r_max)),
                "absolute_max": max(abs(r_min), abs(r_max))
            },
            "capacitor": {
                "nominal": c_nominal,
                "minimum": c_min,
                "maximum": c_max,
                "tolerance_percent": tol_c * 100,
                "absolute_min": min(abs(c_min), abs(c_max)),
                "absolute_max": max(abs(c_min), abs(c_max))
            },
            "input_voltage": {
                "nominal": vin_nominal,
                "minimum": vin_min,
                "maximum": vin_max,
                "tolerance_percent": tol_vin * 100,
                "explanation": "Input voltage affects final charging voltage. Final voltage at t→∞ approaches V_in."
            },
            "time_constant": {
                "nominal": r_nominal * c_nominal,
                "minimum": tau_min,
                "maximum": tau_max,
                "absolute_min": min(abs(tau_min), abs(tau_max)),
                "absolute_max": max(abs(tau_min), abs(tau_max)),
                "explanation": "τ = RC controls charging speed. Smaller τ = faster charging. τ_min = R_min × C_min (fastest). τ_max = R_max × C_max (slowest)."
            },
            "capacitor_voltage_at_time": {
                "nominal": vin_nominal * (1 - math.exp(-time_value / (r_nominal * c_nominal))),
                "fastest_charging": vc_fastest,
                "slowest_charging": vc_slowest,
                "absolute_min": min(abs(vc_fastest), abs(vc_slowest)),
                "absolute_max": max(abs(vc_fastest), abs(vc_slowest)),
                "equation_general": "V_C(t) = V_in × (1 - exp(-t/τ))",
                "equation_fastest": f"V_C_fastest = V_in_max × (1 - exp(-{time_value}s / τ_min)) = {vin_max:.3f}V × (1 - exp(-{time_value}s / {tau_min:.6f}s)) = {vc_fastest:.4f}V",
                "equation_slowest": f"V_C_slowest = V_in_min × (1 - exp(-{time_value}s / τ_max)) = {vin_min:.3f}V × (1 - exp(-{time_value}s / {tau_max:.6f}s)) = {vc_slowest:.4f}V",
                "explanation": "Fastest charging uses maximum input voltage and minimum time constant. Slowest uses minimum input voltage and maximum time constant. At steady-state (t→∞), both approach their respective input voltages."
            }
        }
    
    @staticmethod
    def analyze_opamp_gain(
        circuit_type: str,
        gain_nominal: float,
        vin_nominal: float,
        r1_tolerance: float,
        r2_tolerance: Optional[float],
        capacitor_tolerance: float,
        line_fluctuation: float,
        resistor_ohms: Optional[float] = None,
        resistor_ohms_2: Optional[float] = None,
        capacitor_farads: Optional[float] = None,
        cutoff_frequency: Optional[float] = None
    ) -> Dict:
        """Worst-case analysis for op-amp gain"""
        circuit_name = circuit_type.value if hasattr(circuit_type, "value") else str(circuit_type)
        tol_r1 = r1_tolerance / 100.0
        tol_r2 = (r2_tolerance if r2_tolerance is not None else r1_tolerance) / 100.0
        tol_c = capacitor_tolerance / 100.0
        tol_vin = line_fluctuation / 100.0

        r1_nominal = resistor_ohms if resistor_ohms and resistor_ohms > 0 else 1000.0
        if resistor_ohms_2 and resistor_ohms_2 > 0:
            r2_nominal = resistor_ohms_2
        else:
            if circuit_name == "INVERTING_OPAMP":
                r2_nominal = abs(gain_nominal) * r1_nominal
            else:
                r2_nominal = max((abs(gain_nominal) - 1.0) * r1_nominal, 1.0)

        r1_min = r1_nominal * (1 - tol_r1)
        r1_max = r1_nominal * (1 + tol_r1)
        r2_min = r2_nominal * (1 - tol_r2)
        r2_max = r2_nominal * (1 + tol_r2)

        c_nominal = capacitor_farads if capacitor_farads and capacitor_farads > 0 else 1e-6
        c_min = c_nominal * (1 - tol_c)
        c_max = c_nominal * (1 + tol_c)

        is_active_filter = circuit_name == "ACTIVE_OPAMP_FILTER"

        if circuit_name == "INVERTING_OPAMP":
            nominal_gain = -(r2_nominal / r1_nominal)
            gain_min = -(r2_max / r1_min)  # most negative
            gain_max = -(r2_min / r1_max)  # least negative
        else:
            nominal_gain = 1 + (r2_nominal / r1_nominal)
            gain_min = 1 + (r2_min / r1_max)
            gain_max = 1 + (r2_max / r1_min)
        
        vin_min = vin_nominal * (1 - tol_vin)
        vin_max = vin_nominal * (1 + tol_vin)
        
        # Output voltage = Gain × Vin (evaluate corners)
        vout_candidates = [
            gain_min * vin_min,
            gain_min * vin_max,
            gain_max * vin_min,
            gain_max * vin_max,
        ]
        vout_min = min(vout_candidates)
        vout_max = max(vout_candidates)

        result: Dict[str, Any] = {
            "r1_tolerance_percent": r1_tolerance,
            "r2_tolerance_percent": r2_tolerance if r2_tolerance is not None else r1_tolerance,
            "capacitor_tolerance_percent": capacitor_tolerance,
            "line_fluctuation_percent": line_fluctuation,
            "resistor": {
                "nominal": r1_nominal,
                "minimum": r1_min,
                "maximum": r1_max,
                "absolute_min": min(abs(r1_min), abs(r1_max)),
                "absolute_max": max(abs(r1_min), abs(r1_max))
            },
            "resistor_2": {
                "nominal": r2_nominal,
                "minimum": r2_min,
                "maximum": r2_max,
                "absolute_min": min(abs(r2_min), abs(r2_max)),
                "absolute_max": max(abs(r2_min), abs(r2_max))
            },
            "capacitor": {
                "nominal": c_nominal,
                "minimum": c_min,
                "maximum": c_max,
                "absolute_min": min(abs(c_min), abs(c_max)),
                "absolute_max": max(abs(c_min), abs(c_max))
            },
            "input_voltage": {
                "nominal": vin_nominal,
                "minimum": vin_min,
                "maximum": vin_max
            },
            "gain": {
                "nominal": nominal_gain,
                "minimum": gain_min,
                "maximum": gain_max,
                "absolute_min": min(abs(gain_min), abs(gain_max)),
                "absolute_max": max(abs(gain_min), abs(gain_max))
            }
        }

        if is_active_filter:
            fc_nominal = 1 / (2 * math.pi * r2_nominal * c_nominal)
            fc_min = 1 / (2 * math.pi * r2_max * c_max)
            fc_max = 1 / (2 * math.pi * r2_min * c_min)
            tau_nominal = r2_nominal * c_nominal
            tau_min = r2_min * c_min
            tau_max = r2_max * c_max
            test_freq = cutoff_frequency if cutoff_frequency and cutoff_frequency > 0 else fc_nominal

            mag_fc_min = WorstCaseAnalysis._rc_lowpass_magnitude_response(test_freq, fc_min)
            mag_fc_max = WorstCaseAnalysis._rc_lowpass_magnitude_response(test_freq, fc_max)
            mag_nominal = WorstCaseAnalysis._rc_lowpass_magnitude_response(test_freq, fc_nominal)

            vout_candidates = [
                gain_min * mag_fc_min * vin_min,
                gain_min * mag_fc_min * vin_max,
                gain_max * mag_fc_max * vin_min,
                gain_max * mag_fc_max * vin_max,
                gain_min * mag_fc_max * vin_min,
                gain_min * mag_fc_max * vin_max,
                gain_max * mag_fc_min * vin_min,
                gain_max * mag_fc_min * vin_max,
            ]

            result["cutoff_frequency"] = {
                "nominal": fc_nominal,
                "minimum": fc_min,
                "maximum": fc_max,
                "absolute_min": min(abs(fc_min), abs(fc_max)),
                "absolute_max": max(abs(fc_min), abs(fc_max))
            }
            result["time_constant"] = {
                "nominal": tau_nominal,
                "minimum": tau_min,
                "maximum": tau_max,
                "absolute_min": min(abs(tau_min), abs(tau_max)),
                "absolute_max": max(abs(tau_min), abs(tau_max))
            }
            result["output_voltage"] = {
                "nominal": nominal_gain * mag_nominal * vin_nominal,
                "minimum": min(vout_candidates),
                "maximum": max(vout_candidates),
                "absolute_min": min(abs(v) for v in vout_candidates),
                "absolute_max": max(abs(v) for v in vout_candidates),
                "test_frequency": test_freq,
                "explanation": f"Active LPF output at f={test_freq:.2f}Hz uses Gain × |H(jf)| × Vin with fc = 1/(2πR2C)."
            }
            return result
        
        result["output_voltage"] = {
            "nominal": nominal_gain * vin_nominal,
            "minimum": vout_min,
            "maximum": vout_max,
            "absolute_min": min(abs(vout_min), abs(vout_max)),
            "absolute_max": max(abs(vout_min), abs(vout_max))
        }
        return result
    @staticmethod
    def analyze_linear_regulator_with_bridge_rectifier(
        input_ac_nominal: float,
        filter_capacitor_nominal: float,
        series_resistor_nominal: float,
        load_current_nominal: float,
        output_voltage_target: float,
        input_voltage_tolerance: float,
        capacitor_tolerance: float,
        resistor_tolerance: float,
        load_current_tolerance: float
    ) -> Dict:
        """
        Worst-case analysis for linear regulator with full bridge rectifier.
        Analyzes output voltage stability across all component corner cases.
        """
        # Convert percentages to multipliers
        tol_vin = input_voltage_tolerance / 100.0
        tol_c = capacitor_tolerance / 100.0
        tol_r = resistor_tolerance / 100.0
        tol_iload = load_current_tolerance / 100.0
        
        # Calculate corner values
        vin_nominal = input_ac_nominal
        vin_min = input_ac_nominal * (1 - tol_vin)
        vin_max = input_ac_nominal * (1 + tol_vin)
        
        c_nominal = filter_capacitor_nominal
        c_min = filter_capacitor_nominal * (1 - tol_c)
        c_max = filter_capacitor_nominal * (1 + tol_c)
        
        # External series resistor is not used in the standard linear-regulator path.
        r_nominal = 0.0
        r_min = 0.0
        r_max = 0.0
        
        iload_nominal = load_current_nominal
        iload_min = load_current_nominal * (1 - tol_iload)
        iload_max = load_current_nominal * (1 + tol_iload)
        
        # Rectifier parameters
        diode_forward_voltage = 0.7  # Volts
        regulator_dropout = 0.2  # Volts (typical for LM78xx)
        rectifier_frequency = 120  # Hz (full-wave @ 60Hz)
        
        # Calculate peak voltages
        v_peak_nominal = vin_nominal * math.sqrt(2) - 2 * diode_forward_voltage
        v_peak_min = vin_min * math.sqrt(2) - 2 * diode_forward_voltage
        v_peak_max = vin_max * math.sqrt(2) - 2 * diode_forward_voltage
        
        # Calculate ripple voltages (V_ripple = I_load / (f * C))
        v_ripple_nominal = iload_nominal / (rectifier_frequency * c_nominal)
        
        # Worst case ripple: max current and min capacitance
        v_ripple_max = iload_max / (rectifier_frequency * c_min)
        
        # Worst case ripple: min current and max capacitance
        v_ripple_min = iload_min / (rectifier_frequency * c_max)
        
        # Filtered DC voltage (assuming simple RC filter: V_filtered = V_peak - V_ripple/2)
        v_filtered_nominal = v_peak_nominal - v_ripple_nominal / 2
        
        # Worst case scenarios for filtered voltage
        v_filtered_max = v_peak_max - v_ripple_min / 2  # Max peak - min ripple
        v_filtered_min = v_peak_min - v_ripple_max / 2  # Min peak - max ripple
        
        # Voltage drop across an external series resistor is not part of the
        # standard linear-regulator power path.
        v_drop_nominal = 0.0
        v_drop_max = 0.0
        v_drop_min = 0.0
        
        # Output voltage calculation
        # V_out = V_filtered - V_drop_resistor - V_dropout_regulator
        
        # Nominal output
        vout_nominal = min(output_voltage_target, max(v_filtered_nominal - regulator_dropout, 0))

        # Worst case maximum output: Max filtered - dropout
        vout_max = min(output_voltage_target, max(v_filtered_max - regulator_dropout, 0))

        # Worst case minimum output: Min filtered - dropout
        vout_min = min(output_voltage_target, max(v_filtered_min - regulator_dropout, 0))

        # Regulator dissipation estimate
        power_nominal = max(v_filtered_nominal - vout_nominal, 0) * iload_nominal
        power_max = max(v_filtered_max - vout_min, 0) * iload_max
        
        # Analysis summary
        analysis_data = {
            "input_ac_voltage": {
                "nominal": vin_nominal,
                "minimum": vin_min,
                "maximum": vin_max,
                "tolerance_percent": input_voltage_tolerance
            },
            "peak_voltage_after_rectifier": {
                "nominal": v_peak_nominal,
                "minimum": v_peak_min,
                "maximum": v_peak_max,
                "description": "V_peak = V_ac × √2 - 2 × V_diode"
            },
            "filter_capacitor": {
                "nominal": c_nominal * 1e6,
                "minimum": c_min * 1e6,
                "maximum": c_max * 1e6,
                "unit": "µF",
                "tolerance_percent": capacitor_tolerance
            },
            "ripple_voltage": {
                "nominal": v_ripple_nominal,
                "minimum": v_ripple_min,
                "maximum": v_ripple_max,
                "description": "V_ripple = I_load / (f_rect × C)"
            },
            "filtered_dc_voltage": {
                "nominal": v_filtered_nominal,
                "minimum": v_filtered_min,
                "maximum": v_filtered_max,
                "description": "V_filtered ≈ V_peak - V_ripple/2"
            },
            "series_resistor": {
                "nominal": r_nominal,
                "minimum": r_min,
                "maximum": r_max,
                "unit": "Ω",
                "tolerance_percent": resistor_tolerance
            },
            "load_current": {
                "nominal": iload_nominal,
                "minimum": iload_min,
                "maximum": iload_max,
                "unit": "A",
                "tolerance_percent": load_current_tolerance
            },
            "voltage_drop_resistor": {
                "nominal": v_drop_nominal,
                "minimum": v_drop_min,
                "maximum": v_drop_max,
                "description": "V_drop = I_load × R"
            },
            "regulator_dropout_voltage": {
                "value": regulator_dropout,
                "description": "Typical for LM78xx linear regulator ICs"
            },
            "output_voltage": {
                "nominal": vout_nominal,
                "minimum": vout_min,
                "maximum": vout_max,
                "target": output_voltage_target,
                "variation_percent": (((vout_max - vout_min) / output_voltage_target) * 100) if output_voltage_target > 0 else 0,
                "description": "V_out = min(V_target, V_filtered - V_dropout)"
            },
            "power_dissipation_resistor": {
                "nominal": power_nominal,
                "maximum": power_max,
                "unit": "W",
                "description": "Regulator dissipation estimate: P ≈ (V_in - V_out) × I_load"
            },
            "worst_case_scenarios": {
                "max_output_voltage": {
                    "value": vout_max,
                    "conditions": "V_ac_max, C_max, I_load_min",
                    "explanation": "Maximum input and largest capacitor yield the highest regulated headroom"
                },
                "min_output_voltage": {
                    "value": vout_min,
                    "conditions": "V_ac_min, C_min, I_load_max",
                    "explanation": "Minimum input and smallest capacitor yield the lowest available headroom"
                },
                "max_power_dissipation": {
                    "value": power_max,
                    "conditions": "V_ac_max, C_min, I_load_max",
                    "explanation": "Highest input headroom and load current produce maximum regulator heating"
                }
            }
        }
        
        summary = (
            f"Linear Regulator with Full Bridge Rectifier - Worst-Case Analysis\n"
            f"Output Voltage: {vout_nominal:.3f}V (nominal) | "
            f"{vout_min:.3f}V - {vout_max:.3f}V (worst-case range)\n"
            f"Variation: ±{(vout_max - vout_nominal):.3f}V / ±{(vout_nominal - vout_min):.3f}V\n"
            f"Regulator Dissipation: {power_nominal:.2f}W (nominal) | {power_max:.2f}W (max)\n"
            f"Ripple Voltage: {v_ripple_nominal:.3f}V (nominal) | "
            f"{v_ripple_min:.3f}V - {v_ripple_max:.3f}V (range)"
        )
        
        return {
            "circuit_type": "LINEAR_REGULATOR_WITH_BRIDGE_RECTIFIER",
            "analysis_data": analysis_data,
            "summary": summary
        }
    
    @staticmethod
    def analyze_zener_regulator_with_bridge_rectifier(
        input_ac_voltage: float,
        output_voltage: float,
        load_resistance: float,
        series_resistor: float,
        zener_voltage: float,
        filter_capacitor: float,
        ac_tolerance: float = 5.0,
        resistor_tolerance: float = 5.0,
        capacitor_tolerance: float = 10.0,
        load_tolerance: float = 10.0,
        line_frequency_hz: float = 60.0,
        diode_forward_voltage: float = 0.7
    ) -> Dict:
        """Worst-case corner analysis for zener shunt regulator"""
        
        rectifier_frequency = line_frequency_hz * 2
        ripple_nominal = 0.5
        
        # Corner values
        vin_max = input_ac_voltage * (1 + ac_tolerance / 100)
        vin_min = input_ac_voltage * (1 - ac_tolerance / 100)
        
        rs_max = series_resistor * (1 + resistor_tolerance / 100)
        rs_min = series_resistor * (1 - resistor_tolerance / 100)
        
        c_max = filter_capacitor * (1 + capacitor_tolerance / 100)
        c_min = filter_capacitor * (1 - capacitor_tolerance / 100)
        
        r_load_max = load_resistance * (1 + load_tolerance / 100)
        r_load_min = load_resistance * (1 - load_tolerance / 100)
        
        # Helper function for calculations
        def calculate_point(vin, rs, c, r_load):
            v_peak = vin * math.sqrt(2) - 2 * diode_forward_voltage
            i_load = output_voltage / r_load
            ripple = i_load / (rectifier_frequency * c)
            v_filtered = v_peak - ripple / 2
            i_supply = (v_filtered - zener_voltage) / rs
            i_zener = max(i_supply - i_load, 0)
            v_out = zener_voltage
            p_zener = zener_voltage * i_zener
            p_series = (i_supply ** 2) * rs
            return {
                "v_peak": v_peak,
                "v_ripple": ripple,
                "v_filtered": v_filtered,
                "v_out": v_out,
                "i_load": i_load,
                "i_zener": i_zener,
                "i_supply": i_supply,
                "p_zener": p_zener,
                "p_series": p_series
            }
        
        # Nominal point
        nominal = calculate_point(input_ac_voltage, series_resistor, filter_capacitor, load_resistance)
        
        # Corner cases
        corners = {
            "max_input_voltage": calculate_point(vin_max, series_resistor, filter_capacitor, load_resistance),
            "min_input_voltage": calculate_point(vin_min, series_resistor, filter_capacitor, load_resistance),
            "max_series_resistor": calculate_point(input_ac_voltage, rs_max, filter_capacitor, load_resistance),
            "min_series_resistor": calculate_point(input_ac_voltage, rs_min, filter_capacitor, load_resistance),
            "max_filter_capacitor": calculate_point(input_ac_voltage, series_resistor, c_max, load_resistance),
            "min_filter_capacitor": calculate_point(input_ac_voltage, series_resistor, c_min, load_resistance),
            "max_load_resistance": calculate_point(input_ac_voltage, series_resistor, filter_capacitor, r_load_max),
            "min_load_resistance": calculate_point(input_ac_voltage, series_resistor, filter_capacitor, r_load_min),
        }
        
        # Extract extremes
        all_points = list(corners.values()) + [nominal]
        
        v_peaks = [p["v_peak"] for p in all_points]
        v_ripples = [p["v_ripple"] for p in all_points]
        v_filtered = [p["v_filtered"] for p in all_points]
        v_outs = [p["v_out"] for p in all_points]
        i_loads = [p["i_load"] for p in all_points]
        i_zeners = [p["i_zener"] for p in all_points]
        i_supplies = [p["i_supply"] for p in all_points]
        p_zeners = [p["p_zener"] for p in all_points]
        p_series_list = [p["p_series"] for p in all_points]
        
        # Regulation quality
        output_variation = (max(v_outs) - min(v_outs)) / output_voltage * 100 if output_voltage else 0
        load_regulation = (max(i_loads) - min(i_loads)) / nominal["i_load"] * 100 if nominal["i_load"] else 0
        
        analysis_data = {
            "nominal": nominal,
            "corners": corners,
            "extremes": {
                "peak_voltage": {
                    "min": float(min(v_peaks)),
                    "max": float(max(v_peaks)),
                    "nominal": float(nominal["v_peak"]),
                    "variation_percent": float((max(v_peaks) - min(v_peaks)) / nominal["v_peak"] * 100)
                },
                "ripple_voltage": {
                    "min": float(min(v_ripples)),
                    "max": float(max(v_ripples)),
                    "nominal": float(nominal["v_ripple"]),
                    "variation_percent": float((max(v_ripples) - min(v_ripples)) / nominal["v_ripple"] * 100) if nominal["v_ripple"] else 0
                },
                "filtered_dc": {
                    "min": float(min(v_filtered)),
                    "max": float(max(v_filtered)),
                    "nominal": float(nominal["v_filtered"])
                },
                "output_voltage": {
                    "min": float(min(v_outs)),
                    "max": float(max(v_outs)),
                    "nominal": float(nominal["v_out"]),
                    "regulation_percent": float(output_variation)
                },
                "load_current": {
                    "min": float(min(i_loads)),
                    "max": float(max(i_loads)),
                    "nominal": float(nominal["i_load"]),
                    "load_regulation_percent": float(load_regulation)
                },
                "zener_current": {
                    "min": float(min(i_zeners)),
                    "max": float(max(i_zeners)),
                    "nominal": float(nominal["i_zener"])
                },
                "supply_current": {
                    "min": float(min(i_supplies)),
                    "max": float(max(i_supplies)),
                    "nominal": float(nominal["i_supply"])
                },
                "zener_power": {
                    "min": float(min(p_zeners)),
                    "max": float(max(p_zeners)),
                    "nominal": float(nominal["p_zener"]),
                    "description": "P = V_z × I_z (worst case: worst at minimum load)"
                },
                "series_resistor_power": {
                    "min": float(min(p_series_list)),
                    "max": float(max(p_series_list)),
                    "nominal": float(nominal["p_series"]),
                    "description": "P = I² × R (worst case: worst at maximum load)"
                }
            },
            "worst_case_scenarios": {
                "highest_output_voltage": {
                    "value": float(max(v_outs)),
                    "condition": "Maximum peak voltage with good filtering",
                    "explanation": "Occurs with max input AC voltage"
                },
                "lowest_output_voltage": {
                    "value": float(min(v_outs)),
                    "condition": "Minimum peak voltage with poor filtering",
                    "explanation": "Occurs with min input AC voltage"
                },
                "maximum_zener_power": {
                    "value": float(max(p_zeners)),
                    "condition": "No load condition",
                    "explanation": "All supply current flows through zener; worst at minimum output voltage"
                },
                "maximum_series_resistor_power": {
                    "value": float(max(p_series_list)),
                    "condition": "Full load condition",
                    "explanation": "Maximum current draws maximum power; depends on load resistance"
                },
                "maximum_ripple": {
                    "value": float(max(v_ripples)),
                    "condition": "Minimum capacitor with maximum load",
                    "explanation": "Ripple = I_load / (f × C)"
                }
            }
        }
        
        summary = (
            f"Zener Shunt Regulator - Worst-Case Analysis\n"
            f"Output Voltage: {nominal['v_out']:.3f}V (nominal)\n"
            f"Output Variation: ±{output_variation:.2f}%\n"
            f"Peak Voltage Range: {min(v_peaks):.2f}V - {max(v_peaks):.2f}V\n"
            f"Ripple Voltage Range: {min(v_ripples):.3f}V - {max(v_ripples):.3f}V\n"
            f"Zener Power (max): {max(p_zeners):.2f}W\n"
            f"Series Resistor Power (max): {max(p_series_list):.2f}W\n"
            f"Load Regulation: ±{load_regulation:.2f}%"
        )
        
        return {
            "circuit_type": "ZENER_REGULATOR_WITH_BRIDGE_RECTIFIER",
            "analysis_data": analysis_data,
            "summary": summary
        }
