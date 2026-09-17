#!/usr/bin/env python3
"""Legal Lens — one-command launcher.

Run this instead of starting the backend, frontend, Ollama, and ingestion
separately: `python3 run.py` (or `./run.py`) from the project root.

What it does, in order, each step skipped automatically if already done:
  1. Creates backend/.venv if missing, installs backend dependencies.
  2. Creates backend/.env from .env.example if missing.
  3. Checks Ollama is reachable and the configured model is pulled — warns
     (doesn't hard-fail) if not, since the deterministic parts of the app
     (claims/evidence CRUD, timeline, audit log, Law Retrieval) work with
     no LLM at all.
  4. Ingests the legal corpus into ChromaDB if it hasn't been already.
  5. Installs frontend node_modules if missing.
  6. Starts the backend (uvicorn) and frontend (vite dev) together, waits
     for both to come up, prints the URLs, and streams their logs.
  7. On Ctrl+C, shuts both down cleanly.

Nothing here replaces `backend/tests` (run those with `pytest` directly) or
`backend/e2e_smoke.py` (a live, no-mocking pipeline smoke test) — this
script is specifically about getting the app itself running.
"""

from __future__ import annotations

import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Line-buffer stdout even when it's redirected to a file/pipe (not a TTY) — otherwise
# every print() below sits in Python's internal buffer and never reaches a log file
# until the process exits, even though the backend/frontend subprocesses' own output
# (inherited fd, no Python-level buffering) shows up immediately. Only matters when
# stdout isn't a live terminal (e.g. `python3 run.py > run.log 2>&1 &`), but that's a
# real, likely way this script gets used, not just a testing artifact.
try:
    sys.stdout.reconfigure(line_buffering=True)
except AttributeError:
    pass  # older Python without reconfigure(); safe to skip

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = BACKEND / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

BACKEND_PORT = 8000
FRONTEND_PORT = 5173
OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3.5:9b-q4_K_M"


def _print_step(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def _run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=check)


def _venv_has_package(package: str) -> bool:
    result = subprocess.run(
        [str(VENV_PYTHON), "-c", f"import {package}"],
        capture_output=True,
    )
    return result.returncode == 0


def ensure_backend_venv() -> None:
    _print_step("1. Backend virtual environment")
    if VENV_PYTHON.exists():
        print(f"Already exists at {VENV}.")
    else:
        print(f"Creating venv at {VENV} ...")
        base_python = shutil.which("python3.13") or shutil.which("python3.12") or shutil.which("python3.11") or sys.executable
        _run([base_python, "-m", "venv", str(VENV)], cwd=ROOT)
        print("Created.")

    if _venv_has_package("fastapi"):
        print("Backend dependencies already installed.")
    else:
        print("Installing backend dependencies (pip install -e .) ...")
        _run([str(VENV_PYTHON), "-m", "pip", "install", "-q", "-e", "."], cwd=BACKEND)
        print("Installed.")


def ensure_backend_env_file() -> None:
    _print_step("2. Backend .env file")
    env_file = BACKEND / ".env"
    env_example = BACKEND / ".env.example"
    if env_file.exists():
        print(f"{env_file} already exists.")
        return
    print(f"Creating {env_file} from .env.example (no API key needed — fully local) ...")
    shutil.copy(env_example, env_file)
    print("Created.")


def _ollama_model_name() -> str:
    env_file = BACKEND / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("OLLAMA_MODEL=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip() or DEFAULT_MODEL
    return DEFAULT_MODEL


def check_ollama() -> None:
    _print_step("3. Ollama (local LLM)")
    model = _ollama_model_name()
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as resp:
            import json

            models = [m["name"] for m in json.load(resp).get("models", [])]
    except (urllib.error.URLError, OSError):
        print(
            f"WARNING: Ollama isn't reachable at {OLLAMA_URL}.\n"
            f"  Install it from https://ollama.com, run `ollama pull {model}`, and make\n"
            f"  sure the Ollama app/daemon is running. The app will still start without\n"
            f"  it, but every AI-agent step will fail until Ollama is up — deterministic\n"
            f"  features (claims/evidence CRUD, timeline, audit log, Law Retrieval) still\n"
            f"  work with no LLM at all."
        )
        return

    if model in models:
        print(f"Ollama is running and '{model}' is available.")
    else:
        print(
            f"WARNING: Ollama is running, but '{model}' isn't pulled yet.\n"
            f"  Run: ollama pull {model}\n"
            f"  Currently available: {', '.join(models) or '(none)'}"
        )


def ensure_corpus_ingested() -> None:
    _print_step("4. Legal corpus / ChromaDB")
    check = subprocess.run(
        [str(VENV_PYTHON), "-c", "from app.vector_store import get_collection; print(get_collection().count())"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
    )
    count = int(check.stdout.strip() or "0") if check.returncode == 0 else 0
    if count > 0:
        print(f"Already ingested: {count} chunks in ChromaDB.")
        return
    print("No chunks found — running ingestion (this reads the PDFs in data/raw/criminal-law/) ...")
    _run([str(VENV_PYTHON), "-m", "app.ingestion"], cwd=BACKEND)


def ensure_frontend_deps() -> None:
    _print_step("5. Frontend dependencies")
    if (FRONTEND / "node_modules").exists():
        print("node_modules already installed.")
        return
    npm = shutil.which("npm")
    if npm is None:
        print("ERROR: npm not found on PATH. Install Node.js (https://nodejs.org) and re-run.")
        sys.exit(1)
    print("Running npm install ...")
    _run([npm, "install"], cwd=FRONTEND)


def _wait_for(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    return False


def run_servers() -> None:
    _print_step("6. Starting backend + frontend")
    npm = shutil.which("npm")
    if npm is None:
        print("ERROR: npm not found on PATH. Install Node.js (https://nodejs.org) and re-run.")
        sys.exit(1)

    backend_proc = subprocess.Popen(
        [str(VENV_PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(BACKEND_PORT)],
        cwd=BACKEND,
    )
    frontend_proc = subprocess.Popen(
        [npm, "run", "dev", "--", "--port", str(FRONTEND_PORT)],
        cwd=FRONTEND,
    )

    # SIGTERM (the default signal `kill <pid>` sends, and what most process
    # supervisors use to ask a process to stop) doesn't raise KeyboardInterrupt on
    # its own — only SIGINT (Ctrl+C in a live terminal) does. Without this, `kill`ing
    # run.py would leave the backend/frontend subprocesses orphaned and still
    # running. Converting SIGTERM into the same KeyboardInterrupt path means one
    # shutdown code path handles both Ctrl+C and `kill`.
    def _handle_sigterm(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _handle_sigterm)

    print("\nWaiting for both servers to come up ...")
    backend_ok = _wait_for(f"http://localhost:{BACKEND_PORT}/health")
    frontend_ok = _wait_for(f"http://localhost:{FRONTEND_PORT}")

    print()
    print("=" * 70)
    if backend_ok:
        print(f"Backend:  http://localhost:{BACKEND_PORT}  (OK)")
    else:
        print(f"Backend:  http://localhost:{BACKEND_PORT}  (not responding yet — check its log output above)")
    if frontend_ok:
        print(f"Frontend: http://localhost:{FRONTEND_PORT}  (OK) <-- open this in your browser")
    else:
        print(f"Frontend: http://localhost:{FRONTEND_PORT}  (not responding yet — check its log output above)")
    print("=" * 70)
    print("Press Ctrl+C to stop both servers.\n")

    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("Backend process exited unexpectedly — stopping frontend too.")
                break
            if frontend_proc.poll() is not None:
                print("Frontend process exited unexpectedly — stopping backend too.")
                break
    except KeyboardInterrupt:
        print("\nShutting down ...")
    finally:
        for proc, name in ((backend_proc, "backend"), (frontend_proc, "frontend")):
            if proc.poll() is None:
                proc.terminate()
        for proc, name in ((backend_proc, "backend"), (frontend_proc, "frontend")):
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print(f"{name} didn't stop in time, killing it.")
                proc.kill()
        print("Stopped.")


def main() -> None:
    if not BACKEND.exists() or not FRONTEND.exists():
        print("ERROR: run this script from the Legal Lens project root (backend/ and frontend/ must exist next to it).")
        sys.exit(1)

    ensure_backend_venv()
    ensure_backend_env_file()
    check_ollama()
    ensure_corpus_ingested()
    ensure_frontend_deps()
    run_servers()


if __name__ == "__main__":
    main()
