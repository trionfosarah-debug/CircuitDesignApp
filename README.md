# CircuitDesignApp

Standalone release of the Circuit Design & Robustness Analysis Platform.

## Download and run

This release contains a native **macOS arm64** executable built with Nuitka.

1. Download `CircuitDesignApp`.
2. Make it executable if needed: `chmod +x CircuitDesignApp`
3. Launch it from Terminal or Finder.
4. Open `http://127.0.0.1:8000` if the browser does not open automatically.

The app runs locally by default and does not require Python installation.
Ollama is optional and is used only for AI explanations and recommendations.

## Backend protections

The bundled backend:

- Listens on localhost by default.
- Restricts browser CORS to localhost.
- Limits request size and request rate.
- Adds security response headers.
- Prevents unsafe static-file paths.
- Hides unexpected internal exception details.

Copy `.env.example` to `.env` only when custom configuration is needed. Keep
`API_HOST=127.0.0.1` for local use. If exposing the service beyond the machine,
set a strong `BACKEND_API_KEY` and configure `ALLOWED_ORIGINS`; non-local
binding without an API key is rejected.

## Platform support

The checked-in `CircuitDesignApp` file is the macOS Apple Silicon build. It is
not a Windows `.exe` or an Intel macOS binary.

To build Windows locally, clone this repository on Windows and run
`build_windows.bat`. The script installs dependencies and creates
`dist\CircuitDesignApp.exe`. See [WINDOWS_BUILD.md](WINDOWS_BUILD.md) for
requirements and troubleshooting. Builds must run on their target operating
system.

The repository includes the `app/` and `frontend/` source required by the build
script. Generated virtual environments and build directories are ignored.

## License

See [LICENSE](LICENSE).
