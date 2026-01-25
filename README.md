# Udanax Green Test Harness

Golden test harness for capturing the semantic behavior of the original 1999 Udanax Green backend.

## Purpose

Generate golden tests that document the correct behavior of Udanax enfilade operations. The C backend serves as the reference implementation; the Python FEBE client drives it through its protocol.

## Building

```bash
make          # Build C backend
make test     # Run Python protocol tests
make clean    # Clean build artifacts
```

Binaries are output to `backend/build/`.

## Running

Start the backend in test mode (in-memory storage, no disk persistence):

```bash
backend/build/backend --test-mode
```

## Project Structure

```
├── backend/     # C backend (Udanax Green enfilade server)
├── febe/        # Python FEBE protocol client
├── Makefile     # Build orchestration
└── LICENSE      # Project license
```

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
