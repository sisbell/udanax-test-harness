#!/usr/bin/env python3
"""Generate golden test cases for multi-session scenarios.

Unlike single-session tests, these require:
1. Starting the backenddaemon (TCP mode)
2. Connecting multiple FEBE clients via TCP
3. Testing interactions between sessions

The backenddaemon listens on port 55146 by default (configurable via .backendrc).
"""

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

# Add parent directory (febe/) to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir.parent))

from client import XuSession, XuConn, TcpStream, Address
from scenarios.multisession import MULTISESSION_SCENARIOS

# Default settings
DEFAULT_PORT = 55146
DEFAULT_HOST = "localhost"
DEFAULT_ACCOUNT = Address(1, 1, 0, 1)


class BackendDaemon:
    """Manages the backend daemon subprocess for multi-session testing."""

    def __init__(self, backend_path, port=DEFAULT_PORT, data_dir=None):
        self.backend_path = backend_path
        self.port = port
        self.data_dir = data_dir
        self.process = None
        self.sessions = []

    def start(self, timeout=10):
        """Start the backend daemon and wait for it to be ready."""
        env = os.environ.copy()

        # Create data directory and .backendrc file to configure the port
        if self.data_dir:
            os.makedirs(self.data_dir, exist_ok=True)
            rcfile = os.path.join(self.data_dir, ".backendrc")
            with open(rcfile, "w") as f:
                f.write(f"port = {self.port}\n")
            cwd = self.data_dir
        else:
            cwd = os.getcwd()

        # Start the daemon with stderr redirected to a file
        stderr_file = os.path.join(self.data_dir or cwd, "daemon_stderr.log")
        stderr_fd = open(stderr_file, "w")

        self.process = subprocess.Popen(
            [self.backend_path],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=stderr_fd,
            cwd=cwd,
            env=env,
            start_new_session=True  # Detach from terminal
        )

        # Give the daemon time to start up
        # We'll verify it's ready when we actually connect
        time.sleep(2.0)

        # Just check if the process is still running
        if self.process.poll() is not None:
            stderr_fd.close()
            with open(stderr_file, "r") as f:
                stderr = f.read()
            print(f"Backend exited early with code {self.process.returncode}")
            print(f"stderr: {stderr}")
            return False

        return True

    def connect(self, retries=5, delay=0.5):
        """Create a new session connected to the daemon."""
        last_error = None
        for attempt in range(retries):
            try:
                stream = TcpStream(DEFAULT_HOST, self.port)
                session = XuSession(XuConn(stream))
                session.account(DEFAULT_ACCOUNT)
                self.sessions.append(session)
                return session
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    time.sleep(delay)

        print(f"Failed to connect after {retries} attempts: {last_error}")
        return None

    def disconnect_all(self):
        """Disconnect all sessions."""
        for session in self.sessions:
            if session and session.open:
                try:
                    session.quit()
                except Exception:
                    pass
        self.sessions = []

    def stop(self):
        """Stop the backend daemon."""
        self.disconnect_all()

        if self.process:
            try:
                # Try graceful termination
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    self.process.kill()
                    try:
                        self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        # Kill the entire process group
                        try:
                            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                        except Exception:
                            pass
            except Exception:
                pass
            self.process = None

        # Brief pause to ensure port is released
        time.sleep(0.2)


def run_multisession_scenario(backend_path, data_dir, category, name, scenario_func, verbose=False):
    """Run a single multi-session scenario with a fresh backend daemon."""
    # Use a unique port for each test to avoid conflicts
    port = DEFAULT_PORT + (hash(name) % 1000)

    if verbose:
        print(f"\n  Using port {port}, data_dir: {data_dir}")

    daemon = BackendDaemon(backend_path, port=port, data_dir=data_dir)
    try:
        if verbose:
            print("  Starting daemon...", flush=True)
        if not daemon.start():
            return {
                "name": name,
                "error": "Failed to start backend daemon",
                "operations": []
            }

        if verbose:
            print("  Daemon started, connecting session A...", flush=True)

        # Create two sessions
        session_a = daemon.connect()

        if verbose:
            print("  Session A connected, connecting session B...", flush=True)

        session_b = daemon.connect()

        if not session_a or not session_b:
            return {
                "name": name,
                "error": "Failed to connect sessions",
                "operations": []
            }

        if verbose:
            print("  Both sessions connected, running scenario...", flush=True)

        # Run the scenario
        result = scenario_func((session_a, session_b))

        if verbose:
            print("  Scenario complete", flush=True)

        return result

    except Exception as e:
        import traceback
        return {
            "name": name,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "operations": []
        }
    finally:
        if verbose:
            print("  Stopping daemon...", flush=True)
        daemon.stop()
        # Clean up data directory
        if data_dir and os.path.exists(data_dir):
            import shutil
            try:
                shutil.rmtree(data_dir)
            except Exception:
                pass
        if verbose:
            print("  Cleanup complete", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Generate multi-session golden test cases")
    parser.add_argument("--backend", default="../../backend/build/backenddaemon",
                        help="Path to backenddaemon executable")
    parser.add_argument("--output", default="../../golden",
                        help="Output directory for test cases")
    parser.add_argument("--scenario", help="Run only this scenario")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    parser.add_argument("--data-dir", default="/tmp/xanadu-multisession-test",
                        help="Directory for test data (will be cleaned)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output for debugging")
    args = parser.parse_args()

    if args.list:
        print("Available multi-session scenarios:")
        for category, name, _ in MULTISESSION_SCENARIOS:
            print(f"  - {name}")
        return

    # Resolve paths
    script_dir = Path(__file__).parent
    backend_path = (script_dir / args.backend).resolve()
    output_dir = (script_dir / args.output).resolve()

    if not backend_path.exists():
        print(f"Error: Backend daemon not found at {backend_path}")
        print("Run 'make' in the backend directory to build backenddaemon.")
        sys.exit(1)

    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run scenarios
    success_count = 0
    error_count = 0

    for category, name, scenario_func in MULTISESSION_SCENARIOS:
        if args.scenario and args.scenario != name:
            continue

        print(f"Running {category}/{name}...", end=" ", flush=True)

        # Each scenario gets its own data directory
        data_dir = os.path.join(args.data_dir, name)

        result = run_multisession_scenario(
            str(backend_path), data_dir, category, name, scenario_func,
            verbose=args.verbose
        )

        if "error" in result:
            print(f"ERROR: {result['error']}")
            error_count += 1
            if "traceback" in result:
                print(result["traceback"])
        else:
            print("ok")
            success_count += 1

            # Write output
            category_dir = output_dir / category
            category_dir.mkdir(exist_ok=True)

            output_file = category_dir / f"{name}.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)

    print(f"\nResults: {success_count} passed, {error_count} failed")
    if success_count > 0:
        print(f"Tests written to {output_dir}/multisession/")


if __name__ == "__main__":
    main()
