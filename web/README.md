# Stock Trader Web App

FastAPI web app: dashboard, run pipeline, settings (config), backtest, utilities.

## Run

From the **project root** (Stock-Trader):

```bash
# Install dependencies (if not already)
pip install -r requirements.txt

# Start the web server
uvicorn web.main:app --host 0.0.0.0 --port 5000
```

Open **http://localhost:5000**

## Or run web/main.py directly

```bash
python web/main.py
```

(Uses uvicorn on port 5000.)

## Features

- **Dashboard** – Latest `reports/dashboard_*.html` (same style as current output). Run the pipeline to generate.
- **Run Pipeline** – One-click run with live log stream.
- **Settings** – Edit `config/config.yaml` (raw YAML). Saved to the same file.
- **Backtest** – Form: lookback days, optional config file; run and view output.
- **Utilities** (gear icon) – Type Check, Verify Bug Fixes, Runtime Test.

Config is read/written to `config/config.yaml` in the project root.
