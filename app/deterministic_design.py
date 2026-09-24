"""Deterministic circuit synthesis using analytical formulas"""
import math
from typing import Tuple, Dict


E24_VALUES = [10, 11, 12, 13, 15, 16, 18, 20, 22, 24, 27, 30, 33, 36, 39, 43, 47, 51, 56, 62, 68, 75, 82, 91]


def find_closest_e24_resistor(target: float) -> Tuple[float, str]:
    """Find closest E24 standard resistor and return value and display string"""
    decade_exp = math.floor(math.log10(target))
    candidates = []
    
    for exp in [decade_exp - 1, decade_exp]:
        decade = 10 ** exp
        for e24_val in E24_VALUES:
            candidates.append(e24_val * decade)
    
    value = min(candidates, key=lambda x: abs(x - target))
    
    if value >= 1e6:
        display = f"{value / 1e6:.1f}MΩ"
    elif value >= 1e3:
        display = f"{value / 1e3:.1f}kΩ"
    else:
        display = f"{value:.1f}Ω"
    
    return value, display


def format_capacitor(farads: float) -> str:
    """Format capacitor value to readable string"""
    if farads >= 1e-6:
        return f"{farads * 1e6:.2f}µF"
    elif farads >= 1e-9:
        return f"{farads * 1e9:.2f}nF"
    elif farads >= 1e-12:
        return f"{farads * 1e12:.2f}pF"
    else:
        return f"{farads:.2e}F"


def format_resistor(ohms: float) -> str:
    """Format resistor value to readable string"""
    if ohms >= 1e6:
        return f"{ohms / 1e6:.2f}MΩ"
    elif ohms >= 1e3:
        return f"{ohms / 1e3:.2f}kΩ"
    return f"{ohms:.2f}Ω"


class DeterministicDesign:
    """Analytical circuit synthesis engine"""

    @staticmethod
    def _derive_rc_values(
        cutoff_frequency: float = None,
        time_duration: float = None,
        resistor_ohms: float = None,
        capacitor_farads: float = None
    ) -> Tuple[float, float, list[str]]:
        """Resolve RC values from user overrides or analytical formulas."""
        notes = []

        if resistor_ohms and capacitor_farads:
            notes.append("Using user-provided resistor and capacitor values")
            return resistor_ohms, capacitor_farads, notes

        if cutoff_frequency is not None and cutoff_frequency <= 0:
            raise ValueError("Cutoff frequency must be greater than zero")
        if time_duration is not None and time_duration <= 0:
            raise ValueError("Time duration must be greater than zero")

        if resistor_ohms and cutoff_frequency:
            derived_c = 1 / (2 * math.pi * cutoff_frequency * resistor_ohms)
            notes.append("Using user-provided resistor and solving for capacitor")
            return resistor_ohms, derived_c, notes

        if capacitor_farads and cutoff_frequency:
            derived_r = 1 / (2 * math.pi * cutoff_frequency * capacitor_farads)
            notes.append("Using user-provided capacitor and solving for resistor")
            return derived_r, capacitor_farads, notes

        if resistor_ohms and time_duration:
            derived_c = time_duration / resistor_ohms
            notes.append("Using user-provided resistor and solving for capacitor from τ = RC")
            return resistor_ohms, derived_c, notes

        if capacitor_farads and time_duration:
            derived_r = time_duration / capacitor_farads
            notes.append("Using user-provided capacitor and solving for resistor from τ = RC")
            return derived_r, capacitor_farads, notes

        return None, None, notes
    
    @staticmethod
    def design_rc_low_pass(
        cutoff_frequency: float,
        voltage_value: float,
        resistor_ohms: float = None,
        capacitor_farads: float = None
    ) -> Dict:
        """Design RC low-pass filter: fc = 1 / (2πRC)"""
        resolved_r, resolved_c, notes = DeterministicDesign._derive_rc_values(
            cutoff_frequency=cutoff_frequency,
            resistor_ohms=resistor_ohms,
            capacitor_farads=capacitor_farads
        )

        if resolved_r and resolved_c:
            actual_fc = 1 / (2 * math.pi * resolved_r * resolved_c)
            derivation = [
                f"RC Low-Pass Filter: fc = 1/(2πRC)",
                f"Target cutoff: {cutoff_frequency} Hz",
                *notes,
                f"Resistor R = {format_resistor(resolved_r)}",
                f"Capacitor C = {format_capacitor(resolved_c)}",
                f"Actual fc = 1/(2π·{resolved_r:.6g}·{resolved_c:.6e}) = {actual_fc:.2f} Hz"
            ]

            return {
                "resistor_ohms": resolved_r,
                "capacitor_farads": resolved_c,
                "resistor_display": format_resistor(resolved_r),
                "capacitor_display": format_capacitor(resolved_c),
                "transfer_function": f"H(s) = 1/(1+sRC) where RC={resolved_r*resolved_c:.6e}",
                "cutoff_frequency": actual_fc,
                "time_constant": resolved_r * resolved_c,
                "output_voltage": voltage_value,
                "derivation": derivation
            }

        capacitor_options = [1e-9, 10e-9, 100e-9, 1e-6, 10e-6]
        best_error = float('inf')
        best_design = None
        
        for target_c in capacitor_options:
            target_r = 1 / (2 * math.pi * cutoff_frequency * target_c)
            
            if target_r < 100 or target_r > 10e6:
                continue
            
            r_value, r_display = find_closest_e24_resistor(target_r)
            actual_fc = 1 / (2 * math.pi * r_value * target_c)
            error = abs(actual_fc - cutoff_frequency) / cutoff_frequency
            
            if error < best_error:
                best_error = error
                best_design = {
                    "r_value": r_value,
                    "r_display": r_display,
                    "c_value": target_c,
                    "actual_fc": actual_fc,
                    "target_r": target_r
                }
        
        if best_design is None:
            raise ValueError(f"Cannot design filter for {cutoff_frequency} Hz")
        
        r_value = best_design["r_value"]
        r_display = best_design["r_display"]
        target_c = best_design["c_value"]
        actual_fc = best_design["actual_fc"]
        
        derivation = [
            f"RC Low-Pass Filter: fc = 1/(2πRC)",
            f"Target cutoff: {cutoff_frequency} Hz",
            f"Chosen C = {format_capacitor(target_c)}",
            f"Solved R = 1/(2π·fc·C) = {best_design['target_r']:.2f} Ω",
            f"Nearest E24 resistor: {r_display}",
            f"Actual fc = 1/(2π·{r_value:.0f}·{target_c:.2e}) = {actual_fc:.2f} Hz"
        ]
        
        return {
            "resistor_ohms": r_value,
            "capacitor_farads": target_c,
            "resistor_display": r_display,
            "capacitor_display": format_capacitor(target_c),
            "transfer_function": f"H(s) = 1/(1+sRC) where RC={r_value*target_c:.6e}",
            "cutoff_frequency": actual_fc,
            "time_constant": r_value * target_c,
            "output_voltage": voltage_value,
            "derivation": derivation
        }
    
    @staticmethod
    def design_rc_high_pass(
        cutoff_frequency: float,
        voltage_value: float,
        resistor_ohms: float = None,
        capacitor_farads: float = None
    ) -> Dict:
        """Design RC high-pass filter"""
        resolved_r, resolved_c, notes = DeterministicDesign._derive_rc_values(
            cutoff_frequency=cutoff_frequency,
            resistor_ohms=resistor_ohms,
            capacitor_farads=capacitor_farads
        )

        if resolved_r and resolved_c:
            actual_fc = 1 / (2 * math.pi * resolved_r * resolved_c)
            derivation = [
                f"RC High-Pass Filter: fc = 1/(2πRC)",
                f"Target cutoff: {cutoff_frequency} Hz",
                *notes,
                f"Resistor R = {format_resistor(resolved_r)}",
                f"Capacitor C = {format_capacitor(resolved_c)}",
                f"Actual fc = 1/(2π·{resolved_r:.6g}·{resolved_c:.6e}) = {actual_fc:.2f} Hz"
            ]

            return {
                "resistor_ohms": resolved_r,
                "capacitor_farads": resolved_c,
                "resistor_display": format_resistor(resolved_r),
                "capacitor_display": format_capacitor(resolved_c),
                "transfer_function": f"H(s) = sRC/(1+sRC)",
                "cutoff_frequency": actual_fc,
                "time_constant": resolved_r * resolved_c,
                "output_voltage": voltage_value,
                "derivation": derivation
            }

        capacitor_options = [1e-9, 10e-9, 100e-9, 1e-6, 10e-6]
        best_error = float('inf')
        best_design = None
        
        for target_c in capacitor_options:
            target_r = 1 / (2 * math.pi * cutoff_frequency * target_c)
            
            if target_r < 100 or target_r > 10e6:
                continue
            
            r_value, r_display = find_closest_e24_resistor(target_r)
            actual_fc = 1 / (2 * math.pi * r_value * target_c)
            error = abs(actual_fc - cutoff_frequency) / cutoff_frequency
            
            if error < best_error:
                best_error = error
                best_design = {
                    "r_value": r_value,
                    "r_display": r_display,
                    "c_value": target_c,
                    "actual_fc": actual_fc,
                    "target_r": target_r
                }
        
        if best_design is None:
            raise ValueError(f"Cannot design filter for {cutoff_frequency} Hz")
        
        r_value = best_design["r_value"]
        r_display = best_design["r_display"]
        target_c = best_design["c_value"]
        actual_fc = best_design["actual_fc"]
        
        derivation = [
            f"RC High-Pass Filter: fc = 1/(2πRC)",
            f"Target cutoff: {cutoff_frequency} Hz",
            f"Chosen C = {format_capacitor(target_c)}",
            f"Solved R = {best_design['target_r']:.2f} Ω",
            f"Nearest E24 resistor: {r_display}",
            f"Actual fc = {actual_fc:.2f} Hz"
        ]
        
        return {
            "resistor_ohms": r_value,
            "capacitor_farads": target_c,
            "resistor_display": r_display,
            "capacitor_display": format_capacitor(target_c),
            "transfer_function": f"H(s) = sRC/(1+sRC)",
            "cutoff_frequency": actual_fc,
            "time_constant": r_value * target_c,
            "output_voltage": voltage_value,
            "derivation": derivation
        }
    
    @staticmethod
    def design_rc_charging(
        time_duration: float,
        voltage_value: float,
        resistor_ohms: float = None,
        capacitor_farads: float = None
    ) -> Dict:
        """Design RC charging circuit: τ = RC"""
        tau = time_duration
        resolved_r, resolved_c, notes = DeterministicDesign._derive_rc_values(
            time_duration=time_duration,
            resistor_ohms=resistor_ohms,
            capacitor_farads=capacitor_farads
        )

        if resolved_r and resolved_c:
            r_value = resolved_r
            target_c = resolved_c
            r_display = format_resistor(r_value)
        else:
            target_r = 10e3  # Start with 10kΩ
            r_value, r_display = find_closest_e24_resistor(target_r)
            target_c = tau / r_value
            notes = ["Using auto-selected resistor and solving for capacitor from τ = RC"]

        actual_tau = r_value * target_c
        
        derivation = [
            f"RC Charging Circuit: τ = RC",
            f"Target time constant: {time_duration} seconds",
            *notes,
            f"Chosen R = {r_display}",
            f"Solved C = τ/R = {target_c:.6e} F",
            f"C = {format_capacitor(target_c)}",
            f"Actual τ = {actual_tau:.6f} seconds"
        ]
        
        return {
            "resistor_ohms": r_value,
            "capacitor_farads": target_c,
            "resistor_display": r_display,
            "capacitor_display": format_capacitor(target_c),
            "transfer_function": f"V_c(t) = V_in(1 - e^(-t/τ)), τ={actual_tau:.6f}s",
            "time_constant": actual_tau,
            "output_voltage": voltage_value,
            "derivation": derivation
        }
    
    @staticmethod
    def design_non_inverting_opamp(
        gain_setting: float = 10.0,
        cutoff_frequency: float = None,
        input_voltage: float = None,
        resistor_1_ohms: float = None,
        resistor_2_ohms: float = None
    ) -> Dict:
        """Non-inverting op-amp with optional lowpass filter: Gain = 1 + Rf/Rin, fc = 1/(2πRC)"""
        if resistor_1_ohms and resistor_2_ohms:
            rin = resistor_1_ohms
            rf_value = resistor_2_ohms
            target_rf = rf_value
            rf_display = format_resistor(rf_value)
            rin_display = format_resistor(rin)
            source_note = "Using user-provided R1/R2 values"
        else:
            rin = 1000  # 1kΩ
            target_rf = (gain_setting - 1) * rin
            rf_value, rf_display = find_closest_e24_resistor(target_rf)
            rin_display = f"{rin / 1e3:.1f}kΩ"
            source_note = "Using auto-selected E24 values from target gain"

        actual_gain = 1 + rf_value / rin
        vin = input_voltage if input_voltage is not None else 1.0
        vout = actual_gain * vin
        
        derivation = [
            f"Non-Inverting Op-Amp: Gain = 1 + Rf/Rin",
            source_note,
            f"Target gain: {gain_setting}",
            f"Chosen Rin = {rin_display}",
            f"Solved Rf = (Gain - 1)·Rin = {target_rf:.2f} Ω",
            f"Nearest E24 Rf = {rf_display}",
            f"Actual gain = 1 + {rf_value:.0f}/{rin} = {actual_gain:.4f}"
        ]
        
        result = {
            "resistor_ohms": rin,
            "resistor_ohms_2": rf_value,
            "capacitor_farads": None,
            "resistor_display": rin_display,
            "resistor_display_2": rf_display,
            "capacitor_display": None,
            "gain": actual_gain,
            "transfer_function": f"V_out = {actual_gain:.4f}·V_in",
            "input_voltage": vin,
            "output_voltage": vout,
            "derivation": derivation
        }
        
        # Add lowpass filter if cutoff frequency is specified
        if cutoff_frequency is not None and cutoff_frequency > 0:
            capacitor_options = [1e-9, 10e-9, 100e-9, 1e-6, 10e-6]
            best_error = float('inf')
            best_filter_design = None
            
            for target_c in capacitor_options:
                target_r = 1 / (2 * math.pi * cutoff_frequency * target_c)
                
                if target_r < 100 or target_r > 10e6:
                    continue
                
                r_value, r_display = find_closest_e24_resistor(target_r)
                actual_fc = 1 / (2 * math.pi * r_value * target_c)
                error = abs(actual_fc - cutoff_frequency) / cutoff_frequency
                
                if error < best_error:
                    best_error = error
                    best_filter_design = {
                        "r_value": r_value,
                        "r_display": r_display,
                        "c_value": target_c,
                        "actual_fc": actual_fc
                    }
            
            if best_filter_design is not None:
                result["filter_resistor_ohms"] = best_filter_design["r_value"]
                result["filter_capacitor_farads"] = best_filter_design["c_value"]
                result["filter_resistor_display"] = best_filter_design["r_display"]
                result["filter_capacitor_display"] = format_capacitor(best_filter_design["c_value"])
                result["cutoff_frequency"] = best_filter_design["actual_fc"]
                result["output_voltage"] = vout
                result["transfer_function"] = f"H(s) = {actual_gain:.4f}/(1+sRC) where fc = {best_filter_design['actual_fc']:.2f} Hz"
                
                derivation.extend([
                    f"",
                    f"Lowpass Filter: fc = 1/(2πRC)",
                    f"Target fc = {cutoff_frequency} Hz",
                    f"RC Network: R_filter = {best_filter_design['r_display']}, C_filter = {result['filter_capacitor_display']}",
                    f"Actual fc = {best_filter_design['actual_fc']:.2f} Hz"
                ])
        
        return result
    
    @staticmethod
    def design_inverting_opamp(
        gain_setting: float = 10.0,
        cutoff_frequency: float = None,
        input_voltage: float = None,
        resistor_1_ohms: float = None,
        resistor_2_ohms: float = None
    ) -> Dict:
        """Inverting op-amp with optional lowpass filter: Gain = -Rf/Rin, fc = 1/(2πRC)"""
        if resistor_1_ohms and resistor_2_ohms:
            rin = resistor_1_ohms
            rf_value = resistor_2_ohms
            target_rf = rf_value
            rf_display = format_resistor(rf_value)
            rin_display = format_resistor(rin)
            source_note = "Using user-provided R1/R2 values"
        else:
            rin = 1000
            target_rf = abs(gain_setting) * rin
            rf_value, rf_display = find_closest_e24_resistor(target_rf)
            rin_display = f"{rin / 1e3:.1f}kΩ"
            source_note = "Using auto-selected E24 values from target gain"

        actual_gain = -rf_value / rin
        vin = input_voltage if input_voltage is not None else 1.0
        vout = actual_gain * vin
        
        derivation = [
            f"Inverting Op-Amp: Gain = -Rf/Rin",
            source_note,
            f"Target gain magnitude: {abs(gain_setting)}",
            f"Chosen Rin = {rin_display}",
            f"Solved Rf = {target_rf:.2f} Ω",
            f"Nearest E24 Rf = {rf_display}",
            f"Actual gain = -{rf_value:.0f}/{rin} = {actual_gain:.4f}"
        ]
        
        result = {
            "resistor_ohms": rin,
            "resistor_ohms_2": rf_value,
            "capacitor_farads": None,
            "resistor_display": rin_display,
            "resistor_display_2": rf_display,
            "capacitor_display": None,
            "gain": actual_gain,
            "transfer_function": f"V_out = {actual_gain:.4f}·V_in",
            "input_voltage": vin,
            "output_voltage": vout,
            "derivation": derivation
        }
        
        # Add lowpass filter if cutoff frequency is specified
        if cutoff_frequency is not None and cutoff_frequency > 0:
            capacitor_options = [1e-9, 10e-9, 100e-9, 1e-6, 10e-6]
            best_error = float('inf')
            best_filter_design = None
            
            for target_c in capacitor_options:
                target_r = 1 / (2 * math.pi * cutoff_frequency * target_c)
                
                if target_r < 100 or target_r > 10e6:
                    continue
                
                r_value, r_display = find_closest_e24_resistor(target_r)
                actual_fc = 1 / (2 * math.pi * r_value * target_c)
                error = abs(actual_fc - cutoff_frequency) / cutoff_frequency
                
                if error < best_error:
                    best_error = error
                    best_filter_design = {
                        "r_value": r_value,
                        "r_display": r_display,
                        "c_value": target_c,
                        "actual_fc": actual_fc
                    }
            
            if best_filter_design is not None:
                result["filter_resistor_ohms"] = best_filter_design["r_value"]
                result["filter_capacitor_farads"] = best_filter_design["c_value"]
                result["filter_resistor_display"] = best_filter_design["r_display"]
                result["filter_capacitor_display"] = format_capacitor(best_filter_design["c_value"])
                result["cutoff_frequency"] = best_filter_design["actual_fc"]
                result["output_voltage"] = vout
                result["transfer_function"] = f"H(s) = {actual_gain:.4f}/(1+sRC) where fc = {best_filter_design['actual_fc']:.2f} Hz"
                
                derivation.extend([
                    f"",
                    f"Lowpass Filter: fc = 1/(2πRC)",
                    f"Target fc = {cutoff_frequency} Hz",
                    f"RC Network: R_filter = {best_filter_design['r_display']}, C_filter = {result['filter_capacitor_display']}",
                    f"Actual fc = {best_filter_design['actual_fc']:.2f} Hz"
                ])
        
        return result
    
    @staticmethod
    def design_opamp_active_filter(cutoff_frequency: float, gain_setting: float = 1.0, is_inverting: bool = False, capacitor_farads: float = None) -> Dict:
        """Active op-amp LPF transimpedance filter: Rin input, R2||C feedback
        
        Args:
            cutoff_frequency: Target cutoff frequency in Hz
            gain_setting: Gain magnitude (typically 1.0 or higher)
            is_inverting: True for inverting config, False for non-inverting
            capacitor_farads: Optional capacitor value in Farads (if None, will be calculated)
        """
        # Design feedback RC network: fc = 1/(2π R2 C)
        if capacitor_farads:
            # User provided a specific capacitor value
            target_c = capacitor_farads
            target_r2 = 1 / (2 * math.pi * cutoff_frequency * target_c)
            r2_value, r2_display = find_closest_e24_resistor(target_r2)
            actual_fc = 1 / (2 * math.pi * r2_value * target_c)
            best_design = {
                "r2_value": r2_value,
                "r2_display": r2_display,
                "cf_value": target_c,
                "actual_fc": actual_fc
            }
        else:
            # Search through standard capacitor values to find best match
            capacitor_options = [1e-9, 10e-9, 100e-9, 1e-6, 10e-6]
            best_error = float('inf')
            best_design = None
            
            for target_c in capacitor_options:
                target_r2 = 1 / (2 * math.pi * cutoff_frequency * target_c)
                
                if target_r2 < 100 or target_r2 > 10e6:
                    continue
                
                r2_value, r2_display = find_closest_e24_resistor(target_r2)
                actual_fc = 1 / (2 * math.pi * r2_value * target_c)
                error = abs(actual_fc - cutoff_frequency) / cutoff_frequency
                
                if error < best_error:
                    best_error = error
                    best_design = {
                        "r2_value": r2_value,
                        "r2_display": r2_display,
                        "cf_value": target_c,
                        "actual_fc": actual_fc
                    }
            
            if best_design is None:
                raise ValueError(f"Cannot design filter for {cutoff_frequency} Hz")
        
        # Input resistor
        r1 = 10000  # 10kΩ input resistor
        r2_value = best_design["r2_value"]
        
        # Gain from transimpedance: |H| = R2/R1
        actual_gain = abs(r2_value / r1)
        
        if is_inverting:
            config_name = "Inverting"
            transfer_fn = f"H(s) = -{actual_gain:.4f}/(1 + sR2Cf)"
        else:
            config_name = "Non-Inverting"
            transfer_fn = f"H(s) = +{actual_gain:.4f}/(1 + sR2Cf)"
        
        derivation = [
            f"Active Op-Amp {config_name} LPF (Transimpedance):",
            f"Input Resistor (R1) = 10.0kΩ",
            f"Feedback: R2 = {best_design['r2_display']}, Cf = {format_capacitor(best_design['cf_value'])}",
            f"Cutoff Frequency: fc = 1/(2π R2 Cf) = {best_design['actual_fc']:.2f} Hz",
            f"Gain: |H| = R2/R1 = {actual_gain:.4f}"
        ]
        
        return {
            "resistor_ohms": r1,
            "resistor_ohms_2": r2_value,
            "capacitor_farads": best_design["cf_value"],
            "resistor_display": "10.0kΩ",
            "resistor_display_2": best_design["r2_display"],
            "capacitor_display": format_capacitor(best_design["cf_value"]),
            "gain": actual_gain if not is_inverting else -actual_gain,
            "transfer_function": transfer_fn,
            "cutoff_frequency": best_design["actual_fc"],
            "time_constant": r2_value * best_design["cf_value"],
            "derivation": derivation
        }
    @staticmethod
    def design_linear_regulator_with_bridge_rectifier(
        input_ac_voltage: float,
        output_voltage: float,
        load_current: float,
        dropout_voltage: float = 0.2,
        ripple_voltage: float = 0.5,
        line_frequency_hz: float = 60.0,
        diode_forward_voltage: float = 0.7,
        primary_voltage_rms: float = None,
        secondary_voltage_rms: float = None,
        transformer_turns_ratio: float = None
    ) -> Dict:
        """
        Design a linear regulator with full bridge rectifier.
        
        Components:
        - Transformer (step-down AC)
        - Full bridge rectifier (4 diodes)
        - Filter capacitor
        - Linear regulator IC (LM7805, etc)
        - Optional bypass capacitors for stability
        
        Args:
            input_ac_voltage: AC input voltage (RMS)
            output_voltage: Desired DC output voltage
            load_current: Maximum load current in Amperes
            dropout_voltage: Regulator dropout voltage (typically 0.2-2V)
            ripple_voltage: Allowable ripple voltage at filter output
        """
        # Step 1: Calculate required peak voltage after rectifier
        # For full bridge: V_peak = V_ac_rms * sqrt(2) - 2*V_diode_drop
        secondary_rms = secondary_voltage_rms if secondary_voltage_rms is not None else input_ac_voltage
        primary_rms = primary_voltage_rms
        if primary_rms is None and transformer_turns_ratio:
            primary_rms = secondary_rms * transformer_turns_ratio
        v_primary_peak = primary_rms * math.sqrt(2) if primary_rms is not None else None
        v_secondary_peak = secondary_rms * math.sqrt(2)
        v_peak = v_secondary_peak - 2 * diode_forward_voltage
        
        # Step 2: Required input voltage to regulator (must account for ripple and dropout)
        v_required = output_voltage + dropout_voltage + ripple_voltage / 2
        
        # Step 3: Calculate filter capacitor
        # Ripple voltage: V_ripple = I_load / (f * C)
        # Standard AC frequency: 50/60 Hz, full-wave rectified = 100/120 Hz
        rectifier_frequency = line_frequency_hz * 2
        tb_seconds = 0.75 / rectifier_frequency
        period_seconds = 1 / rectifier_frequency
        tc_seconds = period_seconds - tb_seconds
        filter_capacitor = (load_current * tb_seconds) / ripple_voltage
        
        # Standard capacitor values
        capacitor_options = [1000e-6, 2200e-6, 4700e-6, 10000e-6]
        filter_cap = min(capacitor_options, key=lambda x: abs(x - filter_capacitor))
        v_filtered_no_load = v_peak
        v_filtered_avg = v_peak - (ripple_voltage / 2)
        v_filtered_min = v_peak - ripple_voltage
        v_zero_to_peak = ripple_voltage / 2
        piv_estimate = v_peak
        
        # Step 4: Select regulator IC (e.g., LM7805 for 5V)
        regulator_name = f"LM78{int(output_voltage):02d}"  # LM7805, LM7812, etc
        
        # Step 5: Standard linear regulators do not require an external series
        # resistor or zener clamp in the main power path. The regulator IC
        # provides the control loop and current limiting.
        series_r_value = 0.0
        series_r_display = "Not required"
        power_dissipation = 0.0

        # Step 6: Compatibility placeholders for existing response fields
        zener_voltage = output_voltage
        zener_current = 0.0
        regulator_power = max(v_filtered_avg - output_voltage, 0.0) * load_current
        
        derivation = [
            f"Linear Regulator with Full Bridge Rectifier Design",
            f"",
            f"STEP 1: Transformer / Rectifier Labels",
            f"  Vpri,rms = {primary_rms:.2f}V" if primary_rms is not None else f"  Vpri,rms = not specified",
            f"  Vpri,peak = √2 × Vpri,rms = {v_primary_peak:.2f}V" if v_primary_peak is not None else f"  Vpri,peak = not specified",
            f"  N = Npri / Nsec = {transformer_turns_ratio:.3f}" if transformer_turns_ratio is not None else f"  N = not specified",
            f"  Vsec,rms = {secondary_rms:.2f}V",
            (
                f"  Vsec,peak = Vpri,peak / N = √2 × Vpri,rms / N = {v_secondary_peak:.2f}V"
                if v_primary_peak is not None and transformer_turns_ratio is not None
                else f"  Vsec,peak = √2 × Vsec,rms = {v_secondary_peak:.2f}V"
            ),
            f"",
            f"STEP 2: Capacitor Sizing",
            f"  fline = {line_frequency_hz:.2f}Hz",
            f"  frect = 2 × fline = {rectifier_frequency:.2f}Hz",
            f"  T = 1 / frect = {period_seconds * 1000:.2f}ms",
            f"  Tb = 0.75 × T = {tb_seconds * 1000:.2f}ms",
            f"  Tc = T - Tb = {tc_seconds * 1000:.2f}ms",
            f"  IFL = {load_current:.3f}A",
            f"  VPP = {ripple_voltage:.3f}V",
            f"  VOP = VPP / 2 = {v_zero_to_peak:.3f}V",
            f"  C = (IFL × Tb) / Vpp = ({load_current:.3f} × {tb_seconds:.6f}) / {ripple_voltage:.3f}",
            f"  Calculated C = {filter_capacitor * 1e6:.0f}µF",
            f"  Selected C = {filter_cap * 1e6:.0f}µF",
            f"",
            f"STEP 3: Filter Capacitor Voltages",
            f"  VCF-HL-NL = Vsec,peak - 2VD = {v_secondary_peak:.2f} - 2({diode_forward_voltage:.2f}) = {v_filtered_no_load:.2f}V",
            f"  VDC = Vsec,peak - 2VD - VOP = {v_secondary_peak:.2f} - 2({diode_forward_voltage:.2f}) - {v_zero_to_peak:.3f} = {v_filtered_avg:.2f}V",
            f"  VCF-HL-FL = Vsec,peak - 2VD - VPP/2 = {v_secondary_peak:.2f} - 2({diode_forward_voltage:.2f}) - {ripple_voltage:.3f}/2 = {v_filtered_avg:.2f}V",
            f"  VTR = VTROUGH = VCF,min = Vsec,peak - 2VD - VPP = {v_secondary_peak:.2f} - 2({diode_forward_voltage:.2f}) - {ripple_voltage:.3f} = {v_filtered_min:.2f}V",
            f"  PIV ≈ Vsec,peak - 2VD = {piv_estimate:.2f}V",
            f"",
            f"STEP 4: Required Input to Regulator",
            f"  Output Voltage: {output_voltage}V",
            f"  Dropout Voltage: {dropout_voltage}V",
            f"  Ripple Voltage: ±{ripple_voltage/2:.2f}V",
            f"  Required Input: {v_required:.2f}V = {output_voltage} + {dropout_voltage} + {ripple_voltage/2:.2f}",
            f"",
            f"STEP 5: Regulator IC Selection",
            f"  Output Voltage: {output_voltage}V",
            f"  Typical IC: {regulator_name} (up to 1-1.5A)",
            f"",
            f"STEP 6: Linear Regulator Stage",
            f"  Regulator IC: {regulator_name}",
            f"  Required Input to Regulator: {v_required:.2f}V",
            f"  Available Nominal Input: {v_filtered_avg:.2f}V",
            f"  Headroom: {v_filtered_avg - v_required:.2f}V",
            f"  Standard external series resistor: not required",
            f"",
            f"STEP 7: Regulation and Dissipation",
            f"  Output regulated at: {output_voltage:.2f}V",
            f"  Estimated regulator dissipation: {regulator_power:.2f}W",
            f"  Zener placeholder value: {zener_voltage:.1f}V (not used in main power path)",
            f"  Zener placeholder current: {zener_current:.3f}A",
            f"",
            f"COMPONENTS SUMMARY:",
            f"  • Transformer: {secondary_rms:.2f}VAC secondary feeding bridge rectifier",
            f"  • Full Bridge Rectifier: 4× 1N4007 diodes (1A, 1000V)",
            f"  • Filter Capacitor: {filter_cap*1e6:.0f}µF, voltage rating ≥ {int(v_peak)+5}V",
            f"  • Series Resistor: {series_r_display}",
            f"  • Regulator IC: {regulator_name}",
            f"  • Zener Diode: not required for standard linear regulation",
            f"  • Input Bypass Cap: 0.1µF (optional, recommended)",
            f"  • Output Bypass Cap: 0.1µF (for stability)",
        ]
        
        return {
            "series_resistor_ohms": series_r_value,
            "series_resistor_display": series_r_display,
            "filter_capacitor_farads": filter_cap,
            "filter_capacitor_display": format_capacitor(filter_cap),
            "zener_voltage": zener_voltage,
            "zener_current": zener_current,
            "peak_input_voltage": v_peak,
            "output_voltage": output_voltage,
            "load_current": load_current,
            "dropout_voltage": dropout_voltage,
            "ripple_voltage": ripple_voltage,
            "primary_voltage_rms": primary_rms,
            "secondary_voltage_rms": secondary_rms,
            "transformer_turns_ratio": transformer_turns_ratio,
            "line_frequency_hz": line_frequency_hz,
            "diode_forward_voltage": diode_forward_voltage,
            "regulator_power_dissipation": regulator_power,
            "transfer_function": f"VCF-HL-FL = Vsec,peak - 2VD - Vpp/2 = {v_filtered_avg:.2f}V",
            "derivation": derivation
        }
    
    @staticmethod
    def design_zener_regulator_with_bridge_rectifier(
        input_ac_voltage: float,
        output_voltage: float,
        load_resistance: float,
        min_zener_current: float = 5.0,
        series_resistor_ohms: float = None,
        filter_capacitor_farads: float = None,
        line_frequency_hz: float = 60.0,
        diode_forward_voltage: float = 0.7,
        primary_voltage_rms: float = None,
        secondary_voltage_rms: float = None,
        transformer_turns_ratio: float = None
    ) -> Dict:
        """Design Zener shunt regulator with full bridge rectifier
        
        A zener regulator uses a zener diode in parallel with the load
        to maintain constant output voltage. The series resistor limits
        current and dissipates excess power.
        """
        
        # Constants
        rectifier_frequency = line_frequency_hz * 2  # Full-wave rectification
        
        # Peak voltage after rectification (full bridge)
        v_peak = input_ac_voltage * math.sqrt(2) - 2 * diode_forward_voltage
        
        # Select standard filter capacitor (assuming 0.5V ripple)
        ripple_voltage = 0.5
        estimated_load_current = output_voltage / load_resistance
        filter_capacitor = estimated_load_current / (rectifier_frequency * ripple_voltage)
        filter_cap_options = [1000e-6, 2200e-6, 4700e-6, 10000e-6]
        if filter_capacitor_farads is not None and filter_capacitor_farads > 0:
            filter_cap = filter_capacitor_farads
        else:
            filter_cap = min(filter_cap_options, key=lambda x: abs(x - filter_capacitor))
        
        # Approximate filtered DC (with ripple)
        v_filtered_avg = v_peak - (ripple_voltage / 2)
        
        # Zener selection - standard values
        zener_voltage = output_voltage
        zener_options = [3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1, 10, 12, 15, 18]
        zener_voltage = min(zener_options, key=lambda x: abs(x - output_voltage))
        
        # Calculate series resistor for regulated current
        # Rs must limit maximum current: Rs = (V_in - V_out) / I_max
        max_output_current = estimated_load_current * 1.5  # Safety margin
        min_input_voltage = v_filtered_avg - (ripple_voltage / 2)  # Worst case
        
        series_r = (min_input_voltage - zener_voltage) / max_output_current
        if series_resistor_ohms is not None and series_resistor_ohms > 0:
            series_r_value = series_resistor_ohms
            series_r_display = format_resistor(series_r_value)
        else:
            series_r_value, series_r_display = find_closest_e24_resistor(series_r)
        
        # Operating point analysis
        # At no load: Iz_max = (Vin - Vz) / Rs
        v_supply_nominal = v_filtered_avg
        i_z_max = (v_supply_nominal - zener_voltage) / series_r_value
        i_z_min_mA = min_zener_current
        
        # At full load: Iz_min must be positive for regulation
        i_load_max = (v_supply_nominal - zener_voltage) / series_r_value - (min_zener_current / 1000)
        
        # Actual load resistance (might differ)
        i_load_actual = estimated_load_current
        i_z_actual = (v_supply_nominal - zener_voltage) / series_r_value - i_load_actual
        
        # Power dissipation in zener (worst case at no load)
        p_z = zener_voltage * i_z_max * 1000  # Convert to mW
        
        # Power dissipation in series resistor
        i_total_max = (v_supply_nominal - zener_voltage) / series_r_value
        p_series = (i_total_max ** 2) * series_r_value
        
        # Zener diode power rating selection
        zener_power_mW = 500 if p_z < 400 else (1000 if p_z < 800 else 2000)
        zener_model = "1N4733A" if zener_voltage == 5.1 else f"1N474{int(zener_voltage)}"
        
        derivation = [
            f"Zener Shunt Regulator with Full Bridge Rectifier Design",
            f"",
            f"STEP 1: Rectifier & Filter",
            f"  AC Input (RMS): {input_ac_voltage}V",
            f"  Primary Voltage (RMS): {primary_voltage_rms if primary_voltage_rms is not None else 'not specified'}",
            f"  Secondary Voltage (RMS): {secondary_voltage_rms if secondary_voltage_rms is not None else input_ac_voltage}",
            f"  Transformer Turns Ratio: {transformer_turns_ratio if transformer_turns_ratio is not None else 'not specified'}",
            f"  Line Frequency: {line_frequency_hz}Hz",
            f"  Peak Voltage: {v_peak:.2f}V = {input_ac_voltage}×√2 - 2×{diode_forward_voltage}V",
            f"  Ripple Voltage: ±{ripple_voltage/2:.2f}V",
            f"  Filtered DC (avg): {v_filtered_avg:.2f}V",
            f"  Filter Capacitor: {format_capacitor(filter_cap)}" + (" (user override)" if filter_capacitor_farads is not None and filter_capacitor_farads > 0 else ""),
            f"",
            f"STEP 2: Load Analysis",
            f"  Load Resistance: {load_resistance}Ω",
            f"  Nominal Load Current: {i_load_actual:.3f}A",
            f"",
            f"STEP 3: Zener Diode Selection",
            f"  Output Voltage Target: {output_voltage}V",
            f"  Selected Zener Voltage: {zener_voltage}V",
            f"  Zener Model: {zener_model} ({zener_power_mW}mW)",
            f"  Minimum Zener Current: {min_zener_current}mA (for stable regulation)",
            f"",
            f"STEP 4: Series Resistor Sizing",
            f"  Required series resistor limits current flow",
            f"  Rs = (V_supply - V_zener) / I_max",
            f"  Rs = ({v_supply_nominal:.2f} - {zener_voltage}) / {max_output_current:.3f}A",
            f"  Calculated: {series_r:.2f}Ω",
            f"  Selected: {series_r_display}" + (" (user override)" if series_resistor_ohms is not None and series_resistor_ohms > 0 else " (E24)"),
            f"",
            f"STEP 5: Operating Point at Nominal",
            f"  Supply Current: {i_total_max:.3f}A",
            f"  Load Current: {i_load_actual:.3f}A",
            f"  Zener Current: {i_z_actual:.3f}A",
            f"",
            f"STEP 6: Power Dissipation",
            f"  Series Resistor Power: {p_series:.2f}W (use {max(2, math.ceil(p_series))}W resistor)",
            f"  Zener Power (worst case): {p_z:.0f}mW (use {zener_power_mW}mW rating)",
            f"  Note: Worst case at no load when all current flows through zener",
            f"",
            f"STEP 7: Regulation Quality",
            f"  Zener Current Range: {min_zener_current}mA to {i_z_max*1000:.0f}mA",
            f"  Output Voltage Ripple: ±{ripple_voltage/2:.2f}V",
            f"  Load Regulation: Fair (±2-5% typical)",
            f"",
            f"COMPONENTS SUMMARY:",
            f"  • Transformer: {input_ac_voltage}VAC → {output_voltage + 3}VDC (center-tapped recommended)",
            f"  • Full Bridge Rectifier: 4× 1N4007 diodes (1A, 1000V)",
            f"  • Filter Capacitor: {format_capacitor(filter_cap)}, voltage ≥ {int(v_peak)+5}V",
            f"  • Series Resistor: {series_r_display}, {max(2, math.ceil(p_series))}W",
            f"  • Zener Diode: {zener_model} ({zener_voltage}V, {zener_power_mW}mW)",
            f"  • Bypass Capacitor (optional): 0.1µF on output for noise filtering",
        ]
        
        return {
            "zener_diode_voltage": zener_voltage,
            "zener_diode_power": zener_power_mW,
            "series_resistor_value": series_r_value,
            "series_resistor_display": series_r_display,
            "series_resistor_power": p_series,
            "input_voltage": input_ac_voltage,
            "load_resistor_value": load_resistance,
            "filter_capacitor_farads": filter_cap,
            "filter_capacitor_display": format_capacitor(filter_cap),
            "peak_input_voltage": v_peak,
            "no_load_current": i_z_max,
            "full_load_current": i_z_actual,
            "output_voltage": zener_voltage,
            "primary_voltage_rms": primary_voltage_rms,
            "secondary_voltage_rms": secondary_voltage_rms if secondary_voltage_rms is not None else input_ac_voltage,
            "transformer_turns_ratio": transformer_turns_ratio,
            "line_frequency_hz": line_frequency_hz,
            "diode_forward_voltage": diode_forward_voltage,
            "transfer_function": f"Zener Shunt Regulation: {zener_voltage}V (regulated)",
            "derivation": derivation
        }
