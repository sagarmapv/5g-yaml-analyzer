# 5G SBI YAML Viewer & Analyzer

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A lightweight web tool to parse, inspect, and explore **5G SBI YAML API files** (from 3GPP specs). Built with **Python + Flask**, it lists **Network Functions → Services → SBI messages** with URI, method, parameters, responses, and generated curl templates.

## Project Structure

```text
5g-yaml-analyzer/
├── backend/
│   ├── app.py                 # Flask entry point
│   ├── config.py              # Portable path configuration
│   ├── routes/                # REST API blueprints
│   └── services/              # Build pipeline, bank builder, search, curl
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── scripts/
│   └── build.py               # CLI: YAML → JSON → Bank → index
├── Yaml-Files/5GC_APIs/       # User-supplied 3GPP YAMLs
├── Parsed-JSON/               # Generated (gitignored)
├── Bank/                      # Generated (gitignored)
├── index.json                 # Generated (gitignored)
├── tests/
├── requirements.txt
└── README.md
```

## Features

- **Build pipeline**: YAML → Swagger JSON → Bank JSON → index (cross-platform Python, no bash)
- **Web viewer**: Collapsible NF → Services sidebar with search
- **REST API**: Index, bank, search, curl, rebuild, health endpoints
- **curl generator**: Copy-ready curl templates per operation
- **Windows-friendly**: No hardcoded Linux paths; runs on Windows 10/11

## YAML File Setup

This repo does **not** include 3GPP YAMLs due to size and licensing.

1. Download OpenAPI YAML files from [jdegre/5GC_APIs](https://github.com/jdegre/5GC_APIs)
2. Place them in:

```text
Yaml-Files/5GC_APIs/
```

## Prerequisites

- Python 3.10+
- [Node.js](https://nodejs.org/) with swagger-cli:

```bash
npm install -g @apidevtools/swagger-cli
```

On Windows, Python resolves `swagger-cli.cmd` automatically. If build still fails, ensure `%APPDATA%\npm` is on your PATH, or run from a terminal where `swagger-cli --version` works.

## Setup

### Windows (PowerShell)

```powershell
git clone https://github.com/sagarmapv/5g-yaml-analyzer.git
cd 5g-yaml-analyzer

python -m venv venv
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
copy .env.example .env
```

### Linux / macOS

```bash
git clone https://github.com/sagarmapv/5g-yaml-analyzer.git
cd 5g-yaml-analyzer

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

## Run

Build the index from your YAML files (first time, or after adding YAMLs):

```bash
python scripts/build.py
```

Start the server:

```bash
python -m backend.app
```

Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

### NF Topology diagram

Open [http://127.0.0.1:5000/topology](http://127.0.0.1:5000/topology) for an interactive graph of which NFs reference which others (inferred from cross-spec YAML `$ref` links and SBI path patterns). Use **Core 5GC NFs only** to focus on AMF, SMF, UDM, PCF, NRF, etc.

You can also rebuild from the UI (**Rebuild** button) or via API:

```bash
curl -X POST http://127.0.0.1:5000/api/rebuild
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/index` | GET | NF → services map |
| `/api/yaml/<file>` | GET | Raw YAML content |
| `/api/parsed/<file>` | GET | Operation summary list |
| `/api/bank/<file>` | GET | Full Bank JSON for a service |
| `/api/search?q=` | GET | Cross-NF search |
| `/api/curl/<file>/<operationId>` | GET | Generated curl template |
| `/api/rebuild` | POST | Re-run build pipeline |
| `/api/health` | GET | Health and build status |
| `/topology` | GET | Interactive NF relationship diagram |
| `/api/map` | GET | NF → 3GPP TS spec → YAML hierarchy |

Legacy routes (`/index`, `/yaml/`, `/parsed/`, `/list-yamls`) remain for backward compatibility.

## Development

Install dev dependencies and run tests:

```bash
pip install -r requirements-dev.txt
pytest -v
```

## Configuration

Optional environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_ROOT` | Auto-detected | Override project root path |
| `DEBUG` | `false` | Flask debug mode |
| `PORT` | `5000` | Server port |
| `HOST` | `127.0.0.1` | Server host |

## License

MIT License — see [LICENSE](LICENSE).

## Credits

Built with love by Aditya Madduri and contributors. Inspired by the need to bring clarity to 5G SBI interfaces.
