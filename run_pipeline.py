"""
==============================================================================
Olist E-Commerce Data Warehouse - End-to-End Pipeline Orchestrator
Script: run_pipeline.py
Purpose: Orchestrates the full lifecycle of data processing:
         1. Staging Ingestion (Raw CSV -> staging schema)
         2. Warehouse Transformation (staging -> warehouse Star Schema)
         3. Data Quality Auditing (72 automated integrity checks)
         4. BI Analytics Dashboard (Streamlit interactive interface)

Features:
         - Live console streaming + persistent file logging in logs/
         - Generates timestamped logs: logs/pipeline_YYYYMMDD_HHMMSS.log
         - Updates logs/pipeline_latest.log for easy monitoring
         - Transaction-safe, fail-fast error handling
==============================================================================
"""

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output encoding for Windows Terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ------------------------------------------------------------------------------
# Paths Configuration
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"
DASHBOARD_DIR = BASE_DIR / "dashboard"
LOGS_DIR = BASE_DIR / "logs"

LOAD_STAGING_SCRIPT = SCRIPTS_DIR / "load_staging.py"
LOAD_WAREHOUSE_SCRIPT = SCRIPTS_DIR / "load_warehouse.py"
VALIDATE_WAREHOUSE_SCRIPT = SCRIPTS_DIR / "validate_warehouse.py"
DASHBOARD_APP_SCRIPT = DASHBOARD_DIR / "app.py"


# ------------------------------------------------------------------------------
# Logging Infrastructure
# ------------------------------------------------------------------------------
class PipelineLogger:
    """Manages simultaneous live streaming to console and file logging in logs/."""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = self.log_dir / f"pipeline_{timestamp}.log"
        self.latest_log_path = self.log_dir / "pipeline_latest.log"

        # Open file in UTF-8
        self._file = open(self.log_file_path, "w", encoding="utf-8", buffering=1)

    def log(self, message: str = "", end: str = "\n"):
        """Writes to both stdout and log file."""
        sys.stdout.write(message + end)
        sys.stdout.flush()
        self._file.write(message + end)
        self._file.flush()

    def log_error(self, message: str = "", end: str = "\n"):
        """Writes to both stderr and log file."""
        sys.stderr.write(message + end)
        sys.stderr.flush()
        self._file.write(f"[ERROR] {message}{end}")
        self._file.flush()

    def banner(self, step_num: int, total_steps: int, title: str, description: str):
        """Prints a styled execution banner for each pipeline stage."""
        self.log("\n" + "=" * 75)
        self.log(f"[{step_num}/{total_steps}] {title.upper()}")
        self.log(f"      {description}")
        self.log("=" * 75)

    def close(self):
        """Flushes, closes log file, and syncs to pipeline_latest.log."""
        if self._file and not self._file.closed:
            self._file.flush()
            self._file.close()
            try:
                shutil.copyfile(self.log_file_path, self.latest_log_path)
            except Exception:
                pass


def run_step(step_name: str, script_path: Path, logger: PipelineLogger, args: list = None) -> float:
    """Executes a standalone Python script in a subprocess with live logging.

    Args:
        step_name: Human-readable name of the step.
        script_path: Absolute path to the script to execute.
        logger: Active PipelineLogger instance.
        args: Optional list of command-line arguments.

    Returns:
        float: Execution duration in seconds.

    Raises:
        SystemExit: If the subprocess returns a non-zero exit code.
    """
    if not script_path.exists():
        logger.log_error(f"Script not found: {script_path}")
        logger.close()
        sys.exit(1)

    # Use -u for unbuffered real-time stdout streaming
    cmd = [sys.executable, "-u", str(script_path)]
    if args:
        cmd.extend(args)

    start_time = time.time()
    try:
        process = subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        # Stream lines in real time to both terminal and log file
        for line in process.stdout:
            logger.log(line, end="")

        process.wait()
        returncode = process.returncode

    except KeyboardInterrupt:
        logger.log_error(f"Pipeline interrupted by user during '{step_name}'.")
        logger.close()
        sys.exit(130)

    elapsed = time.time() - start_time

    if returncode != 0:
        logger.log("\n" + "!" * 75)
        logger.log_error(f"[PIPELINE HALTED] Stage '{step_name}' failed with exit code {returncode}!")
        logger.log(f"Review the log above or file '{logger.log_file_path}' for details.")
        logger.log("!" * 75 + "\n")
        logger.close()
        sys.exit(returncode)

    logger.log(f"\n[+] {step_name} completed successfully in {elapsed:.2f}s.")
    return elapsed


def launch_dashboard(app_path: Path, logger: PipelineLogger):
    """Launches the Streamlit BI Analytics dashboard."""
    if not app_path.exists():
        logger.log_error(f"Dashboard entrypoint not found: {app_path}")
        logger.close()
        sys.exit(1)

    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    logger.log("\n" + "=" * 75)
    logger.log("[*] Starting Streamlit server...")
    logger.log(f"[*] Command: {' '.join(cmd)}")
    logger.log(f"[*] Pipeline log saved to: {logger.log_file_path}")
    logger.log("[*] Press Ctrl+C in this terminal anytime to stop the dashboard server.")
    logger.log("=" * 75 + "\n")

    # Sync log before handing control over to interactive Streamlit
    logger.close()

    try:
        subprocess.run(cmd, cwd=BASE_DIR)
    except KeyboardInterrupt:
        print("\n[INFO] Dashboard server stopped by user. Pipeline finished gracefully.")


def main():
    total_start = time.time()
    logger = PipelineLogger(LOGS_DIR)

    # Parse CLI flags
    skip_staging = "--skip-staging" in sys.argv
    skip_warehouse = "--skip-warehouse" in sys.argv
    skip_validation = "--skip-validation" in sys.argv
    skip_dashboard = any(arg in sys.argv for arg in ["--skip-dashboard", "--no-dashboard", "--headless"])
    dashboard_only = "--dashboard-only" in sys.argv

    start_datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logger.log("=" * 75)
    logger.log("   OLIST E-COMMERCE DATA WAREHOUSE & ANALYTICS PIPELINE")
    logger.log("=" * 75)
    logger.log(f"• Start Time         : {start_datetime_str}")
    logger.log(f"• Python Interpreter : {sys.executable}")
    logger.log(f"• Project Root       : {BASE_DIR}")
    logger.log(f"• Log File           : {logger.log_file_path}")
    logger.log(f"• Mode               : {'Dashboard Only' if dashboard_only else 'Full Data Pipeline'}")
    logger.log("=" * 75)

    if dashboard_only:
        logger.banner(1, 1, "Analytics Dashboard", "Launching Streamlit Dashboard directly")
        launch_dashboard(DASHBOARD_APP_SCRIPT, logger)
        return

    # Total stages count
    total_stages = 4 if not skip_dashboard else 3
    current_stage = 1

    # --------------------------------------------------------------------------
    # Stage 1: Staging Ingestion
    # --------------------------------------------------------------------------
    if skip_staging:
        logger.log("\n[*] Skipping Stage 1 (Staging Ingestion) as requested (--skip-staging).")
    else:
        logger.banner(
            current_stage,
            total_stages,
            "Staging Ingestion",
            "Loading 9 raw CSV datasets into PostgreSQL staging schema via binary copy",
        )
        run_step("Staging Ingestion", LOAD_STAGING_SCRIPT, logger)
    current_stage += 1

    # --------------------------------------------------------------------------
    # Stage 2: Warehouse Transformation & Loading
    # --------------------------------------------------------------------------
    if skip_warehouse:
        logger.log("\n[*] Skipping Stage 2 (Warehouse Loading) as requested (--skip-warehouse).")
    else:
        logger.banner(
            current_stage,
            total_stages,
            "Warehouse Transformation",
            "Transforming staging views and loading into Kimball Star Schema (ACID Transaction)",
        )
        run_step("Warehouse Loading", LOAD_WAREHOUSE_SCRIPT, logger)
    current_stage += 1

    # --------------------------------------------------------------------------
    # Stage 3: Data Quality & Validation Suite
    # --------------------------------------------------------------------------
    if skip_validation:
        logger.log("\n[*] Skipping Stage 3 (Data Quality Validation) as requested (--skip-validation).")
    else:
        logger.banner(
            current_stage,
            total_stages,
            "Data Quality Audit",
            "Running 72 automated integrity, referential, null rate, and financial reconciliation checks",
        )
        run_step("Warehouse Validation", VALIDATE_WAREHOUSE_SCRIPT, logger)
    current_stage += 1

    total_pipeline_time = time.time() - total_start
    logger.log("\n" + "=" * 75)
    logger.log(f"[+] DATA PIPELINE FINISHED SUCCESSFULLY IN {total_pipeline_time:.2f}s!")
    logger.log(f"[+] Execution log persisted at: {logger.log_file_path}")
    logger.log(f"[+] Latest log link: {logger.latest_log_path}")
    logger.log("=" * 75)

    # --------------------------------------------------------------------------
    # Stage 4: Launch Streamlit BI Dashboard
    # --------------------------------------------------------------------------
    if skip_dashboard:
        logger.log("[*] Dashboard launch skipped (--skip-dashboard / --no-dashboard).")
        logger.close()
    else:
        logger.banner(
            current_stage,
            total_stages,
            "BI Analytics Dashboard",
            "Starting Streamlit dashboard on http://localhost:8501",
        )
        launch_dashboard(DASHBOARD_APP_SCRIPT, logger)


if __name__ == "__main__":
    main()
