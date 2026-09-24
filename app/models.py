"""Pydantic models for request/response contracts"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
from enum import Enum


class CircuitType(str, Enum):
    """Supported circuit types"""
    RC_LOW_PASS = "RC_LOW_PASS"
    RC_HIGH_PASS = "RC_HIGH_PASS"
    RC_CHARGING = "RC_CHARGING"
    NON_INVERTING_OPAMP = "NON_INVERTING_OPAMP"
    INVERTING_OPAMP = "INVERTING_OPAMP"
    ACTIVE_OPAMP_FILTER = "ACTIVE_OPAMP_FILTER"
    LINEAR_REGULATOR_WITH_BRIDGE_RECTIFIER = "LINEAR_REGULATOR_WITH_BRIDGE_RECTIFIER"
    ZENER_REGULATOR_WITH_BRIDGE_RECTIFIER = "ZENER_REGULATOR_WITH_BRIDGE_RECTIFIER"


class VoltageType(str, Enum):
    """Voltage input types"""
    DC = "DC"
    AC_PEAK_TO_PEAK = "AC_PEAK_TO_PEAK"
    AC_PEAK = "AC_PEAK"
    AC_RMS = "AC_RMS"


# ========== REQUEST MODELS ==========

class CircuitDesignRequest(BaseModel):
    """Request for deterministic circuit design"""
    circuit_type: CircuitType
    voltage_value: Optional[float] = Field(None, gt=0, lt=1000)
    output_voltage: Optional[float] = Field(None, gt=0, lt=1000)
    voltage_type: VoltageType = Field(default=VoltageType.DC)
    cutoff_frequency: Optional[float] = Field(None, gt=0)
    time_duration: Optional[float] = Field(None, gt=0)
    gain_setting: Optional[float] = Field(None)
    resistor_ohms: Optional[float] = Field(None, gt=0)
    resistor_ohms_2: Optional[float] = Field(None, gt=0)
    # Linear regulator specific parameters
    load_current: Optional[float] = Field(None, gt=0)  # Load current in Amps
    dropout_voltage: Optional[float] = Field(None, gt=0)  # Dropout voltage in Volts
    ripple_voltage: Optional[float] = Field(None, gt=0)  # Allowable ripple in Volts
    # Zener regulator specific parameters
    load_resistance: Optional[float] = Field(None, gt=0)  # Load resistance in Ohms
    min_zener_current: Optional[float] = Field(None, gt=0)  # Minimum Zener current in mA
    primary_voltage_rms: Optional[float] = Field(None, gt=0)
    secondary_voltage_rms: Optional[float] = Field(None, gt=0)
    transformer_turns_ratio: Optional[float] = Field(None, gt=0)
    line_frequency_hz: Optional[float] = Field(None, gt=0)
    diode_forward_voltage: Optional[float] = Field(None, gt=0)
    # Active Op-Amp Filter configuration
    is_inverting: Optional[bool] = Field(None)  # True for inverting, False for non-inverting
    capacitor_farads: Optional[float] = Field(None, gt=0)  # Capacitor value in Farads


class MonteCarloRequest(BaseModel):
    """Request for Monte Carlo analysis"""
    circuit_type: CircuitType
    resistor_ohms: Optional[float] = Field(None, gt=0)
    resistor_ohms_2: Optional[float] = Field(None, gt=0)
    capacitor_farads: Optional[float] = Field(None, gt=0)
    voltage_value: float = Field(..., gt=0, lt=1000)
    output_voltage: Optional[float] = Field(None, gt=0, lt=1000)
    voltage_type: VoltageType = Field(default=VoltageType.DC)
    num_samples: int = Field(..., ge=100, le=100000)
    r1_tolerance_percent: float = Field(..., ge=0, le=50)
    r2_tolerance_percent: Optional[float] = Field(None, ge=0, le=50)
    capacitor_tolerance_percent: float = Field(..., ge=0, le=50)
    line_fluctuation_percent: float = Field(..., ge=0, le=50)
    time_duration: Optional[float] = Field(None, gt=0)
    gain_setting: Optional[float] = Field(None)
    cutoff_frequency: Optional[float] = Field(None, gt=0)
    load_current: Optional[float] = Field(None, gt=0)
    load_resistance: Optional[float] = Field(None, gt=0)
    dropout_voltage: Optional[float] = Field(None, gt=0)
    ripple_voltage: Optional[float] = Field(None, gt=0)
    min_zener_current: Optional[float] = Field(None, gt=0)
    primary_voltage_rms: Optional[float] = Field(None, gt=0)
    secondary_voltage_rms: Optional[float] = Field(None, gt=0)
    transformer_turns_ratio: Optional[float] = Field(None, gt=0)
    line_frequency_hz: Optional[float] = Field(None, gt=0)
    diode_forward_voltage: Optional[float] = Field(None, gt=0)

    class Config:
        extra = "allow"


class WorstCaseRequest(BaseModel):
    """Request for worst-case analysis"""
    circuit_type: CircuitType
    resistor_ohms: Optional[float] = Field(None, gt=0)
    resistor_ohms_2: Optional[float] = Field(None, gt=0)
    capacitor_farads: Optional[float] = Field(None, gt=0)
    voltage_value: float = Field(..., gt=0, lt=1000)
    output_voltage: Optional[float] = Field(None, gt=0, lt=1000)
    voltage_type: VoltageType = Field(default=VoltageType.DC)
    r1_tolerance_percent: float = Field(..., ge=0, le=50)
    r2_tolerance_percent: Optional[float] = Field(None, ge=0, le=50)
    capacitor_tolerance_percent: float = Field(..., ge=0, le=50)
    line_fluctuation_percent: float = Field(..., ge=0, le=50)
    time_duration: Optional[float] = Field(None, gt=0)
    gain_setting: Optional[float] = Field(None)
    cutoff_frequency: Optional[float] = Field(None, gt=0)
    load_current: Optional[float] = Field(None, gt=0)
    load_resistance: Optional[float] = Field(None, gt=0)
    dropout_voltage: Optional[float] = Field(None, gt=0)
    ripple_voltage: Optional[float] = Field(None, gt=0)
    min_zener_current: Optional[float] = Field(None, gt=0)
    primary_voltage_rms: Optional[float] = Field(None, gt=0)
    secondary_voltage_rms: Optional[float] = Field(None, gt=0)
    transformer_turns_ratio: Optional[float] = Field(None, gt=0)
    line_frequency_hz: Optional[float] = Field(None, gt=0)
    diode_forward_voltage: Optional[float] = Field(None, gt=0)


class MATLABGenerationRequest(BaseModel):
    """Request for MATLAB code generation"""
    circuit_type: CircuitType
    resistor_ohms: Optional[float] = Field(None, gt=0)
    resistor_ohms_2: Optional[float] = Field(None, gt=0)
    capacitor_farads: Optional[float] = Field(None, gt=0)
    voltage_value: float = Field(..., gt=0, lt=1000)
    output_voltage: Optional[float] = Field(None, gt=0, lt=1000)
    voltage_type: VoltageType = Field(default=VoltageType.DC)
    num_samples: int = Field(..., ge=100, le=100000)
    r1_tolerance_percent: float = Field(..., ge=0, le=50)
    r2_tolerance_percent: Optional[float] = Field(None, ge=0, le=50)
    capacitor_tolerance_percent: float = Field(..., ge=0, le=50)
    line_fluctuation_percent: float = Field(..., ge=0, le=50)
    cutoff_frequency: Optional[float] = Field(None, gt=0)
    gain_setting: Optional[float] = Field(None)
    load_current: Optional[float] = Field(None, gt=0)
    load_resistance: Optional[float] = Field(None, gt=0)
    dropout_voltage: Optional[float] = Field(None, gt=0)
    ripple_voltage: Optional[float] = Field(None, gt=0)
    min_zener_current: Optional[float] = Field(None, gt=0)
    primary_voltage_rms: Optional[float] = Field(None, gt=0)
    secondary_voltage_rms: Optional[float] = Field(None, gt=0)
    transformer_turns_ratio: Optional[float] = Field(None, gt=0)
    line_frequency_hz: Optional[float] = Field(None, gt=0)
    diode_forward_voltage: Optional[float] = Field(None, gt=0)


class CSVExportRequest(BaseModel):
    """Request for CSV export"""
    circuit_type: CircuitType
    raw_data: Dict[str, List[float]]


class ExplanationRequest(BaseModel):
    """Request for conceptual explanation"""
    concept: str
    circuit_type: CircuitType
    context: Optional[str] = None


# ========== RESPONSE MODELS ==========

class MonteCarloMetric(BaseModel):
    """Statistics for a single metric from Monte Carlo"""
    mean: Optional[float] = None
    std_dev: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    percentile_5: Optional[float] = None
    percentile_95: Optional[float] = None
    absolute_min: Optional[float] = None
    absolute_max: Optional[float] = None


class CircuitDesignResponse(BaseModel):
    """Response for circuit design"""
    circuit_type: CircuitType
    resistor_ohms: Optional[float] = None
    resistor_ohms_2: Optional[float] = None
    capacitor_farads: Optional[float] = None
    resistor_display: Optional[str] = None
    resistor_display_2: Optional[str] = None
    capacitor_display: Optional[str] = None
    gain: Optional[float] = None
    transfer_function: Optional[str] = None
    cutoff_frequency: Optional[float] = None
    time_constant: Optional[float] = None
    output_voltage: Optional[float] = None
    input_voltage: Optional[float] = None
    voltage_value: Optional[float] = None
    derivation: List[str] = []
    # Linear regulator specific fields
    series_resistor_ohms: Optional[float] = None
    series_resistor_display: Optional[str] = None
    filter_capacitor_farads: Optional[float] = None
    filter_capacitor_display: Optional[str] = None
    zener_voltage: Optional[float] = None
    zener_current: Optional[float] = None
    peak_input_voltage: Optional[float] = None
    load_current: Optional[float] = None
    dropout_voltage: Optional[float] = None
    # Zener regulator specific fields
    zener_diode_voltage: Optional[float] = None
    zener_diode_power: Optional[float] = None
    series_resistor_value: Optional[float] = None
    series_resistor_power: Optional[float] = None
    load_resistor_value: Optional[float] = None
    no_load_current: Optional[float] = None
    full_load_current: Optional[float] = None
    primary_voltage_rms: Optional[float] = None
    secondary_voltage_rms: Optional[float] = None
    transformer_turns_ratio: Optional[float] = None
    line_frequency_hz: Optional[float] = None
    diode_forward_voltage: Optional[float] = None


class MonteCarloResponse(BaseModel):
    """Response for Monte Carlo analysis"""
    circuit_type: CircuitType
    num_samples: int
    r1_tolerance_percent: float
    r2_tolerance_percent: Optional[float]
    capacitor_tolerance_percent: float
    line_fluctuation_percent: float
    metrics: Dict[str, MonteCarloMetric]
    raw_data: Dict[str, List[float]] = {}


class WorstCaseResponse(BaseModel):
    """Response for worst-case analysis"""
    circuit_type: CircuitType
    analysis_data: Dict[str, Any]
    summary: str


class MATLABCodeResponse(BaseModel):
    """Response with MATLAB code"""
    circuit_type: CircuitType
    matlab_code: str
    description: str


class CSVExportResponse(BaseModel):
    """Response with CSV data"""
    csv_data: str
    filename: str
    num_rows: int


class ExplanationResponse(BaseModel):
    """Response with conceptual explanation"""
    concept: str
    explanation: str
    source: str
