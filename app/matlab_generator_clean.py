"""Clean MATLAB code generator used as a safe replacement."""
from typing import Optional


class MATLABCodeGenerator:
    @staticmethod
    def generate_complete_analysis(
        circuit_type: str,
        resistor_ohms: Optional[float],
        resistor_ohms_2: Optional[float],
        capacitor_farads: float,
        voltage_value: float,
        num_samples: int,
        r1_tolerance_percent: float,
        r2_tolerance_percent: Optional[float],
        capacitor_tolerance_percent: float,
        line_fluctuation_percent: float,
        cutoff_frequency: Optional[float] = None,
        gain_setting: Optional[float] = None,
        mc_results: Optional[dict] = None,
        wc_results: Optional[dict] = None,
    ) -> str:
        # Normalize enum/string inputs from backend
        circuit_key = circuit_type.value if hasattr(circuit_type, "value") else str(circuit_type)

        rc_types = ("RC_LOW_PASS", "RC_HIGH_PASS", "RC_CHARGING")

        # Frontend-aligned nominal values
        r1_nom = float(resistor_ohms) if resistor_ohms and resistor_ohms > 0 else 10000.0
        vin_nom = float(voltage_value) if voltage_value is not None else 5.0
        c_nom = float(capacitor_farads) if capacitor_farads and capacitor_farads > 0 else 1e-6
        r1_tol = float(r1_tolerance_percent or 0.0)
        r2_tol = float(r2_tolerance_percent if r2_tolerance_percent is not None else r1_tol)
        vin_tol = float(line_fluctuation_percent or 0.0)
        c_tol = float(capacitor_tolerance_percent or 0.0)

        if circuit_key in rc_types:
            return f"""%% RC MATLAB Analysis
clear all; close all; clc;

R_nominal = {r1_nom};
C_nominal = {c_nom};
V_in_nominal = {vin_nom};
N = {num_samples};

R_tol = {r1_tol};
C_tol = {c_tol};
Vin_tolerance = {vin_tol};
V_tolerance = Vin_tolerance;

R_samples = zeros(1, N);
C_samples = zeros(1, N);
V_samples = zeros(1, N);
fc_samples = zeros(1, N);
tau_samples = zeros(1, N);

for i = 1:N
    R_samples(i) = R_nominal * (1 + (rand() - 0.5) * 2 * R_tol/100);
    C_samples(i) = C_nominal * (1 + (rand() - 0.5) * 2 * C_tol/100);
    V_samples(i) = V_in_nominal * (1 + (rand() - 0.5) * 2 * Vin_tolerance/100);
    fc_samples(i) = 1 / (2 * pi * R_samples(i) * C_samples(i));
    tau_samples(i) = R_samples(i) * C_samples(i);
end

R_min = R_nominal * (1 - R_tol/100);
R_max = R_nominal * (1 + R_tol/100);
C_min = C_nominal * (1 - C_tol/100);
C_max = C_nominal * (1 + C_tol/100);
Vin_min = V_in_nominal * (1 - Vin_tolerance/100);
Vin_max = V_in_nominal * (1 + Vin_tolerance/100);

fc_min = 1 / (2 * pi * R_max * C_max);
fc_max = 1 / (2 * pi * R_min * C_min);

sample_index = (1:N)';
mc_table = table(sample_index, R_samples', C_samples', V_samples', fc_samples', tau_samples', ...
    'VariableNames', {{'Sample', 'R_Ohms', 'C_F', 'Vin_V', 'fc_Hz', 'tau_s'}});

summary_metric = ["R_Ohms"; "C_F"; "Vin_V"; "fc_Hz"; "tau_s"];
summary_mean = [mean(R_samples); mean(C_samples); mean(V_samples); mean(fc_samples); mean(tau_samples)];
summary_std = [std(R_samples); std(C_samples); std(V_samples); std(fc_samples); std(tau_samples)];
summary_table = table(summary_metric, summary_mean, summary_std, ...
    'VariableNames', {{'Metric', 'Mean', 'StdDev'}});

wc_parameter = ["Vin_min"; "Vin_max"; "R_min"; "R_max"; "C_min"; "C_max"; "fc_min"; "fc_max"];
wc_value = [Vin_min; Vin_max; R_min; R_max; C_min; C_max; fc_min; fc_max];
wc_table = table(wc_parameter, wc_value, 'VariableNames', {{'Parameter', 'Value'}});

fprintf('\\n=== RC MONTE CARLO ===\\n');
fprintf('R_nominal = %.6f Ohms\\n', R_nominal);
fprintf('C_nominal = %.6e F\\n', C_nominal);
fprintf('Vin_nominal = %.6f V\\n', V_in_nominal);
fprintf('Vin_min = %.6f V\\n', Vin_min);
fprintf('Vin_max = %.6f V\\n', Vin_max);
fprintf('Vin_tolerance = %.2f%%\\n', Vin_tolerance);
fprintf('Mean fc = %.6f Hz | Std fc = %.6f Hz\\n', mean(fc_samples), std(fc_samples));

disp(' ');
disp('=== SUMMARY TABLE ===');
disp(summary_table);
disp('=== WORST-CASE VALUES TABLE ===');
disp(wc_table);

figure('Name','RC Monte Carlo','NumberTitle','off');

subplot(2,2,1);
histogram(fc_samples, 40);
grid on;
xlabel('fc (Hz)');
ylabel('Count');
title('Cutoff Frequency Distribution');

subplot(2,2,2);
histogram(tau_samples, 40);
grid on;
xlabel('Tau (s)');
ylabel('Count');
title('Time Constant Distribution');

subplot(2,2,3);
scatter(R_samples, fc_samples, 10, 'filled');
grid on;
xlabel('R (Ohms)');
ylabel('fc (Hz)');
title('R vs fc');

subplot(2,2,4);
scatter(C_samples, fc_samples, 10, 'filled');
grid on;
xlabel('C (F)');
ylabel('fc (Hz)');
title('C vs fc');

fprintf('\\nAnalysis complete.\\n');
"""

        elif circuit_key == "NON_INVERTING_OPAMP":
            target_gain = float(gain_setting) if gain_setting and gain_setting > 1.0 else 10.0
            r2_nom = float(resistor_ohms_2) if resistor_ohms_2 and resistor_ohms_2 > 0 else (r1_nom * (target_gain - 1.0))
            return f"""%% Non-Inverting Op-Amp MATLAB Analysis
clear all; close all; clc;

R1_nominal = {r1_nom};
R2_nominal = {r2_nom};
V_in_nominal = {vin_nom};
N = {num_samples};

R1_tol = {r1_tol};
R2_tol = {r2_tol};
Vin_tolerance = {vin_tol};
V_tolerance = Vin_tolerance;

R1_samples = zeros(1, N);
R2_samples = zeros(1, N);
Vin_samples = zeros(1, N);
gain_samples = zeros(1, N);
vout_samples = zeros(1, N);

for i = 1:N
    R1_samples(i) = R1_nominal * (1 + (rand() - 0.5) * 2 * R1_tol/100);
    R2_samples(i) = R2_nominal * (1 + (rand() - 0.5) * 2 * R2_tol/100);
    Vin_samples(i) = V_in_nominal * (1 + (rand() - 0.5) * 2 * Vin_tolerance/100);
    gain_samples(i) = 1 + (R2_samples(i) / R1_samples(i));
    vout_samples(i) = Vin_samples(i) * gain_samples(i);
end

R1_min = R1_nominal * (1 - R1_tol/100);
R1_max = R1_nominal * (1 + R1_tol/100);
R2_min = R2_nominal * (1 - R2_tol/100);
R2_max = R2_nominal * (1 + R2_tol/100);
Vin_min = V_in_nominal * (1 - Vin_tolerance/100);
Vin_max = V_in_nominal * (1 + Vin_tolerance/100);

gain_nom = 1 + (R2_nominal / R1_nominal);
gain_min = 1 + (R2_min / R1_max);
gain_max = 1 + (R2_max / R1_min);
gain_db_samples = 20 * log10(abs(gain_samples));
gain_db_nom = 20 * log10(abs(gain_nom));
gain_db_min = 20 * log10(abs(gain_min));
gain_db_max = 20 * log10(abs(gain_max));

%% Tabular Monte Carlo Results
sample_index = (1:N)';
mc_table = table(sample_index, R1_samples', R2_samples', Vin_samples', gain_samples', vout_samples', ...
    'VariableNames', {{'Sample', 'R1_Ohms', 'R2_Ohms', 'Vin_V', 'Gain', 'Vout_V'}});

summary_metric = ["R1_Ohms"; "R2_Ohms"; "Vin_V"; "Gain"; "Gain_dB"; "Vout_V"];
summary_mean = [mean(R1_samples); mean(R2_samples); mean(Vin_samples); mean(gain_samples); mean(gain_db_samples); mean(vout_samples)];
summary_std = [std(R1_samples); std(R2_samples); std(Vin_samples); std(gain_samples); std(gain_db_samples); std(vout_samples)];
summary_table = table(summary_metric, summary_mean, summary_std, ...
    'VariableNames', {{'Metric', 'Mean', 'StdDev'}});

Vout_min = gain_min * Vin_min;
Vout_max = gain_max * Vin_max;
Vout_nominal = gain_nom * V_in_nominal;
wc_parameter = ["Vin_min"; "Vin_max"; "R1_min"; "R1_max"; "R2_min"; "R2_max"; "Vout_nominal"; "Vout_min"; "Vout_max"; "gain_nom"; "gain_min"; "gain_max"; "gain_db_nom"; "gain_db_min"; "gain_db_max"];
wc_value = [Vin_min; Vin_max; R1_min; R1_max; R2_min; R2_max; Vout_nominal; Vout_min; Vout_max; gain_nom; gain_min; gain_max; gain_db_nom; gain_db_min; gain_db_max];
wc_table = table(wc_parameter, wc_value, 'VariableNames', {{'Parameter', 'Value'}});

fprintf('\\n=== NON-INVERTING OP-AMP MONTE CARLO ===\\n');
fprintf('R1_nominal = %.6f Ohms\\n', R1_nominal);
fprintf('R2_nominal = %.6f Ohms\\n', R2_nominal);
fprintf('Vin_nominal = %.6f V\\n', V_in_nominal);
fprintf('Vin_min = %.6f V\\n', Vin_min);
fprintf('Vin_max = %.6f V\\n', Vin_max);
fprintf('Vout_nominal = %.6f V\\n', Vout_nominal);
fprintf('Vin_tolerance = %.2f%%\\n', Vin_tolerance);
fprintf('Gain mean = %.6f | std = %.6f\\n', mean(gain_samples), std(gain_samples));
fprintf('Gain_dB mean = %.6f dB | std = %.6f dB\\n', mean(gain_db_samples), std(gain_db_samples));

disp(' ');
disp('=== SUMMARY TABLE ===');
disp(summary_table);
disp('=== WORST-CASE VALUES TABLE ===');
disp(wc_table);

%% Graphs
figure('Name','Non-Inverting Op-Amp Monte Carlo','NumberTitle','off');

subplot(2,2,1);
histogram(gain_samples, 40);
grid on;
xlabel('Gain');
ylabel('Count');
title('Gain Distribution');

subplot(2,2,2);
histogram(vout_samples, 40);
grid on;
xlabel('Vout (V)');
ylabel('Count');
title('Output Voltage Distribution');

subplot(2,2,3);
scatter(Vin_samples, vout_samples, 10, 'filled');
grid on;
xlabel('Vin (V)');
ylabel('Vout (V)');
title('Vin vs Vout');

subplot(2,2,4);
plot(sort(gain_samples), 'LineWidth', 1.2);
grid on;
xlabel('Sorted Sample Index');
ylabel('Gain');
title('Gain Spread (Sorted)');

fprintf('\\nAnalysis complete.\\n');
"""

        elif circuit_key == "INVERTING_OPAMP":
            target_gain = float(gain_setting) if gain_setting and gain_setting > 0 else 10.0
            r2_nom = float(resistor_ohms_2) if resistor_ohms_2 and resistor_ohms_2 > 0 else (r1_nom * target_gain)
            return f"""%% Inverting Op-Amp MATLAB Analysis
clear all; close all; clc;

R1_nominal = {r1_nom};
R2_nominal = {r2_nom};
V_in_nominal = {vin_nom};
N = {num_samples};

R1_tol = {r1_tol};
R2_tol = {r2_tol};
Vin_tolerance = {vin_tol};
V_tolerance = Vin_tolerance;

R1_samples = zeros(1, N);
R2_samples = zeros(1, N);
Vin_samples = zeros(1, N);
gain_samples = zeros(1, N);
vout_samples = zeros(1, N);

for i = 1:N
    R1_samples(i) = R1_nominal * (1 + (rand() - 0.5) * 2 * R1_tol/100);
    R2_samples(i) = R2_nominal * (1 + (rand() - 0.5) * 2 * R2_tol/100);
    Vin_samples(i) = V_in_nominal * (1 + (rand() - 0.5) * 2 * Vin_tolerance/100);
    gain_samples(i) = -(R2_samples(i) / R1_samples(i));
    vout_samples(i) = Vin_samples(i) * gain_samples(i);
end

R1_min = R1_nominal * (1 - R1_tol/100);
R1_max = R1_nominal * (1 + R1_tol/100);
R2_min = R2_nominal * (1 - R2_tol/100);
R2_max = R2_nominal * (1 + R2_tol/100);
Vin_min = V_in_nominal * (1 - Vin_tolerance/100);
Vin_max = V_in_nominal * (1 + Vin_tolerance/100);

gain_nom = -(R2_nominal / R1_nominal);
gain_min = -(R2_max / R1_min);
gain_max = -(R2_min / R1_max);
gain_db_samples = 20 * log10(abs(gain_samples));
gain_db_nom = 20 * log10(abs(gain_nom));
gain_db_min = 20 * log10(abs(gain_min));
gain_db_max = 20 * log10(abs(gain_max));

sample_index = (1:N)';
mc_table = table(sample_index, R1_samples', R2_samples', Vin_samples', gain_samples', vout_samples', ...
    'VariableNames', {{'Sample', 'R1_Ohms', 'R2_Ohms', 'Vin_V', 'Gain', 'Vout_V'}});

summary_metric = ["R1_Ohms"; "R2_Ohms"; "Vin_V"; "Gain"; "Gain_dB"; "Vout_V"];
summary_mean = [mean(R1_samples); mean(R2_samples); mean(Vin_samples); mean(gain_samples); mean(gain_db_samples); mean(vout_samples)];
summary_std = [std(R1_samples); std(R2_samples); std(Vin_samples); std(gain_samples); std(gain_db_samples); std(vout_samples)];
summary_table = table(summary_metric, summary_mean, summary_std, ...
    'VariableNames', {{'Metric', 'Mean', 'StdDev'}});

Vout_min = gain_min * Vin_max;
Vout_max = gain_max * Vin_min;
Vout_nominal = gain_nom * V_in_nominal;
wc_parameter = ["Vin_min"; "Vin_max"; "R1_min"; "R1_max"; "R2_min"; "R2_max"; "Vout_nominal"; "Vout_min"; "Vout_max"; "gain_nom"; "gain_min"; "gain_max"; "gain_db_nom"; "gain_db_min"; "gain_db_max"];
wc_value = [Vin_min; Vin_max; R1_min; R1_max; R2_min; R2_max; Vout_nominal; Vout_min; Vout_max; gain_nom; gain_min; gain_max; gain_db_nom; gain_db_min; gain_db_max];
wc_table = table(wc_parameter, wc_value, 'VariableNames', {{'Parameter', 'Value'}});

fprintf('\\n=== INVERTING OP-AMP MONTE CARLO ===\\n');
fprintf('R1_nominal = %.6f Ohms\\n', R1_nominal);
fprintf('R2_nominal = %.6f Ohms\\n', R2_nominal);
fprintf('Vin_nominal = %.6f V\\n', V_in_nominal);
fprintf('Vin_min = %.6f V\\n', Vin_min);
fprintf('Vin_max = %.6f V\\n', Vin_max);
fprintf('Vout_nominal = %.6f V\\n', Vout_nominal);
fprintf('Vin_tolerance = %.2f%%\\n', Vin_tolerance);
fprintf('Gain mean = %.6f | std = %.6f\\n', mean(gain_samples), std(gain_samples));
fprintf('Gain_dB mean = %.6f dB | std = %.6f dB\\n', mean(gain_db_samples), std(gain_db_samples));

disp(' ');
disp('=== SUMMARY TABLE ===');
disp(summary_table);
disp('=== WORST-CASE VALUES TABLE ===');
disp(wc_table);

figure('Name','Inverting Op-Amp Monte Carlo','NumberTitle','off');

subplot(2,2,1);
histogram(gain_samples, 40);
grid on;
xlabel('Gain');
ylabel('Count');
title('Gain Distribution');

subplot(2,2,2);
histogram(vout_samples, 40);
grid on;
xlabel('Vout (V)');
ylabel('Count');
title('Output Voltage Distribution');

subplot(2,2,3);
scatter(Vin_samples, vout_samples, 10, 'filled');
grid on;
xlabel('Vin (V)');
ylabel('Vout (V)');
title('Vin vs Vout');

subplot(2,2,4);
plot(sort(gain_samples), 'LineWidth', 1.2);
grid on;
xlabel('Sorted Sample Index');
ylabel('Gain');
title('Gain Spread (Sorted)');

fprintf('\\nAnalysis complete.\\n');
"""

        else:
            # ACTIVE_OPAMP_FILTER and other types fallback
            r2_nom = float(resistor_ohms_2) if resistor_ohms_2 and resistor_ohms_2 > 0 else r1_nom
            return f"""%% Active Op-Amp Filter MATLAB Analysis
clear all; close all; clc;

R1_nominal = {r1_nom};
R2_nominal = {r2_nom};
C_nominal = {c_nom};
V_in_nominal = {vin_nom};
N = {num_samples};

R1_tol = {r1_tol};
R2_tol = {r2_tol};
C_tol = {c_tol};
Vin_tolerance = {vin_tol};
V_tolerance = Vin_tolerance;

R1_samples = zeros(1, N);
R2_samples = zeros(1, N);
C_samples = zeros(1, N);
Vin_samples = zeros(1, N);
gain_samples = zeros(1, N);
fc_samples = zeros(1, N);
vout_samples = zeros(1, N);

for i = 1:N
    R1_samples(i) = R1_nominal * (1 + (rand() - 0.5) * 2 * R1_tol/100);
    R2_samples(i) = R2_nominal * (1 + (rand() - 0.5) * 2 * R2_tol/100);
    C_samples(i) = C_nominal * (1 + (rand() - 0.5) * 2 * C_tol/100);
    Vin_samples(i) = V_in_nominal * (1 + (rand() - 0.5) * 2 * Vin_tolerance/100);
    gain_samples(i) = 1 + (R2_samples(i) / R1_samples(i));
    fc_samples(i) = 1 / (2 * pi * R2_samples(i) * C_samples(i));
    vout_samples(i) = Vin_samples(i) * gain_samples(i);
end

R1_min = R1_nominal * (1 - R1_tol/100);
R1_max = R1_nominal * (1 + R1_tol/100);
R2_min = R2_nominal * (1 - R2_tol/100);
R2_max = R2_nominal * (1 + R2_tol/100);
C_min = C_nominal * (1 - C_tol/100);
C_max = C_nominal * (1 + C_tol/100);
Vin_min = V_in_nominal * (1 - Vin_tolerance/100);
Vin_max = V_in_nominal * (1 + Vin_tolerance/100);

gain_nom = 1 + (R2_nominal / R1_nominal);
gain_min = 1 + (R2_min / R1_max);
gain_max = 1 + (R2_max / R1_min);
gain_db_samples = 20 * log10(abs(gain_samples));
gain_db_nom = 20 * log10(abs(gain_nom));
gain_db_min = 20 * log10(abs(gain_min));
gain_db_max = 20 * log10(abs(gain_max));
fc_min = 1 / (2 * pi * R2_max * C_max);
fc_max = 1 / (2 * pi * R2_min * C_min);
Vout_min = gain_min * Vin_min;
Vout_max = gain_max * Vin_max;
Vout_nominal = gain_nom * V_in_nominal;

sample_index = (1:N)';
mc_table = table(sample_index, R1_samples', R2_samples', C_samples', Vin_samples', gain_samples', fc_samples', vout_samples', ...
    'VariableNames', {{'Sample', 'R1_Ohms', 'R2_Ohms', 'C_F', 'Vin_V', 'Gain', 'fc_Hz', 'Vout_V'}});

summary_metric = ["R1_Ohms"; "R2_Ohms"; "C_F"; "Vin_V"; "Gain"; "Gain_dB"; "fc_Hz"; "Vout_V"];
summary_mean = [mean(R1_samples); mean(R2_samples); mean(C_samples); mean(Vin_samples); mean(gain_samples); mean(gain_db_samples); mean(fc_samples); mean(vout_samples)];
summary_std = [std(R1_samples); std(R2_samples); std(C_samples); std(Vin_samples); std(gain_samples); std(gain_db_samples); std(fc_samples); std(vout_samples)];
summary_table = table(summary_metric, summary_mean, summary_std, ...
    'VariableNames', {{'Metric', 'Mean', 'StdDev'}});

wc_parameter = ["Vin_min"; "Vin_max"; "R1_min"; "R1_max"; "R2_min"; "R2_max"; "C_min"; "C_max"; "Vout_nominal"; "Vout_min"; "Vout_max"; "gain_nom"; "gain_min"; "gain_max"; "gain_db_nom"; "gain_db_min"; "gain_db_max"; "fc_min"; "fc_max"];
wc_value = [Vin_min; Vin_max; R1_min; R1_max; R2_min; R2_max; C_min; C_max; Vout_nominal; Vout_min; Vout_max; gain_nom; gain_min; gain_max; gain_db_nom; gain_db_min; gain_db_max; fc_min; fc_max];
wc_table = table(wc_parameter, wc_value, 'VariableNames', {{'Parameter', 'Value'}});

fprintf('\\n=== ACTIVE OP-AMP FILTER MONTE CARLO ===\\n');
fprintf('R1_nominal = %.6f Ohms\\n', R1_nominal);
fprintf('R2_nominal = %.6f Ohms\\n', R2_nominal);
fprintf('C_nominal = %.6e F\\n', C_nominal);
fprintf('Vin_nominal = %.6f V\\n', V_in_nominal);
fprintf('Vin_min = %.6f V\\n', Vin_min);
fprintf('Vin_max = %.6f V\\n', Vin_max);
fprintf('Vout_nominal = %.6f V\\n', Vout_nominal);
fprintf('Gain mean = %.6f | std = %.6f\\n', mean(gain_samples), std(gain_samples));
fprintf('Gain_dB mean = %.6f dB | std = %.6f dB\\n', mean(gain_db_samples), std(gain_db_samples));

disp(' ');
disp('=== SUMMARY TABLE ===');
disp(summary_table);
disp('=== WORST-CASE VALUES TABLE ===');
disp(wc_table);

figure('Name','Active Op-Amp Filter Monte Carlo','NumberTitle','off');

subplot(2,2,1);
histogram(gain_samples, 40);
grid on;
xlabel('Gain');
ylabel('Count');
title('Gain Distribution');

subplot(2,2,2);
histogram(fc_samples, 40);
grid on;
xlabel('fc (Hz)');
ylabel('Count');
title('Cutoff Frequency Distribution');

subplot(2,2,3);
scatter(Vin_samples, vout_samples, 10, 'filled');
grid on;
xlabel('Vin (V)');
ylabel('Vout (V)');
title('Vin vs Vout');

subplot(2,2,4);
scatter(R2_samples, fc_samples, 10, 'filled');
grid on;
xlabel('R2 (Ohms)');
ylabel('fc (Hz)');
title('R2 vs fc');

fprintf('Analysis complete.\\n');
"""

    @staticmethod
    def generate_linear_regulator_analysis(
        input_ac_voltage: float,
        output_voltage: float,
        filter_capacitor: float,
        series_resistor: Optional[float],
        load_current: float,
        num_samples: int,
        input_voltage_tolerance_percent: float,
        capacitor_tolerance_percent: float,
        r1_tolerance_percent: float,
        load_current_tolerance_percent: float,
        line_frequency_hz: float = 60.0,
        diode_forward_voltage: float = 0.7,
        primary_voltage_rms: Optional[float] = None,
        secondary_voltage_rms: Optional[float] = None,
        transformer_turns_ratio: Optional[float] = None,
        dropout_voltage: float = 0.2,
    ) -> str:
        """Generate MATLAB code for a linear regulator with bridge rectifier."""
        secondary_rms = secondary_voltage_rms if secondary_voltage_rms is not None else input_ac_voltage
        primary_rms = primary_voltage_rms
        if primary_rms is None and transformer_turns_ratio is not None:
            primary_rms = secondary_rms * transformer_turns_ratio
        turns_ratio = transformer_turns_ratio
        if turns_ratio is None and primary_rms is not None and secondary_rms:
            turns_ratio = primary_rms / secondary_rms

        primary_expr = "[];" if primary_rms is None else f"{primary_rms:.6g};"
        secondary_expr = f"{secondary_rms:.6g};"
        turns_expr = "[];" if turns_ratio is None else f"{turns_ratio:.6g};"
        rs_value = 0.0 if series_resistor is None else float(series_resistor)

        return f"""%% Linear Regulator with Bridge Rectifier
clear; clc; close all;

% Nominal design inputs
Vsecondary_rms_nom = {secondary_rms:.6g};      % Secondary RMS voltage (V)
Vout_target = {output_voltage:.6g};            % Regulated output voltage (V)
IFL_nom = {load_current:.6g};                  % Full-load current (A)
C_nom = {filter_capacitor:.6g};                % Filter capacitor (F)
line_freq = {line_frequency_hz:.6g};           % Line frequency (Hz)
diode_drop = {diode_forward_voltage:.6g};      % Single diode forward drop (V)
regulator_dropout = {dropout_voltage:.6g};     % Regulator dropout voltage (V)
num_samples = {int(num_samples)};

% Transformer reference
Vprimary_rms_nom = {primary_expr}
Vsecondary_rms_ref = {secondary_expr}
turns_ratio = {turns_expr}

% Tolerances
line_tol = {input_voltage_tolerance_percent:.6g} / 100;
C_tol = {capacitor_tolerance_percent:.6g} / 100;
Rs_tol = {r1_tolerance_percent:.6g} / 100;    % Kept for interface compatibility
IL_tol = {load_current_tolerance_percent:.6g} / 100;

% Fixed values
Rs_nom = {rs_value:.6g};                       % Not used in main linear path
rectifier_freq = 2 * line_freq;
T = 1 / rectifier_freq;
Tb = 0.75 * T;
Tc = T - Tb;

% Nominal transformer / rectifier values
Vprimary_peak_nom = Vprimary_rms_nom * sqrt(2);
Vsecondary_peak_nom = Vsecondary_rms_nom * sqrt(2);
Vpeak_nom = Vsecondary_peak_nom - 2 * diode_drop;
Vpp_nom = (IFL_nom * Tb) / C_nom;
Vop_nom = Vpp_nom / 2;
VDC_nom = Vpeak_nom - Vop_nom;
VTR_nom = Vpeak_nom - Vpp_nom;
VCF_nom = VDC_nom;
VCF_HL_NL = Vpeak_nom;
VCF_HL_FL = VDC_nom;
PIV_nom = Vpeak_nom;
RL_nom = Vout_target / IFL_nom;
headroom_nom = VCF_nom - Vout_target - regulator_dropout;

fprintf('Linear Regulator with Bridge Rectifier\\n');
fprintf('--------------------------------------\\n');
fprintf('Vprimary_rms = %.3f V\\n', Vprimary_rms_nom);
fprintf('Vprimary_peak = %.3f V\\n', Vprimary_peak_nom);
fprintf('Vsecondary_rms = %.3f V\\n', Vsecondary_rms_nom);
fprintf('Vsecondary_peak = %.3f V\\n', Vsecondary_peak_nom);
fprintf('N = %.3f\\n', turns_ratio);
fprintf('Tb = %.3f ms\\n', Tb * 1000);
fprintf('Tc = %.3f ms\\n', Tc * 1000);
fprintf('IFL = %.3f A\\n', IFL_nom);
fprintf('Vpp = %.3f V\\n', Vpp_nom);
fprintf('Vop = %.3f V\\n', Vop_nom);
fprintf('VDC = %.3f V\\n', VDC_nom);
fprintf('VTR = %.3f V\\n', VTR_nom);
fprintf('VCF = %.3f V\\n', VCF_nom);
fprintf('VCF_HL_NL = %.3f V\\n', VCF_HL_NL);
fprintf('VCF_HL_FL = %.3f V\\n', VCF_HL_FL);
fprintf('PIV = %.3f V\\n', PIV_nom);
fprintf('Headroom = %.3f V\\n\\n', headroom_nom);

% Worst-case values
Vprimary_rms_max = Vprimary_rms_nom * (1 + line_tol);
Vprimary_rms_min = Vprimary_rms_nom * (1 - line_tol);
Vprimary_peak_max = Vprimary_rms_max * sqrt(2);
Vprimary_peak_min = Vprimary_rms_min * sqrt(2);
Vsecondary_rms_max = Vsecondary_rms_nom * (1 + line_tol);
Vsecondary_rms_min = Vsecondary_rms_nom * (1 - line_tol);
Vsecondary_peak_max = Vsecondary_rms_max * sqrt(2);
Vsecondary_peak_min = Vsecondary_rms_min * sqrt(2);
IL_max = IFL_nom * (1 + IL_tol);
IL_min = IFL_nom * (1 - IL_tol);
RL_max = Vout_target / IL_min;
RL_min = Vout_target / IL_max;
Vpeak_max = Vsecondary_peak_max - 2 * diode_drop;
Vpeak_min = Vsecondary_peak_min - 2 * diode_drop;
C_max = C_nom * (1 + C_tol);
C_min = C_nom * (1 - C_tol);
Vpp_max = (IL_max * Tb) / C_min;
Vpp_min = (IL_min * Tb) / C_max;
Vop_max = Vpp_max / 2;
Vop_min = Vpp_min / 2;
VCF_max = Vpeak_max - Vop_min;
VCF_min = Vpeak_min - Vop_max;
VTR_worst = Vpeak_min - Vpp_max;
Vout_max = min(Vout_target, max(VCF_max - regulator_dropout, 0));
Vout_min = min(Vout_target, max(VCF_min - regulator_dropout, 0));

wc_parameter = ["Vprimary_rms_max"; "Vprimary_rms_min"; "Vprimary_peak_max"; "Vprimary_peak_min"; ...
    "Vsecondary_rms_max"; "Vsecondary_rms_min"; "Vsecondary_peak_max"; "Vsecondary_peak_min"; ...
    "IL_max"; "IL_min"; "RL_max"; "RL_min"; "Vpeak_max"; "Vpeak_min"; "C_max"; "C_min"; ...
    "Vpp_max"; "Vpp_min"; "Vop_max"; "Vop_min"; "VCF_max"; "VCF_min"; "VTR_worst"; "Vout_max"; "Vout_min"];
wc_value = [Vprimary_rms_max; Vprimary_rms_min; Vprimary_peak_max; Vprimary_peak_min; ...
    Vsecondary_rms_max; Vsecondary_rms_min; Vsecondary_peak_max; Vsecondary_peak_min; ...
    IL_max; IL_min; RL_max; RL_min; Vpeak_max; Vpeak_min; C_max; C_min; ...
    Vpp_max; Vpp_min; Vop_max; Vop_min; VCF_max; VCF_min; VTR_worst; Vout_max; Vout_min];
wc_table = table(wc_parameter, wc_value, 'VariableNames', {{'Parameter', 'Value'}});

fprintf('Worst-Case Summary\\n');
fprintf('------------------\\n');
fprintf('Vprimary_rms_max = %.3f V\\n', Vprimary_rms_max);
fprintf('Vprimary_rms_min = %.3f V\\n', Vprimary_rms_min);
fprintf('Vsecondary_rms_max = %.3f V\\n', Vsecondary_rms_max);
fprintf('Vsecondary_rms_min = %.3f V\\n', Vsecondary_rms_min);
fprintf('Vpp_max = %.3f V\\n', Vpp_max);
fprintf('Vpp_min = %.3f V\\n', Vpp_min);
fprintf('VCF_max = %.3f V\\n', VCF_max);
fprintf('VCF_min = %.3f V\\n', VCF_min);
fprintf('VTR_worst = %.3f V\\n', VTR_worst);
fprintf('Vout_max = %.3f V\\n', Vout_max);
fprintf('Vout_min = %.3f V\\n\\n', Vout_min);

disp('=== WORST-CASE VALUES TABLE ===');
disp(wc_table);

% Monte Carlo analysis
rng(1);
Vsecondary_rms_samples = Vsecondary_rms_nom .* (1 + line_tol .* randn(num_samples, 1));
C_samples = C_nom .* (1 + C_tol .* randn(num_samples, 1));
IL_samples = IFL_nom .* (1 + IL_tol .* randn(num_samples, 1));

Vsecondary_peak_samples = Vsecondary_rms_samples .* sqrt(2);
Vpeak_samples = Vsecondary_peak_samples - 2 * diode_drop;
Vpp_samples = (IL_samples .* Tb) ./ C_samples;
Vop_samples = Vpp_samples ./ 2;
VDC_samples = Vpeak_samples - Vop_samples;
VTR_samples = Vpeak_samples - Vpp_samples;
Vout_samples = min(Vout_target .* ones(num_samples, 1), max(VDC_samples - regulator_dropout, 0));
Preg_samples = max(VDC_samples - Vout_samples, 0) .* IL_samples;

summary_metric = ["Vsecondary_rms"; "Vpeak"; "Vpp"; "VDC"; "VTR"; "Vout"; "Preg"];
summary_mean = [mean(Vsecondary_rms_samples); mean(Vpeak_samples); mean(Vpp_samples); mean(VDC_samples); mean(VTR_samples); mean(Vout_samples); mean(Preg_samples)];
summary_std = [std(Vsecondary_rms_samples); std(Vpeak_samples); std(Vpp_samples); std(VDC_samples); std(VTR_samples); std(Vout_samples); std(Preg_samples)];
summary_table = table(summary_metric, summary_mean, summary_std, 'VariableNames', {{'Metric', 'Mean', 'StdDev'}});

disp('=== MONTE CARLO SUMMARY TABLE ===');
disp(summary_table);

figure('Name', 'Linear Regulator with Bridge Rectifier', 'Position', [100, 100, 1200, 800]);

subplot(2,2,1);
histogram(VDC_samples, 40);
grid on;
xlabel('VDC (V)');
ylabel('Count');
title('Filtered DC Distribution');

subplot(2,2,2);
histogram(Vout_samples, 40);
grid on;
xlabel('Vout (V)');
ylabel('Count');
title('Regulated Output Distribution');

subplot(2,2,3);
scatter(Vsecondary_rms_samples, VDC_samples, 10, 'filled');
grid on;
xlabel('Vsecondary_rms (V)');
ylabel('VDC (V)');
title('Secondary RMS vs VDC');

subplot(2,2,4);
scatter(Vpp_samples, VTR_samples, 10, 'filled');
grid on;
xlabel('Vpp (V)');
ylabel('VTR (V)');
title('Ripple vs Trough Voltage');

fprintf('Analysis complete.\\n');
"""

    @staticmethod
    def generate_zener_regulator_analysis(
        input_ac_voltage: float,
        output_voltage: float,
        load_resistance: float,
        series_resistor: float,
        zener_voltage: float,
        filter_capacitor: float,
        num_samples: int,
        ac_tolerance: float,
        resistor_tolerance: float,
        capacitor_tolerance: float,
        load_tolerance: float,
        line_frequency_hz: float = 60.0,
        diode_forward_voltage: float = 0.7,
        primary_voltage_rms: float = None,
        secondary_voltage_rms: float = None,
        transformer_turns_ratio: float = None
    ) -> str:
        """Generate MATLAB code for Zener shunt regulator with bridge rectifier."""
        primary_expr = "[];" if primary_voltage_rms is None else f"{primary_voltage_rms:.6g};"
        secondary_expr = "[];" if secondary_voltage_rms is None else f"{secondary_voltage_rms:.6g};"
        turns_expr = "[];" if transformer_turns_ratio is None else f"{transformer_turns_ratio:.6g};"
        return f"""%% Zener Shunt Regulator with Bridge Rectifier
clear; clc; close all;

% Nominal design inputs
Vin_ac_rms = {input_ac_voltage:.6g};          % Secondary RMS voltage (V)
Vout_target = {output_voltage:.6g};           % Regulated output voltage (V)
Rload_nom = {load_resistance:.6g};            % Load resistance (Ohms)
Rs_nom = {series_resistor:.6g};               % Series resistor (Ohms)
Vz_nom = {zener_voltage:.6g};                 % Zener voltage (V)
C_nom = {filter_capacitor:.6g};               % Filter capacitor (F)
line_freq = {line_frequency_hz:.6g};          % Line frequency (Hz)
diode_drop = {diode_forward_voltage:.6g};     % Single diode forward drop (V)
num_samples = {int(num_samples)};

% Transformer reference
Vprimary_rms = {primary_expr}
Vsecondary_rms = {secondary_expr}
turns_ratio = {turns_expr}

% Tolerances
ac_tol = {ac_tolerance:.6g} / 100;
rs_tol = {resistor_tolerance:.6g} / 100;
c_tol = {capacitor_tolerance:.6g} / 100;
load_tol = {load_tolerance:.6g} / 100;

% Deterministic operating point
rectifier_freq = 2 * line_freq;
Vsec_peak = Vin_ac_rms * sqrt(2);
Vpeak_rectified = Vsec_peak - 2 * diode_drop;
Iload_nom = Vout_target / Rload_nom;
Vripple_nom = Iload_nom / (rectifier_freq * C_nom);
VCF_nom = Vpeak_rectified - Vripple_nom / 2;
Is_nom = max((VCF_nom - Vz_nom) / Rs_nom, 0);
Izt_nom = max(Is_nom - Iload_nom, 0);
Pz_nom = Vz_nom * Izt_nom;
Prs_nom = Is_nom^2 * Rs_nom;

fprintf('Zener Regulator Nominal Values\\n');
fprintf('------------------------------\\n');
fprintf('Primary RMS Voltage: %.3f V\\n', Vprimary_rms);
fprintf('Secondary RMS Voltage: %.3f V\\n', Vin_ac_rms);
fprintf('Secondary Peak Voltage: %.3f V\\n', Vsec_peak);
fprintf('Peak Rectified Voltage: %.3f V\\n', Vpeak_rectified);
fprintf('Filtered DC Voltage (VCF): %.3f V\\n', VCF_nom);
fprintf('Load Current: %.3f A\\n', Iload_nom);
fprintf('Series Current: %.3f A\\n', Is_nom);
fprintf('Zener Current: %.3f A\\n', Izt_nom);
fprintf('Zener Power: %.3f W\\n', Pz_nom);
fprintf('Series Resistor Power: %.3f W\\n\\n', Prs_nom);

% Monte Carlo analysis
rng(1);
Vin_samples = Vin_ac_rms .* (1 + ac_tol .* randn(num_samples, 1));
Rs_samples = Rs_nom .* (1 + rs_tol .* randn(num_samples, 1));
C_samples = C_nom .* (1 + c_tol .* randn(num_samples, 1));
Rload_samples = Rload_nom .* (1 + load_tol .* randn(num_samples, 1));

Vsec_peak_samples = Vin_samples .* sqrt(2);
Vpeak_samples = Vsec_peak_samples - 2 * diode_drop;
Iload_samples = Vout_target ./ Rload_samples;
Vripple_samples = Iload_samples ./ (rectifier_freq .* C_samples);
VCF_samples = Vpeak_samples - Vripple_samples ./ 2;
Is_samples = max((VCF_samples - Vz_nom) ./ Rs_samples, 0);
Iz_samples = max(Is_samples - Iload_samples, 0);
Vout_samples = Vz_nom .* ones(num_samples, 1);
Pz_samples = Vz_nom .* Iz_samples;
Prs_samples = Is_samples .^ 2 .* Rs_samples;

fprintf('Monte Carlo Summary (%d samples)\\n', num_samples);
fprintf('--------------------------------\\n');
fprintf('Mean VCF: %.3f V\\n', mean(VCF_samples));
fprintf('Mean Vout: %.3f V\\n', mean(Vout_samples));
fprintf('Mean Iz: %.3f A\\n', mean(Iz_samples));
fprintf('Mean Pz: %.3f W\\n', mean(Pz_samples));
fprintf('Mean Prs: %.3f W\\n\\n', mean(Prs_samples));

% Worst-case summary
fprintf('Worst-Case Summary\\n');
fprintf('------------------\\n');
fprintf('VCF range: %.3f V to %.3f V\\n', min(VCF_samples), max(VCF_samples));
fprintf('Iz range: %.3f A to %.3f A\\n', min(Iz_samples), max(Iz_samples));
fprintf('Pz max: %.3f W\\n', max(Pz_samples));
fprintf('Prs max: %.3f W\\n\\n', max(Prs_samples));

% Plots
figure('Name', 'Zener Regulator Analysis', 'Position', [100, 100, 1200, 800]);

subplot(2,2,1);
histogram(VCF_samples, 40);
grid on;
xlabel('VCF (V)');
ylabel('Count');
title('Filtered DC Voltage');

subplot(2,2,2);
histogram(Iz_samples * 1000, 40);
grid on;
xlabel('Zener Current (mA)');
ylabel('Count');
title('Zener Current Distribution');

subplot(2,2,3);
scatter(VCF_samples, Iz_samples * 1000, 10, 'filled');
grid on;
xlabel('VCF (V)');
ylabel('Zener Current (mA)');
title('VCF vs Zener Current');

subplot(2,2,4);
scatter(Rs_samples, Prs_samples, 10, 'filled');
grid on;
xlabel('Series Resistor (Ohms)');
ylabel('Resistor Power (W)');
title('Rs vs Power Dissipation');

fprintf('Analysis complete.\\n');
"""
