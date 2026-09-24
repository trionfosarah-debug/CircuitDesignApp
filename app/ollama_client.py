"""Ollama AI integration for conceptual explanations"""
import requests
from typing import Optional


class OllamaClient:
    """Client for Ollama API - Educational explanations only, no math"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize Ollama client"""
        self.base_url = base_url
        self.model = "llama3"
    
    def explain_circuit_concept(
        self,
        concept: str,
        circuit_type: str,
        context: Optional[str] = None
    ) -> str:
        """Get conceptual explanation from Ollama"""
        try:
            prompt = f"""Explain the following circuit concept for undergraduate electrical engineering students in simple terms (avoid complex math):

Concept: {concept}
Circuit Type: {circuit_type}
Additional Context: {context or "None provided"}

Keep the explanation concise (100-150 words) and educational."""
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("response", "Unable to generate explanation")
            else:
                return f"Ollama service error (status {response.status_code})"
        
        except Exception as e:
            # Return fallback explanation if Ollama is unavailable
            return self._get_fallback_explanation(concept, circuit_type)

    def recommend_optimized_option(self, options: list, circuit_type: str, guidance: Optional[str] = None) -> str:
        """Ask the model to recommend and rank optimized options, sending all RC pairs as a table, per user instructions."""
        try:
            # Build table header and rows for all options
            table_header = "| Option | R (Ω) | C (F) | fc (Hz) | error% | score |\n|---|---|---|---|---|---|"
            table_rows = []
            for i, opt in enumerate(options):
                table_rows.append(
                    f"| {i+1} | {opt.get('resistor_display')} | {opt.get('capacitor_display')} | {opt.get('cutoff_frequency'):.2f} | {opt.get('frequency_error_percent'):.2f} | {opt.get('score'):.2f} |"
                )
            table = table_header + "\n" + "\n".join(table_rows)

            guidance_block = guidance or (
                "Analyze the BEST option (lowest score) using these 4 steps:\n\n"
                "STEP 1: Resistor optimality - thermal noise reduction and signal quality\n"
                "STEP 2: Capacitor optimality - frequency accuracy and settling time calculation\n"
                "STEP 3: Score analysis with comparisons to 2+ alternative options\n"
                "STEP 4: Real-world benefits including power dissipation, availability, and PCB advantages\n\n"
                "Show all calculations with actual numbers from the table. Include formulas and explain your reasoning."
            )

            prompt = f"""{guidance_block}\n\nAll candidate RC combinations:\n{table}\n\nProvide detailed analysis with actual calculations and comparisons."""

            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )

            if response.status_code == 200:
                return response.json().get("response", "No recommendation returned")
            else:
                return f"Ollama service error (status {response.status_code})"

        except Exception:
            return "Model unavailable — no recommendation generated."
    
    def _get_fallback_explanation(self, concept: str, circuit_type: str) -> str:
        """Fallback educational explanations when Ollama is unavailable"""
        
        explanations = {
            ("cutoff_frequency", "RC Low-Pass Filter"): 
                "The cutoff frequency is the frequency at which the filter begins to significantly attenuate the signal. "
                "It's where the output power drops to 50% of the input power. Below this frequency, signals pass through mostly unchanged; "
                "above it, they are increasingly blocked. This frequency depends on both the resistor and capacitor values.",
            
            ("time_constant", "RC Charging"):
                "The time constant (tau) determines how fast the capacitor charges. It's the time it takes for the capacitor "
                "voltage to reach about 63% of the input voltage. A larger time constant means slower charging. "
                "Students can use this to predict circuit behavior without solving differential equations.",
            
            ("gain", "Op-Amp"):
                "Gain is the amplification factor of the op-amp circuit. It tells us how many times the output voltage is larger than "
                "the input voltage. For a gain of 10, a 1V input produces a 10V output. Understanding gain is essential for designing "
                "amplifiers and signal conditioning circuits.",
            
            ("sensitivity", "RC Filter"):
                "Sensitivity analysis shows which components have the most effect on circuit performance. "
                "High sensitivity to a component means that small manufacturing tolerances in that component will cause large changes in performance. "
                "This guides design decisions about component selection and testing requirements.",
            
            ("tolerance", "Component"):
                "Component tolerances represent manufacturing variation. A 1kΩ resistor with 5% tolerance can actually be anywhere from "
                "950Ω to 1050Ω. Worst-case analysis considers extreme tolerances to ensure the circuit still works under all conditions.",
        }
        
        key = (concept.lower(), circuit_type)
        return explanations.get(key, 
            f"Educational explanation for {concept} in {circuit_type}: "
            f"This parameter affects circuit performance and should be understood through simulation and experimentation.")
