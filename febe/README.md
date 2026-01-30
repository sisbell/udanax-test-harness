# FEBE Test Harness

Generate golden tests from the Udanax Green C backend.

## Quick Start

```bash
# Build the backend
cd ../backend && make

# Run all tests
python3 generate_golden.py

# Run specific scenario
python3 generate_golden.py --scenario create_version

# List available scenarios
python3 generate_golden.py --list
```

## Test Mode

The backend supports `--test-mode` for in-memory storage:
- No `enf.enf` file created
- State cleared when process exits
- Fresh state per test scenario

## Files

- `client.py` - FEBE protocol client (Python 3)
- `generate_golden.py` - Golden test generator
- `../golden/` - Generated JSON test files
- `../bugs/` - Bug documentation

## Test Scenarios

| Category | Scenario | Description |
|----------|----------|-------------|
| documents | create_document | Create empty document |
| documents | multiple_documents | Multiple independent documents |
| content | insert_text | Insert and retrieve text |
| content | multiple_inserts | Sequential inserts |
| content | insert_middle | Insert within existing content |
| content | delete_text | Delete portion of content |
| content | partial_retrieve | Retrieve subset of content |
| content | vcopy_transclusion | Copy content between documents |
| versions | create_version | Create document version |
| versions | compare_versions | Compare two versions |
| links | create_link | Create link between documents |
| links | find_links | Search for links |
| internal | internal_state | Capture enfilade state |
