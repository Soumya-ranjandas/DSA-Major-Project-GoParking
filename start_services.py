
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path("/app")
DB_PATH = Path(
    os.environ.get("GOPARKING_DB_PATH", str(BASE_DIR / "goparking.db"))
)

processes = []

try:
    # Start Java parking server
    java = subprocess.Popen(
        ["java", "ParkingServer"],
        cwd=str(BASE_DIR / "java_backend"),
    )
    processes.append(java)

    # Start Streamlit first so init_db() creates the tables
    streamlit = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            str(BASE_DIR / "app.py"),
            "--server.port", os.environ.get("PORT", "10000"),
            "--server.address", "0.0.0.0",
        ]
    )
    processes.append(streamlit)

    # Wait for the payments table to be created
    deadline = time.time() + 90

    while time.time() < deadline:
        if streamlit.poll() is not None:
            raise RuntimeError("Streamlit stopped during startup.")

        try:
            with sqlite3.connect(str(DB_PATH), timeout=2) as conn:
                table = conn.execute(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type='table' AND name='payments'"
                ).fetchone()

            if table:
                break
        except sqlite3.Error:
            pass

        time.sleep(1)
    else:
        raise RuntimeError("Timed out waiting for the payments table.")

    # Start payment API only after database initialization
    payment_api = subprocess.Popen(
        [sys.executable, str(BASE_DIR / "payment_api.py")]
    )
    processes.append(payment_api)

    # Keep the container alive while services are running
    while all(p.poll() is None for p in processes):
        time.sleep(2)

finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()
