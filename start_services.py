
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path("/app")
DB_PATH = Path(
    os.environ.get(
        "GOPARKING_DB_PATH",
        str(BASE_DIR / "goparking.db"),
    )
)

processes = []


def log(message):
    print(f"[GoParking Startup] {message}", flush=True)


def stop_processes():
    for process in reversed(processes):
        if process.poll() is None:
            log(f"Stopping process PID {process.pid}")
            process.terminate()

    for process in reversed(processes):
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


try:
    log("Startup script is running")
    log(f"Database path: {DB_PATH}")

    # Start Java parking server
    log("Starting Java parking server")
    java = subprocess.Popen(
        ["java", "ParkingServer"],
        cwd=str(BASE_DIR / "java_backend"),
    )
    processes.append(java)

    # Start Streamlit; app.py calls init_db()
    log("Starting Streamlit")
    streamlit = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(BASE_DIR / "app.py"),
            "--server.port",
            os.environ.get("PORT", "10000"),
            "--server.address",
            "0.0.0.0",
        ],
        cwd=str(BASE_DIR),
    )
    processes.append(streamlit)

    # Wait for Streamlit to initialize the payments table
    log("Waiting for payments table initialization")
    deadline = time.time() + 90

    while time.time() < deadline:
        if streamlit.poll() is not None:
            raise RuntimeError(
                f"Streamlit exited with code {streamlit.returncode}"
            )

        if java.poll() is not None:
            raise RuntimeError(
                f"Java server exited with code {java.returncode}"
            )

        try:
            with sqlite3.connect(str(DB_PATH), timeout=2) as connection:
                table = connection.execute(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type='table' AND name='payments'"
                ).fetchone()

            if table:
                log("Payments table detected")
                break

        except sqlite3.Error as error:
            log(f"Database is not ready yet: {error}")

        time.sleep(2)
    else:
        raise RuntimeError(
            "Timed out waiting for the payments table"
        )

    # Start Payment API after the database is initialized
    log("Starting Payment API")
    payment_api = subprocess.Popen(
        [sys.executable, str(BASE_DIR / "payment_api.py")],
        cwd=str(BASE_DIR),
    )
    processes.append(payment_api)

    # Monitor all services
    log("All services started; monitoring processes")

    while True:
        for name, process in (
            ("Streamlit", streamlit),
            ("Java", java),
            ("Payment API", payment_api),
        ):
            return_code = process.poll()
            if return_code is not None:
                raise RuntimeError(
                    f"{name} exited with code {return_code}"
                )

        time.sleep(2)

except KeyboardInterrupt:
    log("Shutdown requested")

except Exception as error:
    log(f"FATAL: {error}")
    raise

finally:
    stop_processes()
    log("Startup script stopped")
