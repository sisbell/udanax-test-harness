# CLAUDE.md - Udanax Test Harness

## Purpose

This repository contains the FEBE protocol test harness for validating the udanax-green backend. It generates golden tests that document actual backend behavior.

## Key Directories

```
udanax-test-harness/
├── febe/                 # FEBE client and test generator
│   ├── client.py         # Protocol client
│   ├── generate_golden.py # Golden test runner (251 scenarios)
│   ├── scenarios/        # Test scenarios by category
│   └── tests/            # Unit and debug tests
│       ├── test_client.py # Client protocol unit tests (mock, no backend)
│       └── debug/        # Minimal bug reproduction scripts
├── golden/               # Generated golden test files (JSON)
├── backend/              # udanax-green C backend
├── bugs/                 # Bug reports discovered during testing
└── findings/             # Semantic findings from test results
```

## Running Tests

```bash
make test          # Run both suites (client unit tests + golden integration tests)
make test-client   # Client unit tests only (fast, no backend needed)
make test-golden   # Golden integration tests only (251 scenarios, needs backend)
```

## When Bugs Are Discovered

**Do NOT commit when tests reveal bugs.** Instead:

1. **Document the bug** - Create `bugs/NNN-description.md` with reproduction steps
2. **Document findings** - Create `findings/NNN-description.md` with semantic insights
3. **Disable failing tests** - Comment out in SCENARIOS with reference to bug number
4. **Report to user** - Present findings and ask how to proceed

The user decides whether to:
- Fix the bug now
- File it for later
- Investigate further

## Writing New Tests

Add scenarios to `febe/scenarios/<category>.py`:

1. Create a function `scenario_<name>(session)` that exercises the backend
2. Return a dict with `name`, `description`, and `operations` list
3. Add to the `SCENARIOS` list at the bottom of the file
4. Run `make test-golden` to verify

## Git Commits

**Attribution:** Each agent owns its own attribution line. Do not use a global model name — different agents run on different models.
