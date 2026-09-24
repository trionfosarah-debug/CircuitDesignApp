"""FastAPI backend for Circuit Design and Robustness Analysis Platform"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pathlib import Path

import os
import sys
import csv
import io
import numpy as np
from dotenv import load_dotenv
from typing import Optional
import logging
import json
import secrets
import threading
import time
import webbrowser
from collections import defaultdict, deque
from urllib.parse import urlparse

from app.models import (
    CircuitDesignRequest, CircuitDesignResponse,
    MonteCarloRequest, MonteCarloResponse, MonteCarloMetric,
    WorstCaseRequest, WorstCaseResponse,
    MATLABGenerationRequest, MATLABCodeResponse,
    CSVExportRequest, CSVExportResponse,
    ExplanationRequest, ExplanationResponse,
    CircuitType
)
from app.deterministic_design import DeterministicDesign
from app.monte_carlo import MonteCarloAnalysis
from app.worst_case import WorstCaseAnalysis
from app.sensitivity import SensitivityAnalysis
from app.matlab_generator_clean import MATLABCodeGenerator
from app.optimizer import ComponentOptimizer
from app.ollama_client import OllamaClient

load_dotenv()


RECTIFIER_CIRCUITS = {
    CircuitType.LINEAR_REGULATOR_WITH_BRIDGE_RECTIFIER,
    CircuitType.ZENER_REGULATOR_WITH_BRIDGE_RECTIFIER,
}


def _resource_dir(*parts: str) -> Path:
    """Resolve project resources in both source-tree and Nuitka standalone builds."""
    candidates = [Path(__file__).resolve().parent.parent, Path(__file__).resolve().parent]
    if hasattr(sys, "_MEIPASS"):
        candidates.insert(0, Path(sys._MEIPASS))
    candidates.extend([Path(sys.executable).resolve().parent, Path.cwd()])
    for base_dir in candidates:
        candidate = base_dir.joinpath(*parts)
        if candidate.exists():
            return candidate
    return candidates[0].joinpath(*parts)


def _frontend_file_response(path: Path, media_type: Optional[str] = None):
    from fastapi.responses import FileResponse
    response = FileResponse(path, media_type=media_type)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _format_capacitance_value(c_farads: Optional[float]) -> Optional[str]:
    if c_farads is None:
        return None
    return ComponentOptimizer._format_capacitance(c_farads)


def _rows_to_csv(rows: list[dict]) -> str:
    """Serialize export rows without pulling a dataframe engine into the binary."""
    if not rows:
        return ""
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _build_zener_optimization_options(
    series_resistor_ohms: float,
    filter_capacitor_farads: float,
    target_output_voltage: Optional[float],
    load_resistance_ohms: Optional[float],
    secondary_voltage_rms: Optional[float],
    line_frequency_hz: Optional[float],
    diode_forward_voltage: Optional[float],
    line_tolerance_percent: Optional[float]
) -> list[dict]:
    """Return practical Zener regulator alternatives ranked by safety margin."""
    target_vout = target_output_voltage or 5.0
    load_resistance = load_resistance_ohms or 100.0
    secondary_rms = secondary_voltage_rms or 12.0
    line_frequency = line_frequency_hz or 60.0
    diode_drop = diode_forward_voltage or 0.7
    line_tolerance = line_tolerance_percent or 5.0
    rectifier_frequency = line_frequency * 2.0
    load_current = target_vout / load_resistance
    target_min_zener_current = 0.005

    candidate_rs = ComponentOptimizer.get_e24_resistors_in_range(
        max(series_resistor_ohms * 0.7, 10.0),
        max(series_resistor_ohms * 2.0, series_resistor_ohms + 10.0),
        decade_limit=100000
    )
    candidate_cs = sorted(
        {
            cap for cap in ComponentOptimizer.STANDARD_CAPS
            if 1e-6 <= cap <= 10000e-6 and cap >= min(filter_capacitor_farads, 1000e-6)
        },
        key=lambda cap: cap
    )

    if not candidate_rs:
        candidate_rs = [ComponentOptimizer.find_closest_e24(max(series_resistor_ohms, 10.0))]
    if not candidate_cs:
        candidate_cs = [filter_capacitor_farads]

    scored = []
    for r_value in candidate_rs:
        for c_value in candidate_cs:
            vin_rms_min = secondary_rms * (1 - line_tolerance / 100.0)
            vin_rms_max = secondary_rms * (1 + line_tolerance / 100.0)
            vpeak_min = vin_rms_min * (2 ** 0.5) - 2 * diode_drop
            vpeak_max = vin_rms_max * (2 ** 0.5) - 2 * diode_drop
            ripple = load_current / max(rectifier_frequency * c_value, 1e-12)
            vfiltered_min = vpeak_min - ripple / 2.0
            vfiltered_max = vpeak_max - ripple / 2.0
            i_total_full = max((vfiltered_min - target_vout) / r_value, 0.0)
            i_zener_full = max(i_total_full - load_current, 0.0)
            i_zener_noload = max((vfiltered_max - target_vout) / r_value, 0.0)
            p_zener_noload = target_vout * i_zener_noload
            p_resistor_noload = ((vfiltered_max - target_vout) ** 2) / r_value if vfiltered_max > target_vout else 0.0
            p_resistor_full = ((vfiltered_min - target_vout) ** 2) / r_value if vfiltered_min > target_vout else 0.0
            resistor_error = abs(r_value - series_resistor_ohms) / max(series_resistor_ohms, 1e-9)
            capacitor_gain = max(c_value / max(filter_capacitor_farads, 1e-12), 1.0)
            regulation_penalty = max(target_min_zener_current - i_zener_full, 0.0) * 400.0
            zener_power_penalty = max(p_zener_noload - 0.75, 0.0) * 6.0
            resistor_power_penalty = max(max(p_resistor_noload, p_resistor_full) - 0.8, 0.0) * 4.0
            ripple_penalty = ripple / 0.5
            score = (
                regulation_penalty +
                zener_power_penalty +
                resistor_power_penalty +
                ripple_penalty +
                (resistor_error * 0.2) -
                (min(capacitor_gain - 1.0, 3.0) * 0.08)
            )
            safe_at_full_load = i_zener_full >= target_min_zener_current
            recommended_resistor_watts = max(1, int(np.ceil(max(p_resistor_noload, p_resistor_full) / 0.6)))
            recommended_zener_watts = max(1, int(np.ceil(p_zener_noload / 0.6)))
            scored.append({
                "series_resistor_value": r_value,
                "series_resistor_display": ComponentOptimizer._format_resistance(r_value),
                "filter_capacitor_farads": c_value,
                "filter_capacitor_display": ComponentOptimizer._format_capacitance(c_value),
                "output_voltage": target_vout,
                "estimated_ripple_voltage": ripple,
                "estimated_full_load_zener_current": i_zener_full,
                "estimated_no_load_zener_current": i_zener_noload,
                "estimated_no_load_zener_power": p_zener_noload,
                "estimated_resistor_power": max(p_resistor_noload, p_resistor_full),
                "recommended_resistor_watts": recommended_resistor_watts,
                "recommended_zener_watts": recommended_zener_watts,
                "safe_at_full_load": safe_at_full_load,
                "score": score,
                "reasoning": (
                    f"{'Maintains' if safe_at_full_load else 'Misses'} full-load regulation target with "
                    f"{i_zener_full * 1000:.1f} mA zener current, ripple about {ripple:.3f} Vpp, "
                    f"no-load zener dissipation {p_zener_noload:.2f} W, and resistor dissipation "
                    f"up to {max(p_resistor_noload, p_resistor_full):.2f} W."
                )
            })

    scored.sort(
        key=lambda option: (
            0 if option["safe_at_full_load"] else 1,
            option["score"],
            option["estimated_no_load_zener_power"],
            option["estimated_resistor_power"],
            -option["filter_capacitor_farads"]
        )
    )
    unique = []
    seen = set()
    for option in scored:
        key = (option["series_resistor_value"], option["filter_capacitor_farads"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(option)
        if len(unique) == 4:
            break
    return unique


def _normalize_zener_worst_case_analysis(analysis: dict) -> dict:
    """Flatten Zener worst-case extremes into the generic analysis_data shape used by the UI."""
    extremes = analysis.get("extremes", {})
    mapping = {
        "input_voltage_ac": "input_voltage_ac",
        "peak_voltage": "peak_voltage",
        "ripple_voltage": "ripple_voltage",
        "filtered_dc": "filtered_dc_voltage",
        "output_voltage": "output_voltage",
        "load_current": "load_current",
        "zener_current": "zener_current",
        "zener_power": "zener_power",
        "series_resistor_power": "series_resistor_power",
    }

    normalized = {}
    for source_key, target_key in mapping.items():
        metric = extremes.get(source_key)
        if not metric:
            continue
        min_value = metric.get("min")
        max_value = metric.get("max")
        nominal = metric.get("nominal")
        normalized[target_key] = {
            "nominal": nominal,
            "minimum": min_value,
            "maximum": max_value,
            "absolute_min": min_value,
            "absolute_max": max_value
        }

    if "worst_case_scenarios" in analysis:
        normalized["worst_case_scenarios"] = analysis["worst_case_scenarios"]
    if "nominal" in analysis:
        normalized["nominal_operating_point"] = analysis["nominal"]
    if "corners" in analysis:
        normalized["corner_cases"] = analysis["corners"]
    return normalized


def _normalize_circuit_type(circuit_type_input: str) -> str:
    """Normalize user-provided circuit type strings to match CircuitType enum values."""
    if not circuit_type_input:
        return circuit_type_input
    
    # Try direct match first
    for ct in CircuitType:
        if ct.value == circuit_type_input:
            return circuit_type_input
    
    # Normalize common variations
    normalized = circuit_type_input.strip().upper().replace(' ', '_').replace('-', '_')
    
    # Map common user inputs to enum values
    mapping = {
        "RC_LOW_PASS": CircuitType.RC_LOW_PASS,
        "RC_LOWPASS": CircuitType.RC_LOW_PASS,
        "RC_LOW-PASS": CircuitType.RC_LOW_PASS,
        "LOWPASS": CircuitType.RC_LOW_PASS,
        "LOW_PASS": CircuitType.RC_LOW_PASS,
        "RC_HIGH_PASS": CircuitType.RC_HIGH_PASS,
        "RC_HIGHPASS": CircuitType.RC_HIGH_PASS,
        "RC_HIGH-PASS": CircuitType.RC_HIGH_PASS,
        "HIGHPASS": CircuitType.RC_HIGH_PASS,
        "HIGH_PASS": CircuitType.RC_HIGH_PASS,
        "RC_CHARGING": CircuitType.RC_CHARGING,
        "CHARGING": CircuitType.RC_CHARGING,
        "NON_INVERTING_OPAMP": CircuitType.NON_INVERTING_OPAMP,
        "NON_INVERTING": CircuitType.NON_INVERTING_OPAMP,
        "NONINVERTING": CircuitType.NON_INVERTING_OPAMP,
        "INVERTING_OPAMP": CircuitType.INVERTING_OPAMP,
        "INVERTING": CircuitType.INVERTING_OPAMP,
        "ACTIVE_OPAMP_FILTER": CircuitType.ACTIVE_OPAMP_FILTER,
        "ACTIVE_FILTER": CircuitType.ACTIVE_OPAMP_FILTER,
        "OPAMP_FILTER": CircuitType.ACTIVE_OPAMP_FILTER,
    }
    
    return mapping.get(normalized, circuit_type_input)


def _normalize_input_voltage(circuit_type: CircuitType, voltage_type: str, voltage_value: Optional[float]) -> Optional[float]:
    """Convert AC RMS to peak only for circuits that expect a peak-domain input."""
    if voltage_value is None:
        return None
    if voltage_type == "AC_RMS" and circuit_type not in RECTIFIER_CIRCUITS:
        return voltage_value * (2 ** 0.5)
    return voltage_value


def _resolve_rectifier_input(
    voltage_value: Optional[float],
    primary_voltage_rms: Optional[float],
    secondary_voltage_rms: Optional[float],
    transformer_turns_ratio: Optional[float]
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Resolve the RMS secondary voltage used by the rectifier stage."""
    if secondary_voltage_rms is not None:
        resolved_secondary = secondary_voltage_rms
    elif primary_voltage_rms is not None and transformer_turns_ratio:
        resolved_secondary = primary_voltage_rms / transformer_turns_ratio
    else:
        resolved_secondary = voltage_value

    resolved_primary = primary_voltage_rms if primary_voltage_rms is not None else voltage_value
    resolved_turns = transformer_turns_ratio
    return resolved_secondary, resolved_primary, resolved_turns


app = FastAPI(
    title="Circuit Design & Robustness Analysis Platform",
    version="2.0.0",
    description="Educational circuit design tool with Monte Carlo and worst-case analysis",
    docs_url=None if os.getenv("DISABLE_API_DOCS", "").lower() in {"1", "true", "yes"} else "/docs",
    redoc_url=None if os.getenv("DISABLE_API_DOCS", "").lower() in {"1", "true", "yes"} else "/redoc",
)

# The packaged app is intentionally local-only by default. A deployment that needs
# network access must opt in explicitly and should also set BACKEND_API_KEY.
allowed_origins = [origin.strip() for origin in os.getenv(
    "ALLOWED_ORIGINS",
    "http://127.0.0.1:8000,http://localhost:8000"
).split(",") if origin.strip()]
api_key = os.getenv("BACKEND_API_KEY", "").strip()
max_body_bytes = int(os.getenv("MAX_REQUEST_BYTES", str(2 * 1024 * 1024)))
rate_limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
rate_window_seconds = 60.0
request_times: dict[str, deque[float]] = defaultdict(deque)
rate_lock = threading.Lock()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def protect_backend(request: Request, call_next):
    """Apply transport-independent protections before endpoint execution."""
    client_host = request.client.host if request.client else "unknown"
    if api_key and not secrets.compare_digest(request.headers.get("X-API-Key", ""), api_key):
        return JSONResponse(status_code=401, content={"detail": "Authentication required"})

    declared_length = request.headers.get("content-length")
    if declared_length:
        try:
            if int(declared_length) > max_body_bytes:
                return JSONResponse(status_code=413, content={"detail": "Request body too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid content length"})

    now = time.monotonic()
    with rate_lock:
        timestamps = request_times[client_host]
        while timestamps and now - timestamps[0] >= rate_window_seconds:
            timestamps.popleft()
        if len(timestamps) >= rate_limit:
            return JSONResponse(status_code=429, content={"detail": "Too many requests"})
        timestamps.append(now)

    if request.method in {"POST", "PUT", "PATCH"}:
        body = await request.body()
        if len(body) > max_body_bytes:
            return JSONResponse(status_code=413, content={"detail": "Request body too large"})

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Avoid returning stack traces or internal paths to API clients."""
    logging.exception("Unhandled backend error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Initialize clients
ollama = OllamaClient()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "2.0.0"}


@app.get("/")
async def root():
    """Serve the unified frontend index.html."""
    frontend_dir = _resource_dir("frontend")
    index_file = frontend_dir / "index_unified.html"
    if index_file.exists():
        return _frontend_file_response(index_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="Frontend not found")


@app.get("/frontend/")
async def frontend_index():
    """Serve frontend index when accessing /frontend/"""
    frontend_dir = _resource_dir("frontend")
    index_file = frontend_dir / "index_unified.html"
    if index_file.exists():
        return _frontend_file_response(index_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="Frontend not found")


@app.get("/frontend/styles_unified.css")
async def frontend_styles():
    """Serve CSS file"""
    frontend_dir = _resource_dir("frontend")
    css_file = frontend_dir / "styles_unified.css"
    if css_file.exists():
        return _frontend_file_response(css_file, media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS not found")


@app.post("/design", response_model=CircuitDesignResponse)
async def design_circuit(request: CircuitDesignRequest):
    """Design circuit using deterministic analytical synthesis."""
    try:
        engine = DeterministicDesign()
        # Normalize input voltage based on voltage_type
        input_v = _normalize_input_voltage(
            request.circuit_type,
            request.voltage_type,
            request.voltage_value
        )
        output_v = request.output_voltage
        # Calculate design as before
        if request.circuit_type == CircuitType.RC_LOW_PASS:
            design = engine.design_rc_low_pass(
                request.cutoff_frequency,
                input_v if input_v is not None else 1.0,
                request.resistor_ohms,
                request.capacitor_farads
            )
        elif request.circuit_type == CircuitType.RC_HIGH_PASS:
            design = engine.design_rc_high_pass(
                request.cutoff_frequency,
                input_v if input_v is not None else 1.0,
                request.resistor_ohms,
                request.capacitor_farads
            )
        elif request.circuit_type == CircuitType.RC_CHARGING:
            design = engine.design_rc_charging(
                request.time_duration or 1.0,
                input_v if input_v is not None else 1.0,
                request.resistor_ohms,
                request.capacitor_farads
            )
        elif request.circuit_type == CircuitType.NON_INVERTING_OPAMP:
            design = engine.design_non_inverting_opamp(
                request.gain_setting or 10.0,
                request.cutoff_frequency,
                input_v,
                request.resistor_ohms,
                request.resistor_ohms_2
            )
        elif request.circuit_type == CircuitType.INVERTING_OPAMP:
            design = engine.design_inverting_opamp(
                request.gain_setting or 10.0,
                request.cutoff_frequency,
                input_v,
                request.resistor_ohms,
                request.resistor_ohms_2
            )
        elif request.circuit_type == CircuitType.ACTIVE_OPAMP_FILTER:
            design = engine.design_opamp_active_filter(
                request.cutoff_frequency,
                request.gain_setting or 1.0,
                is_inverting=request.is_inverting or False,
                capacitor_farads=request.capacitor_farads
            )
        elif request.circuit_type == CircuitType.LINEAR_REGULATOR_WITH_BRIDGE_RECTIFIER:
            resolved_secondary, resolved_primary, resolved_turns = _resolve_rectifier_input(
                request.voltage_value,
                request.primary_voltage_rms,
                request.secondary_voltage_rms,
                request.transformer_turns_ratio
            )
            design = engine.design_linear_regulator_with_bridge_rectifier(
                input_ac_voltage=resolved_secondary if resolved_secondary is not None else 12.0,
                output_voltage=output_v if output_v is not None else 5.0,
                load_current=request.load_current or 0.5,
                dropout_voltage=request.dropout_voltage or 0.2,
                ripple_voltage=request.ripple_voltage or 0.5,
                line_frequency_hz=request.line_frequency_hz or 60.0,
                diode_forward_voltage=request.diode_forward_voltage or 0.7,
                primary_voltage_rms=resolved_primary,
                secondary_voltage_rms=resolved_secondary,
                transformer_turns_ratio=resolved_turns
            )
        elif request.circuit_type == CircuitType.ZENER_REGULATOR_WITH_BRIDGE_RECTIFIER:
            resolved_secondary, resolved_primary, resolved_turns = _resolve_rectifier_input(
                request.voltage_value,
                request.primary_voltage_rms,
                request.secondary_voltage_rms,
                request.transformer_turns_ratio
            )
            design = engine.design_zener_regulator_with_bridge_rectifier(
                input_ac_voltage=resolved_secondary if resolved_secondary is not None else 12.0,
                output_voltage=output_v if output_v is not None else 5.0,
                load_resistance=request.load_resistance or 100.0,
                min_zener_current=request.min_zener_current or 5.0,
                series_resistor_ohms=request.resistor_ohms,
                filter_capacitor_farads=request.capacitor_farads,
                line_frequency_hz=request.line_frequency_hz or 60.0,
                diode_forward_voltage=request.diode_forward_voltage or 0.7,
                primary_voltage_rms=resolved_primary,
                secondary_voltage_rms=resolved_secondary,
                transformer_turns_ratio=resolved_turns
            )
        else:
            raise ValueError(f"Unknown circuit type: {request.circuit_type}")

        # For RC filters, calculate output voltage if not provided
        if output_v is None and request.circuit_type in [CircuitType.RC_LOW_PASS, CircuitType.RC_HIGH_PASS]:
            # Use amplitude response at cutoff frequency as example
            R = design.get("resistor_ohms")
            C = design.get("capacitor_farads")
            fc = design.get("cutoff_frequency")
            Vin = input_v if input_v is not None else 1.0
            if R and C and fc and Vin:
                import math
                w = 2 * math.pi * fc
                denom = math.sqrt(1 + (w * R * C) ** 2)
                output_v = Vin / denom
        # If still not set, fallback to design or input
        if output_v is None:
            output_v = design.get("output_voltage", input_v)

        return CircuitDesignResponse(
            circuit_type=request.circuit_type,
            resistor_ohms=design.get("resistor_ohms"),
            resistor_ohms_2=design.get("resistor_ohms_2"),
            capacitor_farads=design.get("capacitor_farads"),
            resistor_display=design.get("resistor_display"),
            resistor_display_2=design.get("resistor_display_2"),
            capacitor_display=design.get("capacitor_display"),
            gain=design.get("gain", 1.0),
            transfer_function=design.get("transfer_function"),
            cutoff_frequency=design.get("cutoff_frequency"),
            time_constant=design.get("time_constant"),
            output_voltage=output_v,
            input_voltage=design.get("input_voltage", input_v),
            voltage_value=input_v,
            derivation=design.get("derivation", []),
            # Linear regulator fields
            series_resistor_ohms=design.get("series_resistor_ohms"),
            series_resistor_display=design.get("series_resistor_display"),
            filter_capacitor_farads=design.get("filter_capacitor_farads"),
            filter_capacitor_display=design.get("filter_capacitor_display"),
            zener_voltage=design.get("zener_voltage"),
            zener_current=design.get("zener_current"),
            peak_input_voltage=design.get("peak_input_voltage"),
            load_current=design.get("load_current"),
            dropout_voltage=design.get("dropout_voltage"),
            # Zener regulator fields
            zener_diode_voltage=design.get("zener_diode_voltage"),
            zener_diode_power=design.get("zener_diode_power"),
            series_resistor_value=design.get("series_resistor_value"),
            series_resistor_power=design.get("series_resistor_power"),
            load_resistor_value=design.get("load_resistor_value"),
            no_load_current=design.get("no_load_current"),
            full_load_current=design.get("full_load_current"),
            primary_voltage_rms=design.get("primary_voltage_rms"),
            secondary_voltage_rms=design.get("secondary_voltage_rms"),
            transformer_turns_ratio=design.get("transformer_turns_ratio"),
            line_frequency_hz=design.get("line_frequency_hz"),
            diode_forward_voltage=design.get("diode_forward_voltage")
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/optimize")
async def optimize_components(request: dict):
    """Optimize component values to practical E24/standard values while maintaining specs."""
    try:
        circuit_type_input = request.get("circuit_type")
        resistor_ohms = request.get("resistor_ohms", 10000)
        resistor_ohms_2 = request.get("resistor_ohms_2")
        capacitor_farads = request.get("capacitor_farads", 1e-6)
        target_frequency = request.get("target_frequency")
        target_gain = request.get("target_gain")
        target_output_voltage = request.get("output_voltage")
        load_resistance = request.get("load_resistance")
        primary_voltage_rms = request.get("primary_voltage_rms")
        secondary_voltage_rms = request.get("secondary_voltage_rms")
        transformer_turns_ratio = request.get("transformer_turns_ratio")
        line_frequency_hz = request.get("line_frequency_hz")
        diode_forward_voltage = request.get("diode_forward_voltage")
        line_tolerance_percent = request.get("line_tolerance_percent")
        
        # Normalize circuit type input to match enum
        circuit_type = _normalize_circuit_type(circuit_type_input)
        
        optimizer = ComponentOptimizer()
        
        if circuit_type in [CircuitType.RC_LOW_PASS, CircuitType.RC_HIGH_PASS, CircuitType.ACTIVE_OPAMP_FILTER]:

            from app.optimizer_alternatives import optimize_for_frequency_alternatives
            all_alternatives = optimize_for_frequency_alternatives(
                resistor_ohms, capacitor_farads, target_frequency, circuit_type, num_options=None
            )
            # Always return between 3 and 4 options (top scoring)
            num_to_return = min(4, max(3, len(all_alternatives)))
            # Ensure all alternatives have numeric resistor_ohms and capacitor_farads fields
            alternatives = []
            for alt in all_alternatives[:num_to_return]:
                alt_copy = dict(alt)
                # Try to extract numeric values from display if missing
                if 'resistor_ohms' not in alt_copy and 'resistor_display' in alt_copy:
                    try:
                        alt_copy['resistor_ohms'] = float(str(alt_copy['resistor_display']).replace('Ω','').replace('k','e3').replace('M','e6').replace(' ','').replace(',',''))
                    except Exception:
                        pass
                if 'capacitor_farads' not in alt_copy and 'capacitor_display' in alt_copy:
                    try:
                        val = str(alt_copy['capacitor_display']).replace('F','').replace('μ','e-6').replace('u','e-6').replace('n','e-9').replace('p','e-12').replace(' ','').replace(',','')
                        alt_copy['capacitor_farads'] = float(val)
                    except Exception:
                        pass
                alternatives.append(alt_copy)
            # Simplified 4-step prompt that Llama will actually respond to
            optimization_guidance = (
                "Analyze the BEST option (lowest score) using these 4 steps:\n\n"
                "STEP 1: Resistor optimality - thermal noise reduction and signal quality\n"
                "STEP 2: Capacitor optimality - frequency accuracy and settling time calculation\n"
                "STEP 3: Score analysis with comparisons to 2+ alternative options\n"
                "STEP 4: Real-world benefits including power dissipation, availability, and PCB advantages\n\n"
                "Show all calculations with actual numbers from the table. Include formulas and explain your reasoning."
            )

            try:
                recommendation = ollama.recommend_optimized_option(alternatives, circuit_type, guidance=optimization_guidance)
            except Exception:
                recommendation = "Recommendation unavailable"

            # Return all options, reasoning, and model recommendation
            return {
                "circuit_type": circuit_type,
                "optimized_options": alternatives,
                "derivation": [opt["reasoning"] for opt in alternatives],
                "recommendation": recommendation
            }
        elif circuit_type in [CircuitType.NON_INVERTING_OPAMP, CircuitType.INVERTING_OPAMP]:
            # For op-amps, optimize_for_gain takes (nominal_r_feedback, nominal_r_input, target_gain)
            # If resistor_ohms is not provided, use 1k as default for input resistor
            r_input = resistor_ohms if resistor_ohms and resistor_ohms > 0 else 1000.0
            # If resistor_ohms_2 is not provided, compute from target gain
            r_feedback = resistor_ohms_2 if resistor_ohms_2 and resistor_ohms_2 > 0 else ((target_gain or 10.0) - 1.0) * r_input if target_gain else 10000.0
            optimized = optimizer.optimize_for_gain(r_feedback, r_input, target_gain or 10.0)
            return {
                "circuit_type": circuit_type,
                "resistor_ohms": optimized.get("resistor_input_ohms"),
                "resistor_ohms_2": optimized.get("resistor_feedback_ohms"),
                "resistor_display": optimized.get("resistor_input_display"),
                "resistor_display_2": optimized.get("resistor_feedback_display"),
                "gain": optimized.get("gain"),
                "target_gain": optimized.get("target_gain"),
                "gain_error_percent": optimized.get("gain_error_percent"),
                "optimization_notes": optimized.get("optimization_notes", []),
                "derivation": optimized.get("optimization_notes", [])
            }
        elif circuit_type == CircuitType.ZENER_REGULATOR_WITH_BRIDGE_RECTIFIER:
            nominal_rs = resistor_ohms if resistor_ohms and resistor_ohms > 0 else 33.0
            nominal_c = capacitor_farads if capacitor_farads and capacitor_farads > 0 else 2200e-6
            resolved_secondary, _, _ = _resolve_rectifier_input(
                None,
                primary_voltage_rms,
                secondary_voltage_rms,
                transformer_turns_ratio
            )
            optimized_options = _build_zener_optimization_options(
                nominal_rs,
                nominal_c,
                target_output_voltage,
                load_resistance,
                resolved_secondary,
                line_frequency_hz,
                diode_forward_voltage,
                line_tolerance_percent
            )
            top_option = optimized_options[0] if optimized_options else None
            if top_option:
                recommendation = (
                    f"Option 1 is the safest practical match for a {target_output_voltage or 5.0:.1f}V Zener supply. "
                    f"It keeps about {top_option.get('estimated_full_load_zener_current', 0.0) * 1000:.1f} mA "
                    f"through the Zener at full load and suggests at least "
                    f"{top_option.get('recommended_resistor_watts', 1)} W resistor and "
                    f"{top_option.get('recommended_zener_watts', 1)} W Zener ratings."
                )
            else:
                recommendation = (
                    f"Option 1 is the safest practical match for a {target_output_voltage or 5.0:.1f}V Zener supply. "
                    f"It prioritizes full-load regulation margin and lower no-load dissipation."
                )
            try:
                model_recommendation = ollama.recommend_optimized_option(
                    optimized_options,
                    circuit_type,
                    guidance=(
                        "Choose the best Zener regulator option by prioritizing safe full-load regulation, "
                        "lower no-load zener power, lower resistor stress, and practical capacitor margin."
                    )
                )
                if model_recommendation:
                    recommendation = model_recommendation
            except Exception:
                pass

            return {
                "circuit_type": circuit_type,
                "optimized_options": optimized_options,
                "derivation": [opt["reasoning"] for opt in optimized_options],
                "recommendation": recommendation
            }
        else:
            raise ValueError(f"Cannot optimize circuit type: {circuit_type}")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/montecarlo", response_model=MonteCarloResponse)
async def run_monte_carlo(request: MonteCarloRequest):
    """Run Monte Carlo analysis with user-defined tolerances."""
    try:
        logging.info("[MonteCarlo DEBUG] Incoming request: %s", request.dict())
        mc = MonteCarloAnalysis()
        # Normalize input voltage based on voltage_type
        input_v = _normalize_input_voltage(
            request.circuit_type,
            request.voltage_type,
            request.voltage_value
        )
        
        # For op-amp circuits, provide a sensible capacitor default if not specified
        capacitor_f = request.capacitor_farads if request.capacitor_farads is not None else 1e-6
        
        if request.circuit_type == CircuitType.RC_LOW_PASS:
            results = mc.simulate_rc_low_pass(
                request.resistor_ohms,
                capacitor_f,
                input_v,
                request.num_samples,
                request.r1_tolerance_percent,
                request.capacitor_tolerance_percent,
                request.line_fluctuation_percent,
                request.voltage_type,
                test_frequency=request.cutoff_frequency
            )
        elif request.circuit_type == CircuitType.RC_HIGH_PASS:
            results = mc.simulate_rc_high_pass(
                request.resistor_ohms,
                capacitor_f,
                input_v,
                request.num_samples,
                request.r1_tolerance_percent,
                request.capacitor_tolerance_percent,
                request.line_fluctuation_percent,
                request.voltage_type,
                test_frequency=request.cutoff_frequency
            )
        elif request.circuit_type == CircuitType.RC_CHARGING:
            results = mc.simulate_rc_charging(
                request.resistor_ohms,
                capacitor_f,
                input_v,
                request.num_samples,
                request.r1_tolerance_percent,
                request.capacitor_tolerance_percent,
                request.line_fluctuation_percent,
                request.time_duration or 1.0,
                request.voltage_type
            )
        elif request.circuit_type in [CircuitType.NON_INVERTING_OPAMP, CircuitType.INVERTING_OPAMP, CircuitType.ACTIVE_OPAMP_FILTER]:
            results = mc.simulate_opamp_gain(
                request.circuit_type,
                request.gain_setting or 10.0,
                input_v,
                request.num_samples,
                request.r1_tolerance_percent,
                request.r2_tolerance_percent,
                request.capacitor_tolerance_percent,
                request.line_fluctuation_percent,
                request.resistor_ohms,
                request.resistor_ohms_2,
                request.capacitor_farads,
                request.cutoff_frequency
            )
        elif request.circuit_type == CircuitType.LINEAR_REGULATOR_WITH_BRIDGE_RECTIFIER:
            results = mc.simulate_linear_regulator_with_bridge_rectifier(
                input_ac_voltage=input_v,
                output_voltage=request.output_voltage or 5.0,
                filter_capacitor=request.capacitor_farads,
                series_resistor=request.resistor_ohms,
                zener_voltage=request.voltage_value + 1.0 if request.voltage_value else 6.0,
                load_current=request.load_current or 0.5,
                num_samples=request.num_samples,
                input_voltage_tolerance=request.line_fluctuation_percent,
                capacitor_tolerance=request.capacitor_tolerance_percent,
                resistor_tolerance=request.r1_tolerance_percent,
                load_current_tolerance=10.0  # Default tolerance
            )
        elif request.circuit_type == CircuitType.ZENER_REGULATOR_WITH_BRIDGE_RECTIFIER:
            resolved_secondary, _, _ = _resolve_rectifier_input(
                request.voltage_value,
                request.primary_voltage_rms,
                request.secondary_voltage_rms,
                request.transformer_turns_ratio
            )
            results = mc.simulate_zener_regulator_with_bridge_rectifier(
                input_ac_voltage=resolved_secondary if resolved_secondary is not None else input_v,
                output_voltage=request.output_voltage or 5.0,
                load_resistance=request.load_resistance or 100.0,
                series_resistor=request.resistor_ohms or 10.0,
                zener_voltage=request.output_voltage or 5.0,
                filter_capacitor=request.capacitor_farads or 4700e-6,
                num_samples=request.num_samples,
                ac_voltage_tolerance=request.line_fluctuation_percent,
                resistor_tolerance=request.r1_tolerance_percent,
                capacitor_tolerance=request.capacitor_tolerance_percent,
                load_tolerance=10.0,
                line_frequency_hz=request.line_frequency_hz or 60.0,
                diode_forward_voltage=request.diode_forward_voltage or 0.7
            )
        else:
            raise ValueError(f"Unknown circuit type: {request.circuit_type}")
        
        # Debug: Print all keys and types in results
        logging.info("[MonteCarlo DEBUG] Results object: %s", results)
        logging.info("MonteCarlo endpoint: Results keys and types:")
        for key, data in results.items():
            logging.info("  Key: %s, Type: %s", key, type(data))
        # Convert results to response format, only process dict values, skip lists and other types
        metrics = {}
        for key, data in results.items():
            # Skip non-dict items: raw_data, derivation, voltage_type, etc.
            if key in ["raw_data", "derivation", "voltage_type"]:
                continue
            if not isinstance(data, dict):
                logging.info("MonteCarlo endpoint: Skipping key '%s' of type %s", key, type(data))
                continue
            metrics[key] = MonteCarloMetric(
                mean=data.get("mean"),
                std_dev=data.get("std_dev"),
                min_value=data.get("min"),
                max_value=data.get("max"),
                percentile_5=data.get("percentile_5"),
                percentile_95=data.get("percentile_95"),
                absolute_min=data.get("absolute_min"),
                absolute_max=data.get("absolute_max")
            )
        # Ensure input_voltage is always present in metrics
        if "input_voltage" not in metrics:
            vin_values = results.get("raw_data", {}).get("vin_values")
            if vin_values:
                metrics["input_voltage"] = MonteCarloMetric(
                    mean=float(np.mean(vin_values)),
                    std_dev=float(np.std(vin_values)),
                    min_value=float(np.min(vin_values)),
                    max_value=float(np.max(vin_values)),
                    percentile_5=float(np.percentile(vin_values, 5)),
                    percentile_95=float(np.percentile(vin_values, 95)),
                    absolute_min=float(np.min(np.abs(vin_values))),
                    absolute_max=float(np.max(np.abs(vin_values)))
                )
        return MonteCarloResponse(
            circuit_type=request.circuit_type,
            num_samples=request.num_samples,
            r1_tolerance_percent=request.r1_tolerance_percent,
            r2_tolerance_percent=request.r2_tolerance_percent,
            capacitor_tolerance_percent=request.capacitor_tolerance_percent,
            line_fluctuation_percent=request.line_fluctuation_percent,
            metrics=metrics,
            raw_data=results.get("raw_data", {})
        )
    
    except Exception as e:
        import traceback
        logging.error("[MonteCarlo ERROR] Exception occurred: %s", str(e))
        logging.error(traceback.format_exc())
        try:
            logging.error("[MonteCarlo ERROR] Last results object: %s", results)
        except Exception:
            logging.error("[MonteCarlo ERROR] No results object available.")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/worstcase", response_model=WorstCaseResponse)
async def analyze_worst_case(request: WorstCaseRequest):
    """Analyze absolute worst-case corner variations."""
    try:
        wc = WorstCaseAnalysis()
        # Normalize input voltage based on voltage_type
        input_v = _normalize_input_voltage(
            request.circuit_type,
            request.voltage_type,
            request.voltage_value
        )
        
        # For op-amp circuits, provide a sensible capacitor default if not specified
        capacitor_f = request.capacitor_farads if request.capacitor_farads is not None else 1e-6
        
        if request.circuit_type == CircuitType.RC_LOW_PASS:
            analysis = wc.analyze_rc_low_pass(
                request.resistor_ohms,
                capacitor_f,
                input_v,
                request.r1_tolerance_percent,
                request.capacitor_tolerance_percent,
                request.line_fluctuation_percent,
                request.voltage_type,
                test_frequency=request.cutoff_frequency
            )
        elif request.circuit_type == CircuitType.RC_HIGH_PASS:
            analysis = wc.analyze_rc_high_pass(
                request.resistor_ohms,
                capacitor_f,
                input_v,
                request.r1_tolerance_percent,
                request.capacitor_tolerance_percent,
                request.line_fluctuation_percent,
                request.voltage_type,
                test_frequency=request.cutoff_frequency
            )
        elif request.circuit_type == CircuitType.RC_CHARGING:
            analysis = wc.analyze_rc_charging(
                request.resistor_ohms,
                capacitor_f,
                input_v,
                request.r1_tolerance_percent,
                request.capacitor_tolerance_percent,
                request.line_fluctuation_percent,
                request.time_duration or 1.0,
                request.voltage_type
            )
        elif request.circuit_type in [CircuitType.NON_INVERTING_OPAMP, CircuitType.INVERTING_OPAMP, CircuitType.ACTIVE_OPAMP_FILTER]:
            analysis = wc.analyze_opamp_gain(
                request.circuit_type,
                request.gain_setting or 10.0,
                input_v,
                request.r1_tolerance_percent,
                request.r2_tolerance_percent,
                request.capacitor_tolerance_percent,
                request.line_fluctuation_percent,
                request.resistor_ohms,
                request.resistor_ohms_2,
                request.capacitor_farads,
                request.cutoff_frequency
            )
        elif request.circuit_type == CircuitType.LINEAR_REGULATOR_WITH_BRIDGE_RECTIFIER:
            analysis = wc.analyze_linear_regulator_with_bridge_rectifier(
                input_ac_nominal=input_v,
                filter_capacitor_nominal=request.capacitor_farads,
                series_resistor_nominal=request.resistor_ohms,
                load_current_nominal=request.load_current or 0.5,
                output_voltage_target=request.output_voltage or 5.0,
                input_voltage_tolerance=request.line_fluctuation_percent,
                capacitor_tolerance=request.capacitor_tolerance_percent,
                resistor_tolerance=request.r1_tolerance_percent,
                load_current_tolerance=10.0  # Default tolerance
            )
        elif request.circuit_type == CircuitType.ZENER_REGULATOR_WITH_BRIDGE_RECTIFIER:
            resolved_secondary, _, _ = _resolve_rectifier_input(
                request.voltage_value,
                request.primary_voltage_rms,
                request.secondary_voltage_rms,
                request.transformer_turns_ratio
            )
            analysis = wc.analyze_zener_regulator_with_bridge_rectifier(
                input_ac_voltage=resolved_secondary if resolved_secondary is not None else input_v,
                output_voltage=request.output_voltage or 5.0,
                load_resistance=request.load_resistance or 100.0,
                series_resistor=request.resistor_ohms or 10.0,
                zener_voltage=request.output_voltage or 5.0,
                filter_capacitor=request.capacitor_farads or 4700e-6,
                ac_tolerance=request.line_fluctuation_percent,
                resistor_tolerance=request.r1_tolerance_percent,
                capacitor_tolerance=request.capacitor_tolerance_percent,
                load_tolerance=10.0,
                line_frequency_hz=request.line_frequency_hz or 60.0,
                diode_forward_voltage=request.diode_forward_voltage or 0.7
            )
            if isinstance(analysis, dict) and "analysis_data" in analysis:
                analysis["analysis_data"] = _normalize_zener_worst_case_analysis(analysis["analysis_data"])
            else:
                analysis = _normalize_zener_worst_case_analysis(analysis)
        else:
            raise ValueError(f"Unknown circuit type: {request.circuit_type}")
        
        if isinstance(analysis, dict) and "analysis_data" in analysis and "summary" in analysis:
            analysis_payload = analysis["analysis_data"]
            summary = analysis["summary"]
        else:
            analysis_payload = analysis
            summary = f"Worst-case analysis completed for {request.circuit_type}"

        return WorstCaseResponse(
            circuit_type=request.circuit_type,
            analysis_data=analysis_payload,
            summary=summary
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/matlab", response_model=MATLABCodeResponse)
async def generate_matlab(request: MATLABGenerationRequest):
    """Generate MATLAB code with Monte Carlo loop and actual analysis results."""
    try:
        generator = MATLABCodeGenerator()
        
        # Get actual MC and WC results to include in MATLAB code
        mc_results = None
        wc_results = None
        
        if request.circuit_type in [CircuitType.NON_INVERTING_OPAMP, CircuitType.INVERTING_OPAMP]:
            # Run MC analysis with explicit R1/R2 tolerance model
            mc_analyzer = MonteCarloAnalysis()
            mc_output = mc_analyzer.simulate_opamp_gain(
                circuit_type=request.circuit_type,
                gain_nominal=request.gain_setting or 10.0,
                vin_nominal=request.voltage_value,
                num_samples=request.num_samples,
                r1_tolerance=request.r1_tolerance_percent,
                r2_tolerance=request.r2_tolerance_percent,
                capacitor_tolerance=request.capacitor_tolerance_percent,
                line_fluctuation=request.line_fluctuation_percent,
                resistor_ohms=request.resistor_ohms,
                resistor_ohms_2=request.resistor_ohms_2
            )
            gain_stats = mc_output.get("gain", {})
            gain_values = mc_output.get("raw_data", {}).get("gain_values", [])
            gain_median = float(np.percentile(gain_values, 50)) if gain_values else float(gain_stats.get("mean", 0.0))
            mc_results = {
                "gain_min": float(gain_stats.get("min", 0.0)),
                "gain_median": gain_median,
                "gain_max": float(gain_stats.get("max", 0.0)),
                "gain_std": float(gain_stats.get("std_dev", 0.0)),
            }

            # Run WC analysis with explicit R1/R2 tolerance model
            wc_analyzer = WorstCaseAnalysis()
            wc_results = wc_analyzer.analyze_opamp_gain(
                circuit_type=request.circuit_type,
                gain_nominal=request.gain_setting or 10.0,
                vin_nominal=request.voltage_value,
                r1_tolerance=request.r1_tolerance_percent,
                r2_tolerance=request.r2_tolerance_percent,
                capacitor_tolerance=request.capacitor_tolerance_percent,
                line_fluctuation=request.line_fluctuation_percent,
                resistor_ohms=request.resistor_ohms,
                resistor_ohms_2=request.resistor_ohms_2
            )
        
        # Check if this is a linear regulator circuit
        if request.circuit_type == CircuitType.LINEAR_REGULATOR_WITH_BRIDGE_RECTIFIER:
            code = generator.generate_linear_regulator_analysis(
                input_ac_voltage=request.voltage_value,
                output_voltage=request.output_voltage or 5.0,
                filter_capacitor=request.capacitor_farads,
                series_resistor=request.resistor_ohms,
                load_current=request.load_current or 0.5,
                num_samples=request.num_samples,
                input_voltage_tolerance_percent=request.line_fluctuation_percent,
                capacitor_tolerance_percent=request.capacitor_tolerance_percent,
                r1_tolerance_percent=request.r1_tolerance_percent,
                load_current_tolerance_percent=10.0,  # Default
                line_frequency_hz=request.line_frequency_hz or 60.0,
                diode_forward_voltage=request.diode_forward_voltage or 0.7,
                primary_voltage_rms=request.primary_voltage_rms,
                secondary_voltage_rms=request.secondary_voltage_rms,
                transformer_turns_ratio=request.transformer_turns_ratio,
                dropout_voltage=request.dropout_voltage or 0.2,
            )
        elif request.circuit_type == CircuitType.ZENER_REGULATOR_WITH_BRIDGE_RECTIFIER:
            resolved_secondary, resolved_primary, resolved_turns = _resolve_rectifier_input(
                request.voltage_value,
                request.primary_voltage_rms,
                request.secondary_voltage_rms,
                request.transformer_turns_ratio
            )
            code = generator.generate_zener_regulator_analysis(
                input_ac_voltage=resolved_secondary if resolved_secondary is not None else request.voltage_value,
                output_voltage=request.output_voltage or 5.0,
                load_resistance=request.load_resistance or 100.0,
                series_resistor=request.resistor_ohms or 10.0,
                zener_voltage=request.output_voltage or 5.0,
                filter_capacitor=request.capacitor_farads or 4700e-6,
                num_samples=request.num_samples,
                ac_tolerance=request.line_fluctuation_percent,
                resistor_tolerance=request.r1_tolerance_percent,
                capacitor_tolerance=request.capacitor_tolerance_percent,
                load_tolerance=10.0,
                line_frequency_hz=request.line_frequency_hz or 60.0,
                diode_forward_voltage=request.diode_forward_voltage or 0.7,
                primary_voltage_rms=resolved_primary,
                secondary_voltage_rms=resolved_secondary,
                transformer_turns_ratio=resolved_turns
            )
        else:
            code = generator.generate_complete_analysis(
                request.circuit_type,
                request.resistor_ohms,
                request.resistor_ohms_2,
                request.capacitor_farads,
                request.voltage_value,
                request.num_samples,
                request.r1_tolerance_percent,
                request.r2_tolerance_percent,
                request.capacitor_tolerance_percent,
                request.line_fluctuation_percent,
                request.cutoff_frequency,
                request.gain_setting,
                mc_results=mc_results,
                wc_results=wc_results
            )
        
        # Post-process: remove newlines inside fprintf calls
        import re
        # Pattern: fprintf(' ... ') where ... may contain \n, but remove literal newlines within the string
        def fix_fprintf(code):
            """Remove literal newlines from within fprintf() calls"""
            lines = code.split('\n')
            result = []
            i = 0
            while i < len(lines):
                line = lines[i]
                # Check if this is a fprintf line that might continue to next line
                if 'fprintf(' in line and not line.rstrip().endswith(');'):
                    # This fprintf is incomplete, join with next lines until we find );
                    complete = line
                    i += 1
                    while i < len(lines) and not complete.rstrip().endswith(');'):
                        complete += ' ' + lines[i].strip()
                        i += 1
                    result.append(complete)
                else:
                    result.append(line)
                    i += 1
            return '\n'.join(result)
        
        code = fix_fprintf(code)
        
        return MATLABCodeResponse(
            circuit_type=request.circuit_type,
            matlab_code=code,
            description=f"Complete MATLAB code for {request.circuit_type} with Monte Carlo analysis"
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/export_csv", response_model=CSVExportResponse)
async def export_csv(request: dict):
    """Export complete analysis results: Deterministic, Optimized, MC samples, Worst-Case."""
    try:
        raw_data = request.get("raw_data", {})
        deterministic = request.get("deterministic", {})
        optimized = request.get("optimized")
        worst_case = request.get("worst_case")
        
        num_samples = len(raw_data.get("r_values", raw_data.get("gain_values", raw_data.get("vin_values", []))))
        
        rows = []
        
        if "r_values" in raw_data:
            # RC circuit data
            for i in range(num_samples):
                row = {
                    "Sample": i + 1,
                    # Deterministic
                    "DET_R_Ohms": deterministic.get("resistor_ohms", ""),
                    "DET_C_Farads": deterministic.get("capacitor_farads", ""),
                    "DET_fc_Hz": deterministic.get("cutoff_frequency", ""),
                }
                
                # Optimized
                if optimized:
                    row["OPT_R_Ohms"] = optimized.get("resistor_ohms", "")
                    row["OPT_C_Farads"] = optimized.get("capacitor_farads", "")
                    row["OPT_fc_Hz"] = optimized.get("cutoff_frequency", "")
                
                # MC samples
                row["MC_R_Ohms"] = raw_data["r_values"][i] if i < len(raw_data.get("r_values", [])) else ""
                row["MC_C_Farads"] = raw_data["c_values"][i] if i < len(raw_data.get("c_values", [])) else ""
                row["MC_Vin"] = raw_data["vin_values"][i] if i < len(raw_data.get("vin_values", [])) else ""
                row["MC_fc_Hz"] = raw_data["fc_values"][i] if i < len(raw_data.get("fc_values", [])) else ""
                row["MC_tau_s"] = raw_data["tau_values"][i] if i < len(raw_data.get("tau_values", [])) else ""
                
                # Worst-case (absolute extremes)
                if worst_case and worst_case.get("analysis_data"):
                    wc_data = worst_case["analysis_data"]
                    row["WC_R_min"] = wc_data.get("resistor", {}).get("min", "")
                    row["WC_R_max"] = wc_data.get("resistor", {}).get("max", "")
                    row["WC_C_min"] = wc_data.get("capacitor", {}).get("min", "")
                    row["WC_C_max"] = wc_data.get("capacitor", {}).get("max", "")
                    row["WC_fc_min"] = wc_data.get("cutoff_frequency", {}).get("min", "")
                    row["WC_fc_max"] = wc_data.get("cutoff_frequency", {}).get("max", "")
                
                rows.append(row)
        else:
            # Op-amp circuit data
            for i in range(num_samples):
                row = {
                    "Sample": i + 1,
                    "DET_Gain": deterministic.get("gain", ""),
                    "MC_Gain": raw_data.get("gain_values", [])[i] if i < len(raw_data.get("gain_values", [])) else "",
                    "MC_Vin": raw_data.get("vin_values", [])[i] if i < len(raw_data.get("vin_values", [])) else "",
                    "MC_Vout": raw_data.get("vout_values", [])[i] if i < len(raw_data.get("vout_values", [])) else "",
                    "MC_R1_Ohms": raw_data.get("r1_values", [])[i] if i < len(raw_data.get("r1_values", [])) else "",
                    "MC_R2_Ohms": raw_data.get("r2_values", [])[i] if i < len(raw_data.get("r2_values", [])) else "",
                }
                
                if optimized:
                    row["OPT_Gain"] = optimized.get("gain", "")
                
                if worst_case and worst_case.get("analysis_data"):
                    wc_data = worst_case["analysis_data"]
                    row["WC_Gain_min"] = wc_data.get("gain", {}).get("min", "")
                    row["WC_Gain_max"] = wc_data.get("gain", {}).get("max", "")
                    row["WC_Vout_min"] = wc_data.get("output_voltage", {}).get("min", "")
                    row["WC_Vout_max"] = wc_data.get("output_voltage", {}).get("max", "")
                    # Include worst-case resistor extremes when available
                    row["WC_R1_min"] = wc_data.get("resistor", {}).get("minimum", "")
                    row["WC_R1_max"] = wc_data.get("resistor", {}).get("maximum", "")
                    row["WC_R2_min"] = wc_data.get("resistor_2", {}).get("minimum", "")
                    row["WC_R2_max"] = wc_data.get("resistor_2", {}).get("maximum", "")
                
                rows.append(row)
        
            csv_string = _rows_to_csv(rows)
        
        return CSVExportResponse(
            csv_data=csv_string,
            filename=f"circuit_analysis_results.csv",
            num_rows=num_samples
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/download_csv")
async def download_csv(request: dict):
    """Download CSV for Nominal, MC, or WC table as requested by frontend."""
    from fastapi.responses import StreamingResponse
    try:
        export_type = request.get("type", "mc")
        # NOMINAL EXPORT
        if export_type == "nominal":
            deterministic = request.get("deterministic", {})
            optimized = request.get("optimized", {})
            # Compose a single-row CSV for nominal/optimized values
            row = {
                "Resistor (Ohms)": deterministic.get("resistor_ohms", ""),
                "Resistor (Display)": deterministic.get("resistor_display", ""),
                "Capacitor (Farads)": deterministic.get("capacitor_farads", ""),
                "Capacitor (Display)": deterministic.get("capacitor_display", ""),
                "Cutoff Freq (Hz)": deterministic.get("cutoff_frequency", ""),
                "Time Constant (s)": deterministic.get("time_constant", ""),
                "Gain": deterministic.get("gain", ""),
                "Output Voltage (V)": deterministic.get("output_voltage", ""),
            }
            if optimized:
                row.update({
                    "Optimized Resistor (Ohms)": optimized.get("resistor_ohms", ""),
                    "Optimized Resistor (Display)": optimized.get("resistor_display", ""),
                    "Optimized Capacitor (Farads)": optimized.get("capacitor_farads", ""),
                    "Optimized Capacitor (Display)": optimized.get("capacitor_display", ""),
                    "Optimized Cutoff Freq (Hz)": optimized.get("cutoff_frequency", ""),
                    "Optimized Gain": optimized.get("gain", ""),
                })
            csv_data = _rows_to_csv([row])
            return StreamingResponse(
                io.BytesIO(csv_data.encode()),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=nominal_results.csv"}
            )
        # MONTE CARLO EXPORT
        elif export_type == "mc":
            mc_results = request.get("mc_results", {})
            num_samples = request.get("num_samples", len(mc_results.get("raw_data", {}).get("r_values", [])))
            rows = []
            raw_data = mc_results.get("raw_data", {})
            # Support both RC-style and op-amp-style raw data (r1/r2)
            r_samples = raw_data.get("r_values", raw_data.get("r1_values", []))
            c_samples = raw_data.get("c_values", [])
            vin_samples = raw_data.get("vin_values", [])
            fc_samples = raw_data.get("fc_values", [])
            tau_samples = raw_data.get("tau_values", [])
            r2_samples = raw_data.get("r2_values", [])
            for i in range(num_samples):
                row = {
                    "Sample": i + 1,
                    "R_Ohms": r_samples[i] if i < len(r_samples) else "",
                    "R2_Ohms": r2_samples[i] if i < len(r2_samples) else "",
                    "C_Farads": c_samples[i] if i < len(c_samples) else "",
                    "Vin_V": vin_samples[i] if i < len(vin_samples) else "",
                    "fc_Hz": fc_samples[i] if i < len(fc_samples) else "",
                    "tau_s": tau_samples[i] if i < len(tau_samples) else "",
                }
                rows.append(row)
            csv_data = _rows_to_csv(rows)
            return StreamingResponse(
                io.BytesIO(csv_data.encode()),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=mc_results.csv"}
            )
        # WORST CASE EXPORT
        elif export_type == "wc":
            worst_case = request.get("worst_case", {})
            analysis_data = worst_case.get("analysis_data", {})
            # Flatten WC data for CSV
            rows = []
            for metric, values in analysis_data.items():
                row = {"Metric": metric}
                if isinstance(values, dict):
                    row.update({
                        "WC Stat Min": values.get("minimum", ""),
                        "WC Stat Max": values.get("maximum", ""),
                        "WC Abs Min": values.get("absolute_min", ""),
                        "WC Abs Max": values.get("absolute_max", ""),
                    })
                rows.append(row)
            csv_data = _rows_to_csv(rows)
            return StreamingResponse(
                io.BytesIO(csv_data.encode()),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=wc_results.csv"}
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown export type: {export_type}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/explain", response_model=ExplanationResponse)
async def explain_results(request: ExplanationRequest):
    """Get conceptual explanations from Ollama (no math)."""
    try:
        explanation = ollama.explain_circuit_concept(
            request.concept,
            request.circuit_type,
            request.context
        )
        
        return ExplanationResponse(
            concept=request.concept,
            explanation=explanation,
            source="Ollama Mistral"
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Catch-all: Serve frontend HTML for any unmatched routes
from fastapi.responses import FileResponse

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Serve frontend files or index_unified.html as fallback."""
    frontend_dir = _resource_dir("frontend").resolve()
    file_path = (frontend_dir / full_path).resolve()
    
    if frontend_dir in file_path.parents and file_path.exists() and file_path.is_file():
        media_type = None
        if file_path.suffix == ".html":
            media_type = "text/html"
        elif file_path.suffix == ".css":
            media_type = "text/css"
        return _frontend_file_response(file_path, media_type=media_type)
    
    # Fallback to index_unified.html for SPA routing
    index_file = frontend_dir / "index_unified.html"
    if index_file.exists():
        return _frontend_file_response(index_file, media_type="text/html")
    
    raise HTTPException(status_code=404, detail=f"File not found: {full_path}")


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("APP_HOST", os.getenv("API_HOST", "127.0.0.1"))
    port = int(os.getenv("APP_PORT", os.getenv("API_PORT", "8000")))
    if host not in {"127.0.0.1", "localhost", "::1"} and not api_key:
        raise RuntimeError("Refusing non-local binding without BACKEND_API_KEY")
    open_browser = os.getenv("OPEN_BROWSER", "true").lower() in {"1", "true", "yes"}
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}/")).start()
    uvicorn.run(app, host=host, port=port, server_header=False)
