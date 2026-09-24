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
    def generate_linear_regulator_analysis(*args, **kwargs) -> str:
        """Delegate to the clean linear regulator generator."""
        from app.matlab_generator_clean import MATLABCodeGenerator as CleanMATLABCodeGenerator
        return CleanMATLABCodeGenerator.generate_linear_regulator_analysis(*args, **kwargs)

    @staticmethod
    def generate_zener_regulator_analysis(*args, **kwargs) -> str:
        """Stub for zener regulator (not currently used)."""
        return "%% Zener Regulator Analysis\nfprintf('Placeholder\\n');\n"
