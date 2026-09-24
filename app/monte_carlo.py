"""Monte Carlo analysis with user-defined tolerances"""
import numpy as np
import math
from typing import Any, Dict, List, Tuple, Optional


class MonteCarloAnalysis:
    """Monte Carlo simulation engine"""

    @staticmethod
    def _stats_dict(samples) -> Dict:
        """Create a standard statistics dictionary from a numpy array."""
        return {
            "samples": samples.tolist(),
            "mean": float(np.mean(samples)),
            "std_dev": float(np.std(samples)),
            "min": float(np.min(samples)),
            "max": float(np.max(samples)),
            "percentile_5": float(np.percentile(samples, 5)),
            "percentile_95": float(np.percentile(samples, 95)),
            "absolute_min": float(np.min(np.abs(samples))),
            "absolute_max": float(np.max(np.abs(samples)))
        }
    
    @staticmethod
    def _rc_lowpass_magnitude_response(frequency: float, fc: float) -> float:
        """Calculate magnitude response of RC low-pass filter"""
        if frequency <= 0:
            return 1.0
        ratio = frequency / fc
        return 1.0 / np.sqrt(1 + ratio**2)
    
    @staticmethod
    def _rc_highpass_magnitude_response(frequency: float, fc: float) -> float:
        """Calculate magnitude response of RC high-pass filter"""
        if frequency <= 0:
            return 0.0
        ratio = frequency / fc
        return ratio / np.sqrt(1 + ratio**2)
    
    @staticmethod
    def simulate_rc_low_pass(
        r_nominal: float,
        c_nominal: float,
        vin_nominal: float,
        num_samples: int,
        r1_tolerance: float,
        capacitor_tolerance: float,
        line_fluctuation: float,
        voltage_type: str = "DC",
        test_frequency: float = None
    ) -> Dict:
        """Monte Carlo for RC low-pass filter"""
        
        # Convert percentages to normalized tolerances
        tol_r = r1_tolerance / 100.0
        tol_c = capacitor_tolerance / 100.0
        tol_vin = line_fluctuation / 100.0
        
        # Generate random variations
        r_samples = r_nominal * (1 + np.random.uniform(-tol_r, tol_r, num_samples))
        c_samples = c_nominal * (1 + np.random.uniform(-tol_c, tol_c, num_samples))
        vin_samples = vin_nominal * (1 + np.random.uniform(-tol_vin, tol_vin, num_samples))
        
        # Calculate metrics for each sample
        fc_samples = 1 / (2 * np.pi * r_samples * c_samples)
        tau_samples = r_samples * c_samples
        
        # Calculate frequency response output voltage
        fc_nominal = 1 / (2 * np.pi * r_nominal * c_nominal)
        test_freq = test_frequency if test_frequency else fc_nominal
        
        # Vectorized magnitude response calculation for efficiency
        # |H(jf)| = 1 / sqrt(1 + (f/fc)^2)
        ratio = test_freq / fc_samples
        mag_samples = 1.0 / np.sqrt(1 + ratio**2)
        vout_samples = mag_samples * vin_samples
        
        # Compile results with R and C included in MC statistics
        results = {
            "resistor": {
                "samples": r_samples.tolist(),
                "mean": float(np.mean(r_samples)),
                "std_dev": float(np.std(r_samples)),
                "min": float(np.min(r_samples)),
                "max": float(np.max(r_samples)),
                "percentile_5": float(np.percentile(r_samples, 5)),
                "percentile_95": float(np.percentile(r_samples, 95)),
                "absolute_min": float(np.min(np.abs(r_samples))),
                "absolute_max": float(np.max(np.abs(r_samples)))
            },
            "capacitor": {
                "samples": c_samples.tolist(),
                "mean": float(np.mean(c_samples)),
                "std_dev": float(np.std(c_samples)),
                "min": float(np.min(c_samples)),
                "max": float(np.max(c_samples)),
                "percentile_5": float(np.percentile(c_samples, 5)),
                "percentile_95": float(np.percentile(c_samples, 95)),
                "absolute_min": float(np.min(np.abs(c_samples))),
                "absolute_max": float(np.max(np.abs(c_samples)))
            },
            "input_voltage": {
                "samples": vin_samples.tolist(),
                "mean": float(np.mean(vin_samples)),
                "std_dev": float(np.std(vin_samples)),
                "min": float(np.min(vin_samples)),
                "max": float(np.max(vin_samples)),
                "percentile_5": float(np.percentile(vin_samples, 5)),
                "percentile_95": float(np.percentile(vin_samples, 95)),
                "absolute_min": float(np.min(np.abs(vin_samples))),
                "absolute_max": float(np.max(np.abs(vin_samples))),
                "voltage_type": voltage_type
            },
            "cutoff_frequency": {
                "samples": fc_samples.tolist(),
                "mean": float(np.mean(fc_samples)),
                "std_dev": float(np.std(fc_samples)),
                "min": float(np.min(fc_samples)),
                "max": float(np.max(fc_samples)),
                "percentile_5": float(np.percentile(fc_samples, 5)),
                "percentile_95": float(np.percentile(fc_samples, 95)),
                "absolute_min": float(np.min(np.abs(fc_samples))),
                "absolute_max": float(np.max(np.abs(fc_samples)))
            },
            "time_constant": {
                "samples": tau_samples.tolist(),
                "mean": float(np.mean(tau_samples)),
                "std_dev": float(np.std(tau_samples)),
                "min": float(np.min(tau_samples)),
                "max": float(np.max(tau_samples)),
                "percentile_5": float(np.percentile(tau_samples, 5)),
                "percentile_95": float(np.percentile(tau_samples, 95)),
                "absolute_min": float(np.min(np.abs(tau_samples))),
                "absolute_max": float(np.max(np.abs(tau_samples)))
            },
            "output_voltage": {
                "samples": vout_samples.tolist(),
                "mean": float(np.mean(vout_samples)),
                "std_dev": float(np.std(vout_samples)),
                "min": float(np.min(vout_samples)),
                "max": float(np.max(vout_samples)),
                "percentile_5": float(np.percentile(vout_samples, 5)),
                "percentile_95": float(np.percentile(vout_samples, 95)),
                "absolute_min": float(np.min(np.abs(vout_samples))),
                "absolute_max": float(np.max(np.abs(vout_samples))),
                "voltage_type": voltage_type,
                "test_frequency": test_freq
            },
            "raw_data": {
                "r_values": r_samples.tolist(),
                "c_values": c_samples.tolist(),
                "vin_values": vin_samples.tolist(),
                "fc_values": fc_samples.tolist(),
                "tau_values": tau_samples.tolist()
            },
            "derivation": [
                f"Output voltage at f={test_freq:.1f}Hz: V_out = |H(jf)| × V_in",
                f"Magnitude response accounts for variation in R,C tolerances through fc",
                f"Each sample: V_out = 1/√(1+(f/fc)²) × V_in"
            ]
        }
        
        return results
    
    @staticmethod
    def simulate_rc_high_pass(
        r_nominal: float,
        c_nominal: float,
        vin_nominal: float,
        num_samples: int,
        r1_tolerance: float,
        capacitor_tolerance: float,
        line_fluctuation: float,
        voltage_type: str = "DC",
        test_frequency: float = None
    ) -> Dict:
        """Monte Carlo for RC high-pass filter"""
        
        tol_r = r1_tolerance / 100.0
        tol_c = capacitor_tolerance / 100.0
        tol_vin = line_fluctuation / 100.0
        
        r_samples = r_nominal * (1 + np.random.uniform(-tol_r, tol_r, num_samples))
        c_samples = c_nominal * (1 + np.random.uniform(-tol_c, tol_c, num_samples))
        vin_samples = vin_nominal * (1 + np.random.uniform(-tol_vin, tol_vin, num_samples))
        
        fc_samples = 1 / (2 * np.pi * r_samples * c_samples)
        tau_samples = r_samples * c_samples
        
        # Calculate frequency response output voltage
        fc_nominal = 1 / (2 * np.pi * r_nominal * c_nominal)
        test_freq = test_frequency if test_frequency else fc_nominal
        
        # Vectorized magnitude response calculation for efficiency
        # For high-pass: |H(jf)| = (f/fc) / sqrt(1 + (f/fc)^2)
        ratio = test_freq / fc_samples
        mag_samples = ratio / np.sqrt(1 + ratio**2)
        vout_samples = mag_samples * vin_samples
        
        results = {
            "resistor": {
                "samples": r_samples.tolist(),
                "mean": float(np.mean(r_samples)),
                "std_dev": float(np.std(r_samples)),
                "min": float(np.min(r_samples)),
                "max": float(np.max(r_samples)),
                "percentile_5": float(np.percentile(r_samples, 5)),
                "percentile_95": float(np.percentile(r_samples, 95)),
                "absolute_min": float(np.min(np.abs(r_samples))),
                "absolute_max": float(np.max(np.abs(r_samples)))
            },
            "capacitor": {
                "samples": c_samples.tolist(),
                "mean": float(np.mean(c_samples)),
                "std_dev": float(np.std(c_samples)),
                "min": float(np.min(c_samples)),
                "max": float(np.max(c_samples)),
                "percentile_5": float(np.percentile(c_samples, 5)),
                "percentile_95": float(np.percentile(c_samples, 95)),
                "absolute_min": float(np.min(np.abs(c_samples))),
                "absolute_max": float(np.max(np.abs(c_samples)))
            },
            "cutoff_frequency": {
                "samples": fc_samples.tolist(),
                "mean": float(np.mean(fc_samples)),
                "std_dev": float(np.std(fc_samples)),
                "min": float(np.min(fc_samples)),
                "max": float(np.max(fc_samples)),
                "percentile_5": float(np.percentile(fc_samples, 5)),
                "percentile_95": float(np.percentile(fc_samples, 95)),
                "absolute_min": float(np.min(np.abs(fc_samples))),
                "absolute_max": float(np.max(np.abs(fc_samples)))
            },
            "time_constant": {
                "samples": tau_samples.tolist(),
                "mean": float(np.mean(tau_samples)),
                "std_dev": float(np.std(tau_samples)),
                "min": float(np.min(tau_samples)),
                "max": float(np.max(tau_samples)),
                "percentile_5": float(np.percentile(tau_samples, 5)),
                "percentile_95": float(np.percentile(tau_samples, 95)),
                "absolute_min": float(np.min(np.abs(tau_samples))),
                "absolute_max": float(np.max(np.abs(tau_samples)))
            },
            "output_voltage": {
                "samples": vout_samples.tolist(),
                "mean": float(np.mean(vout_samples)),
                "std_dev": float(np.std(vout_samples)),
                "min": float(np.min(vout_samples)),
                "max": float(np.max(vout_samples)),
                "percentile_5": float(np.percentile(vout_samples, 5)),
                "percentile_95": float(np.percentile(vout_samples, 95)),
                "absolute_min": float(np.min(np.abs(vout_samples))),
                "absolute_max": float(np.max(np.abs(vout_samples))),
                "voltage_type": voltage_type,
                "test_frequency": test_freq
            },
            "raw_data": {
                "r_values": r_samples.tolist(),
                "c_values": c_samples.tolist(),
                "vin_values": vin_samples.tolist(),
                "fc_values": fc_samples.tolist(),
                "tau_values": tau_samples.tolist()
            },
            "derivation": [
                f"Output voltage at f={test_freq:.1f}Hz: V_out = |H(jf)| × V_in",
                f"High-pass magnitude response: |H(jf)| = (f/fc) / √(1+(f/fc)²)",
                f"Accounts for variation in R,C tolerances through fc"
            ]
        }
        
        return results
    
    @staticmethod
    def simulate_rc_charging(
        r_nominal: float,
        c_nominal: float,
        vin_nominal: float,
        num_samples: int,
        r1_tolerance: float,
        capacitor_tolerance: float,
        line_fluctuation: float,
        time_value: float = 1.0,
        voltage_type: str = "DC"
    ) -> Dict:
        """Monte Carlo for RC charging circuit"""
        
        tol_r = r1_tolerance / 100.0
        tol_c = capacitor_tolerance / 100.0
        tol_vin = line_fluctuation / 100.0
        
        r_samples = r_nominal * (1 + np.random.uniform(-tol_r, tol_r, num_samples))
        c_samples = c_nominal * (1 + np.random.uniform(-tol_c, tol_c, num_samples))
        vin_samples = vin_nominal * (1 + np.random.uniform(-tol_vin, tol_vin, num_samples))
        
        tau_samples = r_samples * c_samples
        # V_c(t) = V_in * (1 - exp(-t / tau))
        vc_samples = vin_samples * (1 - np.exp(-time_value / tau_samples))
        
        results = {
            "resistor": {
                "samples": r_samples.tolist(),
                "mean": float(np.mean(r_samples)),
                "std_dev": float(np.std(r_samples)),
                "min": float(np.min(r_samples)),
                "max": float(np.max(r_samples)),
                "percentile_5": float(np.percentile(r_samples, 5)),
                "percentile_95": float(np.percentile(r_samples, 95)),
                "absolute_min": float(np.min(np.abs(r_samples))),
                "absolute_max": float(np.max(np.abs(r_samples)))
            },
            "capacitor": {
                "samples": c_samples.tolist(),
                "mean": float(np.mean(c_samples)),
                "std_dev": float(np.std(c_samples)),
                "min": float(np.min(c_samples)),
                "max": float(np.max(c_samples)),
                "percentile_5": float(np.percentile(c_samples, 5)),
                "percentile_95": float(np.percentile(c_samples, 95)),
                "absolute_min": float(np.min(np.abs(c_samples))),
                "absolute_max": float(np.max(np.abs(c_samples)))
            },
            "time_constant": {
                "samples": tau_samples.tolist(),
                "mean": float(np.mean(tau_samples)),
                "std_dev": float(np.std(tau_samples)),
                "min": float(np.min(tau_samples)),
                "max": float(np.max(tau_samples)),
                "percentile_5": float(np.percentile(tau_samples, 5)),
                "percentile_95": float(np.percentile(tau_samples, 95)),
                "absolute_min": float(np.min(np.abs(tau_samples))),
                "absolute_max": float(np.max(np.abs(tau_samples)))
            },
            "capacitor_voltage": {
                "samples": vc_samples.tolist(),
                "mean": float(np.mean(vc_samples)),
                "std_dev": float(np.std(vc_samples)),
                "min": float(np.min(vc_samples)),
                "max": float(np.max(vc_samples)),
                "percentile_5": float(np.percentile(vc_samples, 5)),
                "percentile_95": float(np.percentile(vc_samples, 95)),
                "absolute_min": float(np.min(np.abs(vc_samples))),
                "absolute_max": float(np.max(np.abs(vc_samples)))
            },
            "output_voltage": {
                "samples": vin_samples.tolist(),
                "mean": float(np.mean(vin_samples)),
                "std_dev": float(np.std(vin_samples)),
                "min": float(np.min(vin_samples)),
                "max": float(np.max(vin_samples)),
                "percentile_5": float(np.percentile(vin_samples, 5)),
                "percentile_95": float(np.percentile(vin_samples, 95)),
                "absolute_min": float(np.min(np.abs(vin_samples))),
                "absolute_max": float(np.max(np.abs(vin_samples))),
                "voltage_type": voltage_type
            },
            "raw_data": {
                "r_values": r_samples.tolist(),
                "c_values": c_samples.tolist(),
                "vin_values": vin_samples.tolist(),
                "tau_values": tau_samples.tolist(),
                "vc_values": vc_samples.tolist()
            },
            "derivation": [
                f"Input voltage type: {voltage_type}",
                f"If AC RMS, converted to peak: V_peak = V_rms * sqrt(2)",
                f"If AC Peak, used as-is.",
                f"If DC, used as-is."
            ]
        }
        
        return results
    
    @staticmethod
    def simulate_opamp_gain(
        circuit_type: str,
        gain_nominal: float,
        vin_nominal: float,
        num_samples: int,
        r1_tolerance: float,
        r2_tolerance: Optional[float],
        capacitor_tolerance: float,
        line_fluctuation: float,
        resistor_ohms: Optional[float] = None,
        resistor_ohms_2: Optional[float] = None,
        capacitor_farads: Optional[float] = None,
        cutoff_frequency: Optional[float] = None
    ) -> Dict:
        """Monte Carlo for op-amp gain (non-inverting or inverting)"""
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

        # Tolerance draws
        r1_factor = np.random.uniform(-tol_r1, tol_r1, num_samples)
        r2_factor = np.random.uniform(-tol_r2, tol_r2, num_samples)
        c_factor = np.random.uniform(-tol_c, tol_c, num_samples)

        # Component samples
        r1_samples = r1_nominal * (1 + r1_factor)
        r2_samples = r2_nominal * (1 + r2_factor)
        c_nominal = capacitor_farads if capacitor_farads and capacitor_farads > 0 else 1e-6
        c_samples = np.ones(num_samples) * c_nominal
        c_samples = c_samples * (1 + c_factor)

        is_active_filter = circuit_name == "ACTIVE_OPAMP_FILTER"

        if circuit_name == "INVERTING_OPAMP":
            gain_samples = -(r2_samples / r1_samples)
        else:
            gain_samples = 1 + (r2_samples / r1_samples)

        vin_samples = vin_nominal * (1 + np.random.uniform(-tol_vin, tol_vin, num_samples))

        results: Dict[str, Any] = {
            "resistor": MonteCarloAnalysis._stats_dict(r1_samples),
            "resistor_2": MonteCarloAnalysis._stats_dict(r2_samples),
            "capacitor": MonteCarloAnalysis._stats_dict(c_samples),
            "gain": MonteCarloAnalysis._stats_dict(gain_samples),
            "input_voltage": MonteCarloAnalysis._stats_dict(vin_samples)
        }

        if is_active_filter:
            fc_samples = 1 / (2 * np.pi * r2_samples * c_samples)
            tau_samples = r2_samples * c_samples
            test_freq = cutoff_frequency if cutoff_frequency and cutoff_frequency > 0 else float(np.mean(fc_samples))
            ratio = test_freq / fc_samples
            mag_samples = 1.0 / np.sqrt(1 + ratio**2)
            vout_samples = gain_samples * mag_samples * vin_samples

            results["cutoff_frequency"] = MonteCarloAnalysis._stats_dict(fc_samples)
            results["time_constant"] = MonteCarloAnalysis._stats_dict(tau_samples)
            output_stats = MonteCarloAnalysis._stats_dict(vout_samples)
            output_stats["test_frequency"] = float(test_freq)
            results["output_voltage"] = output_stats
            results["raw_data"] = {
                "r1_values": r1_samples.tolist(),
                "r2_values": r2_samples.tolist(),
                "c_values": c_samples.tolist(),
                "gain_values": gain_samples.tolist(),
                "vin_values": vin_samples.tolist(),
                "fc_values": fc_samples.tolist(),
                "tau_values": tau_samples.tolist(),
                "vout_values": vout_samples.tolist()
            }
            results["derivation"] = [
                f"Active op-amp LPF uses fc = 1/(2πR2C) with feedback resistor variation and capacitor tolerance.",
                f"At test frequency f={test_freq:.2f}Hz, |H(jf)| = 1/√(1 + (f/fc)^2).",
                f"Each sample output: Vout = Gain × |H(jf)| × Vin."
            ]
            return results

        vout_samples = gain_samples * vin_samples
        results["output_voltage"] = MonteCarloAnalysis._stats_dict(vout_samples)
        results["raw_data"] = {
            "r1_values": r1_samples.tolist(),
            "r2_values": r2_samples.tolist(),
            "c_values": c_samples.tolist(),
            "gain_values": gain_samples.tolist(),
            "vin_values": vin_samples.tolist(),
            "vout_values": vout_samples.tolist()
        }
        
        return results
    @staticmethod
    def simulate_linear_regulator_with_bridge_rectifier(
        input_ac_voltage: float,
        output_voltage: float,
        filter_capacitor: float,
        series_resistor: float,
        zener_voltage: float,
        load_current: float,
        num_samples: int,
        input_voltage_tolerance: float,
        capacitor_tolerance: float,
        r1_tolerance: float,
        load_current_tolerance: float
    ) -> Dict:
        """
        Monte Carlo analysis for linear regulator with full bridge rectifier.
        
        Analyzes output voltage stability under component tolerance variations.
        """
        # Convert percentages to normalized tolerances
        tol_vin = input_voltage_tolerance / 100.0
        tol_c = capacitor_tolerance / 100.0
        tol_r = r1_tolerance / 100.0
        tol_iload = load_current_tolerance / 100.0
        
        # Generate random variations
        vin_samples = input_ac_voltage * (1 + np.random.uniform(-tol_vin, tol_vin, num_samples))
        c_samples = filter_capacitor * (1 + np.random.uniform(-tol_c, tol_c, num_samples))
        iload_samples = load_current * (1 + np.random.uniform(-tol_iload, tol_iload, num_samples))
        
        # Constants for rectifier circuit
        diode_forward_voltage = 0.7  # Volts
        regulator_dropout = 0.2  # Volts (typical for LM78xx)
        
        # Step 1: Calculate peak voltage after rectifier (full-wave: Vac*sqrt(2) - 2*Vdiode)
        v_peak = vin_samples * math.sqrt(2) - 2 * diode_forward_voltage
        
        # Step 2: Calculate ripple voltage based on capacitor and load
        # V_ripple = I_load / (f * C)
        rectifier_frequency = 120  # Hz (full-wave rectification of 60Hz AC)
        v_ripple = iload_samples / (rectifier_frequency * c_samples)
        
        # Step 3: Calculate average DC voltage at filter capacitor output
        v_filtered = v_peak - v_ripple / 2
        
        # Step 4: Output voltage follows the regulator target while sufficient
        # headroom is available; otherwise it falls toward the available input.
        vout_samples = np.where(
            v_filtered >= (output_voltage + regulator_dropout),
            output_voltage,
            np.maximum(v_filtered - regulator_dropout, 0)
        )

        # Optional compatibility placeholders: no external series resistor in
        # the standard linear-regulator power path.
        r_samples = np.zeros(num_samples)
        power_resistor = np.zeros(num_samples)
        
        # Compile results
        results = {
            "input_ac_voltage": {
                "samples": vin_samples.tolist(),
                "mean": float(np.mean(vin_samples)),
                "std_dev": float(np.std(vin_samples)),
                "min": float(np.min(vin_samples)),
                "max": float(np.max(vin_samples)),
                "percentile_5": float(np.percentile(vin_samples, 5)),
                "percentile_95": float(np.percentile(vin_samples, 95)),
                "absolute_min": float(np.min(np.abs(vin_samples))),
                "absolute_max": float(np.max(np.abs(vin_samples)))
            },
            "filter_capacitor": {
                "samples": c_samples.tolist(),
                "mean": float(np.mean(c_samples)),
                "std_dev": float(np.std(c_samples)),
                "min": float(np.min(c_samples)),
                "max": float(np.max(c_samples)),
                "percentile_5": float(np.percentile(c_samples, 5)),
                "percentile_95": float(np.percentile(c_samples, 95)),
                "absolute_min": float(np.min(np.abs(c_samples))),
                "absolute_max": float(np.max(np.abs(c_samples)))
            },
            "series_resistor": {
                "samples": r_samples.tolist(),
                "mean": 0.0,
                "std_dev": 0.0,
                "min": 0.0,
                "max": 0.0,
                "percentile_5": 0.0,
                "percentile_95": 0.0,
                "absolute_min": 0.0,
                "absolute_max": 0.0
            },
            "load_current": {
                "samples": iload_samples.tolist(),
                "mean": float(np.mean(iload_samples)),
                "std_dev": float(np.std(iload_samples)),
                "min": float(np.min(iload_samples)),
                "max": float(np.max(iload_samples)),
                "percentile_5": float(np.percentile(iload_samples, 5)),
                "percentile_95": float(np.percentile(iload_samples, 95)),
                "absolute_min": float(np.min(np.abs(iload_samples))),
                "absolute_max": float(np.max(np.abs(iload_samples)))
            },
            "peak_input_voltage": {
                "samples": v_peak.tolist(),
                "mean": float(np.mean(v_peak)),
                "std_dev": float(np.std(v_peak)),
                "min": float(np.min(v_peak)),
                "max": float(np.max(v_peak)),
                "percentile_5": float(np.percentile(v_peak, 5)),
                "percentile_95": float(np.percentile(v_peak, 95))
            },
            "ripple_voltage": {
                "samples": v_ripple.tolist(),
                "mean": float(np.mean(v_ripple)),
                "std_dev": float(np.std(v_ripple)),
                "min": float(np.min(v_ripple)),
                "max": float(np.max(v_ripple)),
                "percentile_5": float(np.percentile(v_ripple, 5)),
                "percentile_95": float(np.percentile(v_ripple, 95))
            },
            "output_voltage": {
                "samples": vout_samples.tolist(),
                "mean": float(np.mean(vout_samples)),
                "std_dev": float(np.std(vout_samples)),
                "min": float(np.min(vout_samples)),
                "max": float(np.max(vout_samples)),
                "percentile_5": float(np.percentile(vout_samples, 5)),
                "percentile_95": float(np.percentile(vout_samples, 95)),
                "absolute_min": float(np.min(np.abs(vout_samples))),
                "absolute_max": float(np.max(np.abs(vout_samples)))
            },
            "power_dissipation_resistor": {
                "samples": power_resistor.tolist(),
                "mean": float(np.mean(power_resistor)),
                "std_dev": float(np.std(power_resistor)),
                "min": float(np.min(power_resistor)),
                "max": float(np.max(power_resistor)),
                "percentile_5": float(np.percentile(power_resistor, 5)),
                "percentile_95": float(np.percentile(power_resistor, 95))
            },
            "raw_data": {
                "input_ac_values": vin_samples.tolist(),
                "peak_values": v_peak.tolist(),
                "ripple_values": v_ripple.tolist(),
                "filtered_dc_values": (v_peak - v_ripple/2).tolist(),
                "load_current_values": iload_samples.tolist(),
                "output_voltage_values": vout_samples.tolist(),
                "power_dissipation_values": power_resistor.tolist()
            }
        }
        
        return results
    
    @staticmethod
    def simulate_zener_regulator_with_bridge_rectifier(
        input_ac_voltage: float,
        output_voltage: float,
        load_resistance: float,
        series_resistor: float,
        zener_voltage: float,
        filter_capacitor: float,
        num_samples: int,
        ac_voltage_tolerance: float = 5.0,
        resistor_tolerance: float = 5.0,
        capacitor_tolerance: float = 10.0,
        load_tolerance: float = 10.0,
        line_frequency_hz: float = 60.0,
        diode_forward_voltage: float = 0.7
    ) -> Dict:
        """Monte Carlo analysis of zener shunt regulator
        
        Simulates the performance with component tolerances and
        input voltage variations.
        """
        
        np.random.seed(42)  # Reproducible results
        
        # Constants
        rectifier_frequency = line_frequency_hz * 2
        ripple_voltage_nominal = 0.5
        
        # Generate random samples with tolerances
        vin_samples = np.random.normal(
            input_ac_voltage,
            input_ac_voltage * (ac_voltage_tolerance / 100) / 3,
            num_samples
        )
        vin_samples = np.clip(vin_samples, input_ac_voltage * 0.85, input_ac_voltage * 1.15)
        
        # Component variations
        rs_samples = np.random.normal(
            series_resistor,
            series_resistor * (resistor_tolerance / 100) / 3,
            num_samples
        )
        rs_samples = np.clip(rs_samples, series_resistor * (1 - resistor_tolerance/100), 
                             series_resistor * (1 + resistor_tolerance/100))
        
        c_samples = np.random.normal(
            filter_capacitor,
            filter_capacitor * (capacitor_tolerance / 100) / 3,
            num_samples
        )
        c_samples = np.clip(c_samples, filter_capacitor * (1 - capacitor_tolerance/100),
                            filter_capacitor * (1 + capacitor_tolerance/100))
        
        r_load_samples = np.random.normal(
            load_resistance,
            load_resistance * (load_tolerance / 100) / 3,
            num_samples
        )
        r_load_samples = np.clip(r_load_samples, load_resistance * (1 - load_tolerance/100),
                                 load_resistance * (1 + load_tolerance/100))
        
        # Initialize result arrays
        v_peak_samples = np.zeros(num_samples)
        v_ripple_samples = np.zeros(num_samples)
        v_filtered_samples = np.zeros(num_samples)
        i_load_samples = np.zeros(num_samples)
        i_zener_samples = np.zeros(num_samples)
        v_out_samples = np.zeros(num_samples)
        p_zener_samples = np.zeros(num_samples)
        p_series_samples = np.zeros(num_samples)
        
        # Monte Carlo loop
        for i in range(num_samples):
            # Peak voltage after rectification
            v_peak = vin_samples[i] * math.sqrt(2) - 2 * diode_forward_voltage
            v_peak_samples[i] = v_peak
            
            # Calculate ripple based on capacitor
            estimated_load_current = output_voltage / r_load_samples[i]
            ripple = estimated_load_current / (rectifier_frequency * c_samples[i])
            v_ripple_samples[i] = ripple
            
            # Filtered DC voltage
            v_filtered = v_peak - ripple / 2
            v_filtered_samples[i] = v_filtered
            
            # Output voltage (regulated by zener)
            # With load: V_out = V_z approximately
            # But with variation in component tolerances
            v_out = zener_voltage * 1.05  # Small variation from nominal
            # Degrade regulation slightly based on ripple
            v_out -= ripple * 0.1  # Ripple effect
            v_out = np.clip(v_out, 0, zener_voltage * 1.1)
            v_out_samples[i] = v_out
            
            # Load current
            i_load = v_out / r_load_samples[i]
            i_load_samples[i] = i_load
            
            # Supply current
            i_supply = (v_filtered - v_out) / rs_samples[i]
            
            # Zener current
            i_z = i_supply - i_load
            i_z = max(i_z, 0)  # Zener can't source current
            i_zener_samples[i] = i_z
            
            # Power dissipation
            p_z = zener_voltage * i_z
            p_zener_samples[i] = p_z
            
            p_r = (i_supply ** 2) * rs_samples[i]
            p_series_samples[i] = p_r
        
        # Statistics
        results = {
            "num_samples": num_samples,
            "input_voltage_ac": {
                "mean": float(np.mean(vin_samples)),
                "std_dev": float(np.std(vin_samples)),
                "min": float(np.min(vin_samples)),
                "max": float(np.max(vin_samples)),
                "percentile_5": float(np.percentile(vin_samples, 5)),
                "percentile_95": float(np.percentile(vin_samples, 95))
            },
            "peak_voltage": {
                "mean": float(np.mean(v_peak_samples)),
                "std_dev": float(np.std(v_peak_samples)),
                "min": float(np.min(v_peak_samples)),
                "max": float(np.max(v_peak_samples)),
                "percentile_5": float(np.percentile(v_peak_samples, 5)),
                "percentile_95": float(np.percentile(v_peak_samples, 95))
            },
            "ripple_voltage": {
                "mean": float(np.mean(v_ripple_samples)),
                "std_dev": float(np.std(v_ripple_samples)),
                "min": float(np.min(v_ripple_samples)),
                "max": float(np.max(v_ripple_samples)),
                "percentile_5": float(np.percentile(v_ripple_samples, 5)),
                "percentile_95": float(np.percentile(v_ripple_samples, 95))
            },
            "filtered_dc_voltage": {
                "mean": float(np.mean(v_filtered_samples)),
                "std_dev": float(np.std(v_filtered_samples)),
                "min": float(np.min(v_filtered_samples)),
                "max": float(np.max(v_filtered_samples)),
                "percentile_5": float(np.percentile(v_filtered_samples, 5)),
                "percentile_95": float(np.percentile(v_filtered_samples, 95))
            },
            "load_current": {
                "mean": float(np.mean(i_load_samples)),
                "std_dev": float(np.std(i_load_samples)),
                "min": float(np.min(i_load_samples)),
                "max": float(np.max(i_load_samples)),
                "percentile_5": float(np.percentile(i_load_samples, 5)),
                "percentile_95": float(np.percentile(i_load_samples, 95))
            },
            "zener_current": {
                "mean": float(np.mean(i_zener_samples)),
                "std_dev": float(np.std(i_zener_samples)),
                "min": float(np.min(i_zener_samples)),
                "max": float(np.max(i_zener_samples)),
                "percentile_5": float(np.percentile(i_zener_samples, 5)),
                "percentile_95": float(np.percentile(i_zener_samples, 95))
            },
            "output_voltage": {
                "mean": float(np.mean(v_out_samples)),
                "std_dev": float(np.std(v_out_samples)),
                "min": float(np.min(v_out_samples)),
                "max": float(np.max(v_out_samples)),
                "percentile_5": float(np.percentile(v_out_samples, 5)),
                "percentile_95": float(np.percentile(v_out_samples, 95)),
                "regulation_percent": float((np.std(v_out_samples) / np.mean(v_out_samples)) * 100)
            },
            "zener_power": {
                "mean": float(np.mean(p_zener_samples)),
                "std_dev": float(np.std(p_zener_samples)),
                "min": float(np.min(p_zener_samples)),
                "max": float(np.max(p_zener_samples)),
                "percentile_5": float(np.percentile(p_zener_samples, 5)),
                "percentile_95": float(np.percentile(p_zener_samples, 95))
            },
            "series_resistor_power": {
                "mean": float(np.mean(p_series_samples)),
                "std_dev": float(np.std(p_series_samples)),
                "min": float(np.min(p_series_samples)),
                "max": float(np.max(p_series_samples)),
                "percentile_5": float(np.percentile(p_series_samples, 5)),
                "percentile_95": float(np.percentile(p_series_samples, 95))
            },
            "raw_data": {
                "input_ac_values": vin_samples.tolist(),
                "peak_values": v_peak_samples.tolist(),
                "ripple_values": v_ripple_samples.tolist(),
                "filtered_dc_values": v_filtered_samples.tolist(),
                "load_current_values": i_load_samples.tolist(),
                "zener_current_values": i_zener_samples.tolist(),
                "output_voltage_values": v_out_samples.tolist(),
                "zener_power_values": p_zener_samples.tolist(),
                "series_resistor_power_values": p_series_samples.tolist()
            }
        }
        
        return results
