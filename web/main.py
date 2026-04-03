"""
@file main.py
@brief FastAPI web app - dashboard, config, run pipeline, backtest, utilities.
@details Serves current dashboard style; uses config/config.yaml and project root.
"""

import asyncio
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional
from queue import Queue, Empty

import yaml
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

# Project root (parent of web/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
REPORTS_DIR = PROJECT_ROOT / "reports"

app = FastAPI(title="Stock Trader", version="1.0")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


def get_config() -> dict:
    """Load config from config/config.yaml. Always returns a dict."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError:
        return {}
    if not isinstance(config, dict):
        return {"database": {"path": "data/sentiment.db"}}
    return config


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base. Modifies base in place, returns base."""
    for k, v in overlay.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def save_config(updates: dict) -> None:
    """Merge updates into existing config and save to config/config.yaml."""
    config = get_config()
    _deep_merge(config, updates)
    # Ensure database is always a dict so pipeline does not get string indices error
    db = config.get("database")
    if isinstance(db, str):
        config["database"] = {"path": db}
    elif db is not None and not isinstance(db, dict):
        config["database"] = {"path": "data/sentiment.db"}
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def get_latest_dashboard_path() -> Optional[Path]:
    """Return path to most recent dashboard_*.html or None."""
    if not REPORTS_DIR.exists():
        return None
    files = list(REPORTS_DIR.glob("dashboard_*.html"))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page: iframe to latest report or placeholder."""
    path = get_latest_dashboard_path()
    has_report = path is not None and path.exists()
    return templates.TemplateResponse(
        request=request,
        name="wrap_dashboard.html",
        context={"has_report": has_report},
    )


@app.get("/api/dashboard/latest", response_class=HTMLResponse)
async def api_dashboard_latest():
    """Return latest dashboard HTML as full document (for iframe)."""
    path = get_latest_dashboard_path()
    if path and path.exists():
        return HTMLResponse(path.read_text(encoding="utf-8"))
    return HTMLResponse("<p>No report yet. Run the pipeline.</p>", status_code=404)


@app.get("/run", response_class=HTMLResponse)
async def run_page(request: Request):
    return templates.TemplateResponse(request=request, name="run.html")


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    config = get_config()
    return templates.TemplateResponse(request=request, name="config.html", context={"config": config})


@app.get("/utilities", response_class=HTMLResponse)
async def utilities_page(request: Request):
    return templates.TemplateResponse(request=request, name="utilities.html")


@app.get("/backtest", response_class=HTMLResponse)
async def backtest_page(request: Request):
    return templates.TemplateResponse(request=request, name="backtest.html")


# ---------- API: Config ----------
@app.get("/api/config")
async def api_get_config():
    return get_config()


@app.get("/api/config/raw")
async def api_get_config_raw():
    """Return config file as raw YAML text."""
    if not CONFIG_PATH.exists():
        return ""
    return CONFIG_PATH.read_text(encoding="utf-8")


@app.post("/api/config")
async def api_save_config(request: Request):
    body = await request.json()
    if body.get("raw") is not None:
        # Save raw YAML (from textarea)
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(body["raw"], encoding="utf-8")
        return {"ok": True}
    # Merge and save dict
    save_config(body)
    return {"ok": True}


@app.post("/api/config/raw")
async def api_save_config_raw(request: Request):
    """Save raw YAML body to config file."""
    raw = await request.body()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_bytes(raw)
    return {"ok": True}


# ---------- API: Run pipeline (SSE) ----------
def _run_pipeline_worker(queue: Queue) -> None:
    """Run pipeline in thread and put each line into queue. Put None when done."""
    proc = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "main.py"), "--project-root", str(PROJECT_ROOT)],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    try:
        for line in iter(proc.stdout.readline, ""):
            queue.put(line)
        proc.wait()
        queue.put("\n[OK] Pipeline complete.\n" if proc.returncode == 0 else f"\n[Exit {proc.returncode}]\n")
    except Exception as e:
        queue.put(f"\nError: {e}\n")
    finally:
        queue.put(None)
        if proc.poll() is None:
            proc.terminate()


@app.get("/api/run/stream")
async def run_pipeline_stream(request: Request):
    """Stream pipeline stdout/stderr as Server-Sent Events."""
    queue = Queue()

    def start():
        _run_pipeline_worker(queue)

    thread = threading.Thread(target=start)
    thread.start()

    async def event_generator():
        while True:
            try:
                line = queue.get_nowait()
            except Empty:
                await asyncio.sleep(0.05)
                continue
            if line is None:
                break
            yield {"data": line}

    return EventSourceResponse(event_generator())


# ---------- API: Backtest ----------
@app.post("/api/backtest")
async def api_run_backtest(days: int = Form(90), config_file: str = Form("")):
    cmd = [sys.executable, str(PROJECT_ROOT / "utils" / "backtest.py"), "--days", str(days)]
    if config_file.strip():
        cmd.extend(["--config", config_file.strip()])
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return {"ok": result.returncode == 0, "output": output, "returncode": result.returncode}


# ---------- API: Utilities ----------
@app.post("/api/utility/type_check")
async def api_type_check():
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "utils" / "type_check.py")],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    return {"output": result.stdout + result.stderr, "returncode": result.returncode}


@app.post("/api/utility/verify_version")
async def api_verify_version():
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "utils" / "verify_version.py")],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    return {"output": result.stdout + result.stderr, "returncode": result.returncode}


@app.post("/api/utility/runtime")
async def api_runtime_test():
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "utils" / "test_runtime.py")],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    return {"output": result.stdout + result.stderr, "returncode": result.returncode}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
