from flask import Flask, render_template, request, jsonify
from matlab_generator_clean import MATLABCodeGenerator
import os

app = Flask(__name__, template_folder='../templates', static_folder='../static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate-matlab', methods=['POST'])
def generate_matlab():
    try:
        data = request.json
        code = MATLABCodeGenerator.generate_complete_analysis(
            circuit_type=data.get('circuit_type'),
            resistor_ohms=data.get('resistor_ohms'),
            resistor_ohms_2=data.get('resistor_ohms_2'),
            capacitor_farads=data.get('capacitor_farads'),
            voltage_value=data.get('voltage_value'),
            num_samples=data.get('num_samples', 1000),
            r1_tolerance_percent=data.get('r1_tolerance_percent'),
            r2_tolerance_percent=data.get('r2_tolerance_percent'),
            capacitor_tolerance_percent=data.get('capacitor_tolerance_percent'),
            line_fluctuation_percent=data.get('line_fluctuation_percent'),
            cutoff_frequency=data.get('cutoff_frequency'),
            gain_setting=data.get('gain_setting'),
        )
        return jsonify({'success': True, 'matlab_code': code})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
