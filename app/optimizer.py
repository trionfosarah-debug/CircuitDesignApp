"""Component optimization for practical value selection"""
import math


class ComponentOptimizer:
    """Suggests practical E24 resistor and standard capacitor values while maintaining target specs"""
    
    # E24 preferred resistor series (5% tolerance)
    E24_SERIES = [
        10, 11, 12, 13, 15, 16, 18, 20, 22, 24, 27, 30, 33, 36, 39, 43, 47, 51, 56, 62, 68, 75, 82, 91
    ]
    
    # Standard capacitor values (µF range)
    STANDARD_CAPS = [
        1e-9, 2.2e-9, 4.7e-9, 10e-9, 22e-9, 47e-9, 100e-9, 220e-9, 470e-9,  # nF
        1e-6, 2.2e-6, 4.7e-6, 10e-6, 22e-6, 47e-6, 100e-6, 220e-6, 470e-6,
        1000e-6, 2200e-6, 4700e-6, 10000e-6  # µF
    ]
    
    @staticmethod
    def get_e24_resistors_in_range(min_r: float, max_r: float, decade_limit: int = 10) -> list:
        """Generate E24 series resistors within range (across multiple decades)"""
        resistors = []
        current_decade = 1
        
        while current_decade <= decade_limit:
            for base_value in ComponentOptimizer.E24_SERIES:
                r_value = base_value * current_decade
                if min_r <= r_value <= max_r:
                    resistors.append(r_value)
            current_decade *= 10
        
        return sorted(resistors)
    
    @staticmethod
    def find_closest_e24(target_r: float) -> float:
        """Find closest E24 resistor value"""
        # Generate E24 across range
        min_decade = 10 ** (math.floor(math.log10(target_r)) - 1)
        max_decade = 10 ** (math.floor(math.log10(target_r)) + 2)
        
        resistors = []
        decade = min_decade
        while decade <= max_decade:
            for base in ComponentOptimizer.E24_SERIES:
                resistors.append(base * decade)
            decade *= 10
        
        # Find closest
        return min(resistors, key=lambda x: abs(x - target_r))
    
    @staticmethod
    def find_closest_standard_cap(target_c: float) -> float:
        """Find closest standard capacitor value"""
        return min(ComponentOptimizer.STANDARD_CAPS, key=lambda x: abs(x - target_c))
    
    @staticmethod
    def optimize_for_frequency(
        nominal_r: float,
        nominal_c: float,
        target_fc: float,
        circuit_type: str
    ) -> dict:
        """Optimize R and C to maintain target cutoff frequency with practical values"""
        
        if not target_fc or target_fc <= 0:
            target_fc = 1 / (2 * math.pi * nominal_r * nominal_c)
        
        # Get practical R value
        optimal_r = ComponentOptimizer.find_closest_e24(nominal_r)
        
        # Recalculate C to maintain fc with optimized R
        # fc = 1/(2πRC), so C = 1/(2πRfc)
        needed_c = 1 / (2 * math.pi * optimal_r * target_fc)
        optimal_c = ComponentOptimizer.find_closest_standard_cap(needed_c)
        
        # Verify resulting frequency
        resulting_fc = 1 / (2 * math.pi * optimal_r * optimal_c)
        error_percent = abs(resulting_fc - target_fc) / target_fc * 100
        
        # Format for display
        r_display = ComponentOptimizer._format_resistance(optimal_r)
        c_display = ComponentOptimizer._format_capacitance(optimal_c)
        
        return {
            "resistor_ohms": optimal_r,
            "capacitor_farads": optimal_c,
            "resistor_display": r_display,
            "capacitor_display": c_display,
            "cutoff_frequency": resulting_fc,
            "target_frequency": target_fc,
            "frequency_error_percent": error_percent,
            "optimization_notes": [
                f"Selected practical E24 resistor: {r_display}",
                f"Selected standard capacitor: {c_display}",
                f"Resulting cutoff frequency: {resulting_fc:.2f} Hz",
                f"Frequency error: {error_percent:.2f}%"
            ]
        }
    
    @staticmethod
    def optimize_for_gain(
        nominal_r_feedback: float,
        nominal_r_input: float,
        target_gain: float
    ) -> dict:
        """Optimize feedback and input resistors for op-amp gain by trying multiple standard values"""
        
        # Generate candidate input resistors (from E24 series)
        min_ri = 100  # min 100Ω
        max_ri = 1e6  # max 1MΩ
        candidate_ri = ComponentOptimizer.get_e24_resistors_in_range(min_ri, max_ri, decade_limit=100)
        
        best_error = float('inf')
        best_result = None
        
        # Try each standard input resistor value
        for ri in candidate_ri:
            # Calculate needed feedback resistor for this input resistor
            needed_rf = (target_gain - 1) * ri
            
            # Find closest E24 feedback resistor
            optimal_rf = ComponentOptimizer.find_closest_e24(needed_rf)
            
            # Calculate resulting gain
            resulting_gain = 1 + optimal_rf / ri
            error_percent = abs(resulting_gain - target_gain) / target_gain * 100
            
            # Track best combination
            if error_percent < best_error:
                best_error = error_percent
                best_result = {
                    "resistor_feedback_ohms": optimal_rf,
                    "resistor_input_ohms": ri,
                    "resistor_feedback_display": ComponentOptimizer._format_resistance(optimal_rf),
                    "resistor_input_display": ComponentOptimizer._format_resistance(ri),
                    "gain": resulting_gain,
                    "target_gain": target_gain,
                    "gain_error_percent": error_percent,
                    "optimization_notes": [
                        f"Target Gain: {target_gain}",
                        f"Selected Input Resistor (R1): {ComponentOptimizer._format_resistance(ri)} (E24 standard)",
                        f"Calculated Feedback Resistor (R2): {ComponentOptimizer._format_resistance(optimal_rf)} (E24 standard)",
                        f"Formula: Gain = 1 + R2/R1 = 1 + {optimal_rf}/{ri}",
                        f"Resulting Gain: {resulting_gain:.4f}",
                        f"Gain Accuracy: {100 - error_percent:.2f}% (error: {error_percent:.2f}%)",
                        f"Why these values: Optimized for closest match to target gain using standard E24 resistors"
                    ]
                }
        
        return best_result if best_result else {
            "resistor_feedback_ohms": nominal_r_feedback,
            "resistor_input_ohms": nominal_r_input,
            "resistor_feedback_display": ComponentOptimizer._format_resistance(nominal_r_feedback),
            "resistor_input_display": ComponentOptimizer._format_resistance(nominal_r_input),
            "gain": 1 + nominal_r_feedback / nominal_r_input,
            "target_gain": target_gain,
            "gain_error_percent": 0,
            "optimization_notes": ["No optimization needed"]
        }
    
    @staticmethod
    def _format_resistance(r_ohms: float) -> str:
        """Format resistance with appropriate units"""
        if r_ohms >= 1e6:
            return f"{r_ohms/1e6:.1f} MΩ"
        elif r_ohms >= 1e3:
            return f"{r_ohms/1e3:.1f} kΩ"
        else:
            return f"{r_ohms:.1f} Ω"
    
    @staticmethod
    def _format_capacitance(c_farads: float) -> str:
        """Format capacitance with appropriate units"""
        if c_farads >= 1:
            return f"{c_farads:.3f} F"
        elif c_farads >= 1e-3:
            return f"{c_farads*1e3:.3f} mF"
        elif c_farads >= 1e-6:
            return f"{c_farads*1e6:.3f} µF"
        elif c_farads >= 1e-9:
            return f"{c_farads*1e9:.3f} nF"
        else:
            return f"{c_farads*1e12:.3f} pF"
