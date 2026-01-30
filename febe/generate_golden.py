#!/usr/bin/env python3
"""Generate golden test cases from the Udanax Green backend.

Runs test scenarios against the backend in test mode (fresh state per scenario)
and outputs JSON test cases capturing the expected behavior.
"""

import argparse
import json
import sys
from pathlib import Path

from client import XuSession, XuConn, PipeStream, Address

from scenarios import ALL_SCENARIOS

# Default account address for test mode
DEFAULT_ACCOUNT = Address(1, 1, 0, 1)


class BackendProcess:
    """Manages a backend subprocess in test mode."""

    def __init__(self, backend_path):
        self.backend_path = backend_path
        self.process = None
        self.session = None

    def start(self):
        """Start the backend and establish a session."""
        # Use PipeStream to communicate with backend
        stream = PipeStream(f"{self.backend_path} --test-mode")
        self.session = XuSession(XuConn(stream))
        # Set up default account for creating documents
        self.session.account(DEFAULT_ACCOUNT)
        return self.session

    def stop(self):
        """Stop the backend."""
        if self.session and self.session.open:
            try:
                self.session.quit()
            except:
                pass
        self.session = None


def run_scenario(backend_path, category, name, scenario_func):
    """Run a single scenario with a fresh backend."""
    backend = BackendProcess(backend_path)
    try:
        session = backend.start()
        result = scenario_func(session)
        return result
    except Exception as e:
        return {
            "name": name,
            "error": str(e),
            "operations": []
        }
    finally:
        backend.stop()


def main():
    parser = argparse.ArgumentParser(description="Generate golden test cases")
    parser.add_argument("--backend", default="../backend/build/backend",
                        help="Path to backend executable")
    parser.add_argument("--output", default="../golden",
                        help="Output directory for test cases")
    parser.add_argument("--scenario", help="Run only this scenario")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    args = parser.parse_args()

    if args.list:
        print("Available scenarios:")
        current_category = None
        for category, name, _ in ALL_SCENARIOS:
            if category != current_category:
                print(f"\n  {category}:")
                current_category = category
            print(f"    - {name}")
        return

    # Resolve paths
    script_dir = Path(__file__).parent
    backend_path = (script_dir / args.backend).resolve()
    output_dir = (script_dir / args.output).resolve()

    if not backend_path.exists():
        print(f"Error: Backend not found at {backend_path}")
        print("Run 'make' in the backend directory first.")
        sys.exit(1)

    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run scenarios
    for category, name, scenario_func in ALL_SCENARIOS:
        if args.scenario and args.scenario != name:
            continue

        print(f"Running {category}/{name}...", end=" ", flush=True)

        result = run_scenario(str(backend_path), category, name, scenario_func)

        if "error" in result:
            print(f"ERROR: {result['error']}")
        else:
            print("ok")

            # Write output
            category_dir = output_dir / category
            category_dir.mkdir(exist_ok=True)

            output_file = category_dir / f"{name}.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)

    print(f"\nTests written to {output_dir}")


if __name__ == "__main__":
    main()
