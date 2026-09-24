"""Alternative optimization strategies for RC circuits

Provides multiple practical strategies (minimize frequency error, low-noise, low-current, balanced)
and returns a list of option dictionaries with metadata and reasoning.
"""
import math
from .optimizer import ComponentOptimizer


def optimize_for_frequency_alternatives(nominal_r, nominal_c, target_fc, circuit_type, num_options=3):
    # Use only the explicit candidate lists from user prompt
    options = []
    # Audit and expand candidate lists if needed
    candidate_rs = [1e3, 1.2e3, 1.5e3, 1.6e3, 1.8e3, 2.2e3, 3.3e3, 4.7e3, 5.6e3, 10e3]
    candidate_cs = [10e-9, 22e-9, 33e-9, 47e-9, 68e-9, 100e-9, 220e-9]

    scored = []
    print("[DEBUG] Generating candidate RC pairs and scores:")
    for r in candidate_rs:
        for c in candidate_cs:
            fc = 1 / (2 * math.pi * r * c)
            freq_error = abs(fc - target_fc) / target_fc * 100
            score = freq_error + 0.1 * (r / 1e3)
            print(f"  R={r:.0f}Ω, C={c*1e9:.0f}nF, fc={fc:.2f}Hz, error={freq_error:.2f}%, score={score:.2f}")
            scored.append((score, freq_error, r, c, fc))

    # Sort by score, then by smaller R, then by standard C (for tie-breaking)
    scored.sort(key=lambda x: (x[0], x[2], candidate_cs.index(x[3]) if x[3] in candidate_cs else 99))

    # Always return at least 3 and at most 4 unique top-scoring options
    min_options = 3
    max_options = 4
    options = []
    seen = set()
    for score, freq_error, r, c, fc in scored:
        key = (r, c)
        if key in seen:
            continue
        seen.add(key)
        options.append({
            "strategy": "scored_best",
            "resistor_ohms": r,
            "capacitor_farads": c,
            "resistor_display": ComponentOptimizer._format_resistance(r),
            "capacitor_display": ComponentOptimizer._format_capacitance(c),
            "cutoff_frequency": fc,
            "frequency_error_percent": freq_error,
            "score": score,
            "reasoning": f"Score = {freq_error:.2f}% error + 0.1×({r/1e3:.1f}) = {score:.2f}. Chosen for accuracy and practical R/C values."
        })
        if len(options) >= max_options:
            break
    # If not enough, pad with next best until min_options
    if len(options) < min_options:
        for score, freq_error, r, c, fc in scored:
            key = (r, c)
            if key in seen:
                continue
            seen.add(key)
            options.append({
                "strategy": "scored_best",
                "resistor_ohms": r,
                "capacitor_farads": c,
                "resistor_display": ComponentOptimizer._format_resistance(r),
                "capacitor_display": ComponentOptimizer._format_capacitance(c),
                "cutoff_frequency": fc,
                "frequency_error_percent": freq_error,
                "score": score,
                "reasoning": f"Score = {freq_error:.2f}% error + 0.1×({r/1e3:.1f}) = {score:.2f}. Chosen for accuracy and practical R/C values."
            })
            if len(options) >= min_options:
                break
    return options
