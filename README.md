# Udanax Green Test Harness

Golden test harness for capturing the semantic behavior of the original 1999 Udanax Green backend.

## Purpose

Generate golden tests that document the correct behavior of Udanax enfilade operations. The C backend serves as the reference implementation; the Python FEBE client drives it through its protocol.

## Building

```bash
make                # Build C backend
make clean          # Clean build artifacts
```

Binaries are output to `backend/build/`.

## Testing

```bash
make test           # Run all tests (client unit + golden integration)
make test-client    # Client protocol unit tests (no backend needed)
make test-golden    # Golden integration tests (263 scenarios)
```

## Golden Tests

```bash
make golden                                  # Generate golden output (C backend)
make golden BACKEND=/path/to/server          # Generate from custom server
make golden SCENARIO=insert_text             # Single scenario
make golden-list                             # List all scenarios

make compare ACTUAL=/tmp/my-golden           # Compare against reference
make compare ACTUAL=/tmp/my-golden VERBOSE=1 # Show per-operation diffs
make compare ACTUAL=/tmp/my-golden CATEGORY=content  # Filter by category
```

## Project Structure

```
├── backend/     # C backend (Udanax Green enfilade server)
├── febe/        # Python FEBE protocol client and test generator
├── golden/      # Generated golden test files (not in source control)
├── bugs/        # Bug reports discovered during testing
├── findings/    # Semantic findings from test results
├── docs/        # Documentation
├── Makefile     # Build orchestration
└── LICENSE      # Project license
```

## Documentation

| Doc | When to read it |
|-----|-----------------|
| [Golden Tests](docs/golden-tests.md) | Run tests, read output, understand how operations affect state |
| [Writing Scenarios](docs/writing-scenarios.md) | Add new test scenarios to the suite |
| [Integrating an Enfilade Server](docs/integrating-enfilade-server.md) | Connect a custom enfilade server to the FEBE protocol |
| [FEBE Protocol](docs/febe-protocol.md) | Wire format reference for the front-end/back-end protocol |
| [Client API](docs/client-api.md) | Python client methods and their wire mappings |

## Origin

Based on the Udanax Green distribution released 2 September 1999.

Original source: http://udanax.xanadu.com/green/download/udanax-1999-09-29.tar.gz

For more information about the Udanax project: http://www.udanax.com/

## License

This project contains code from multiple sources:

- **backend/** - Udanax Green (1979-1999 Udanax.com) - see `backend/LICENSE`
- **febe/** - Python client by Ka-Ping Yee (1999) - see `febe/LICENSE`
- **Modifications** - MIT License (2026)

See [LICENSE](LICENSE) for full terms.
