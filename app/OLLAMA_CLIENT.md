# Ollama Client

This file documents the behavior of [`ollama_client.py`](./ollama_client.py), which provides the repo's lightweight integration with a local Ollama server for explanation and recommendation tasks.

## Purpose

`OllamaClient` is intentionally narrow in scope:

- It generates short educational circuit explanations.
- It can ask the model to rank and justify optimized RC options.
- It is not responsible for numerical circuit design, fitting, or deterministic analysis.

The deterministic math remains in the analysis and design modules. This client is only for language-model output.

## Default Configuration

- Base URL: `http://localhost:11434`
- API endpoint: `/api/generate`
- Default model: `llama3`
- Request mode: non-streaming (`"stream": false`)

## Class Overview

### `OllamaClient.__init__(base_url="http://localhost:11434")`

Initializes the client with:

- `self.base_url`
- `self.model = "llama3"`

If the Ollama host changes, update the constructor input or extend this class to read from environment configuration.

## Methods

### `explain_circuit_concept(concept, circuit_type, context=None) -> str`

Sends a prompt to Ollama asking for a concise educational explanation:

- audience: undergraduate electrical engineering students
- tone: simple and educational
- constraint: avoid complex math
- target length: about 100 to 150 words

If the Ollama request fails for any reason, the method falls back to `_get_fallback_explanation(...)`.

### `recommend_optimized_option(options, circuit_type, guidance=None) -> str`

Builds a Markdown-style table of candidate RC combinations and asks the model to:

- analyze the best option
- compare it against alternatives
- explain tradeoffs
- show reasoning in a structured way

Expected fields in each `options` item:

- `resistor_display`
- `capacitor_display`
- `cutoff_frequency`
- `frequency_error_percent`
- `score`

If no `guidance` string is provided, the method uses a default 4-step analysis prompt focused on resistor choice, capacitor choice, score comparison, and real-world tradeoffs.

If the request fails, it returns:

`Model unavailable — no recommendation generated.`

### `_get_fallback_explanation(concept, circuit_type) -> str`

Provides local hardcoded explanations for a small set of common concepts when Ollama is unavailable.

Current built-in fallback topics include:

- cutoff frequency in RC low-pass filters
- time constant in RC charging
- gain in op-amp circuits
- sensitivity in RC filters
- tolerance in components

If no exact fallback entry matches, the method returns a generic educational placeholder.

## Request Shape

Both networked methods send `POST` requests to:

```json
{
  "model": "llama3",
  "prompt": "...",
  "stream": false
}
```

The code expects Ollama's JSON response to include a top-level `response` field.

## Failure Behavior

The client is designed to degrade safely:

- HTTP errors return a readable service-status message in some paths.
- network failures or unexpected exceptions trigger fallback behavior.
- explanation flow has local educational backups.
- recommendation flow returns a clear unavailable message instead of raising.

This keeps the rest of the API usable even when Ollama is offline.

## Constraints and Design Intent

- No symbolic or deterministic math should be delegated to Ollama.
- No core circuit sizing logic should move into this client.
- Prompts should stay educational, review-oriented, or comparative.
- Keep latency reasonable; current timeouts are 30s for explanations and 120s for recommendations.

## Known Follow-Ups

Potential improvements if this client grows:

- read model name from `.env`
- read base URL from `.env`
- add structured logging for Ollama failures
- normalize circuit type labels before prompting
- add retry/backoff for transient connection failures
- add tests around fallback behavior and malformed option payloads

## Related Files

- [`app/ollama_client.py`](./ollama_client.py)
- [`README.md`](../README.md)
- [`DEVELOPER_NOTES.md`](../DEVELOPER_NOTES.md)
- [`PLATFORM_DOCUMENTATION.md`](../PLATFORM_DOCUMENTATION.md)
- [`INTERFACE_DOCUMENTATION.md`](../INTERFACE_DOCUMENTATION.md)
